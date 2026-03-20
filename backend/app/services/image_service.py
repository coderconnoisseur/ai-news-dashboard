"""
Image enrichment service.

For news items that have no image_url, fetches the article page and
extracts the best available image via:
  1. og:image          (Open Graph – most reliable, used by all major sites)
  2. twitter:image     (Twitter Card – fallback)
  3. First <img> with a meaningful src that isn't a tracker/icon

Runs as a lightweight background enrichment pass after each fetch cycle.
Processes items in batches to avoid hammering servers.
"""
import asyncio
import logging
from typing import Optional
import httpx
from bs4 import BeautifulSoup
from sqlalchemy.orm import Session
from app.models import NewsItem

logger = logging.getLogger(__name__)

# ─── Config ───────────────────────────────────────────────────────────────────

BATCH_SIZE   = 10        # articles fetched concurrently per batch
REQUEST_TIMEOUT = 10.0   # seconds per article fetch
MAX_ENRICH   = 50        # max items to enrich per cycle (avoid long blocking)

# Substrings that identify non-content images to skip
SKIP_IMAGE_PATTERNS = [
    "pixel", "beacon", "track", "1x1", "spacer", "blank",
    "avatar", "profile", "icon", "logo", "favicon",
    "data:image",           # inline base64 – too large to store as URL
    "ads.", "/ads/", "doubleclick", "adsystem",
]

# Minimum meaningful image dimension hint in URL (some sites embed WxH in path)
MIN_IMAGE_URL_LEN = 20


def _is_valid_image_url(src: str) -> bool:
    if not src or len(src) < MIN_IMAGE_URL_LEN:
        return False
    src_lower = src.lower()
    if any(p in src_lower for p in SKIP_IMAGE_PATTERNS):
        return False
    # Must look like an image file or a CDN image URL
    has_image_ext = any(src_lower.split("?")[0].endswith(ext)
                        for ext in (".jpg", ".jpeg", ".png", ".webp", ".gif", ".avif"))
    has_cdn_hint  = any(x in src_lower for x in ("image", "img", "photo", "media", "cdn", "static"))
    return has_image_ext or has_cdn_hint


async def fetch_og_image(url: str, client: httpx.AsyncClient) -> Optional[str]:
    """
    Fetch article page and extract the best image URL.
    Returns None on any failure or if no suitable image found.
    """
    try:
        resp = await client.get(
            url,
            headers={
                "User-Agent": "Mozilla/5.0 (compatible; AI-News-Bot/1.0)",
                "Accept": "text/html,*/*",
            },
            timeout=REQUEST_TIMEOUT,
            follow_redirects=True,
        )
        if resp.status_code != 200:
            return None

        # Only parse the <head> — most images are in meta tags there.
        # BeautifulSoup stops at </head> if we slice the content.
        head_end = resp.text.lower().find("</head>")
        html_head = resp.text[:head_end + 7] if head_end != -1 else resp.text[:4000]
        soup = BeautifulSoup(html_head, "lxml")

        # 1. og:image
        og = soup.find("meta", property="og:image")
        if og:
            src = og.get("content", "").strip()
            if src and _is_valid_image_url(src):
                return src

        # 2. twitter:image
        tw = soup.find("meta", attrs={"name": "twitter:image"})
        if tw:
            src = tw.get("content", "").strip()
            if src and _is_valid_image_url(src):
                return src

        # 3. First meaningful <img> in the full page body
        full_soup = BeautifulSoup(resp.text, "lxml")
        for img in full_soup.find_all("img", limit=20):
            src = (img.get("src") or img.get("data-src") or "").strip()
            if src and _is_valid_image_url(src):
                # Resolve relative
                if src.startswith("/"):
                    from urllib.parse import urlparse
                    parsed = urlparse(url)
                    src = f"{parsed.scheme}://{parsed.netloc}{src}"
                if src.startswith("http"):
                    return src

    except Exception as e:
        logger.debug(f"Image fetch failed for {url}: {e}")

    return None


async def _enrich_batch(items: list[NewsItem], db: Session) -> int:
    """Fetch OG images for a batch of items concurrently. Returns count enriched."""
    enriched = 0
    async with httpx.AsyncClient() as client:
        tasks = [fetch_og_image(item.url, client) for item in items]
        results = await asyncio.gather(*tasks, return_exceptions=True)

    for item, result in zip(items, results):
        if isinstance(result, str) and result:
            item.image_url = result[:2000]
            enriched += 1

    db.commit()
    return enriched


async def enrich_missing_images(db: Session) -> int:
    """
    Find recently saved items without images and enrich them.
    Called from the fetch cycle after save_news_items completes.
    Returns total count of images found.
    """
    items_missing = (
        db.query(NewsItem)
        .filter(NewsItem.image_url.is_(None))
        .order_by(NewsItem.fetched_at.desc())
        .limit(MAX_ENRICH)
        .all()
    )

    if not items_missing:
        return 0

    total_enriched = 0
    # Process in batches to avoid opening too many connections at once
    for i in range(0, len(items_missing), BATCH_SIZE):
        batch = items_missing[i : i + BATCH_SIZE]
        count = await _enrich_batch(batch, db)
        total_enriched += count
        if i + BATCH_SIZE < len(items_missing):
            await asyncio.sleep(0.5)   # small pause between batches

    logger.info(f"Image enrichment: {total_enriched}/{len(items_missing)} images found")
    return total_enriched