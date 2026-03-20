"""
Ingestion service: fetches AI/ML news from RSS feeds and HTML scrapers.
Applies relevance filtering (AI/ML keywords only) and ad detection before saving.
"""
import hashlib
import logging
import re
from datetime import datetime, timezone
from typing import Optional
import feedparser
import httpx
from bs4 import BeautifulSoup
from sqlalchemy.orm import Session
from app.models import Source, NewsItem
from app.config import get_settings
from app.services.title_service import clean_title

logger = logging.getLogger(__name__)
settings = get_settings()

# ─── Source registry ──────────────────────────────────────────────────────────
# type="rss"     → standard feedparser fetch
# type="scraper" → custom HTML scraper (for sites with no RSS)
# needs_filter=True → apply strict AI keyword filter (mixed-topic sources)
# needs_filter=False → source is AI-only; skip keyword check

DEFAULT_SOURCES = [
    # ── AI-lab blogs (dedicated AI content – minimal filtering) ───────────────
    {"name": "OpenAI Blog",
     "url":  "https://openai.com/blog/rss.xml",
     "type": "rss", "needs_filter": False},

    {"name": "Google AI Blog",
     "url":  "https://blog.google/technology/ai/rss/",
     "type": "rss", "needs_filter": False},

    {"name": "Anthropic News",
     "url":  "https://www.anthropic.com/news",
     "type": "scraper", "needs_filter": False},

    {"name": "DeepMind Blog",
     "url":  "https://deepmind.google/discover/blog/",
     "type": "scraper", "needs_filter": False},

    {"name": "Meta AI Blog",
     "url":  "https://ai.meta.com/blog/",
     "type": "scraper", "needs_filter": False},

    {"name": "Hugging Face Blog",
     "url":  "https://huggingface.co/blog/feed.xml",
     "type": "rss", "needs_filter": False},

    {"name": "Microsoft AI Blog",
     "url":  "https://blogs.microsoft.com/ai/feed/",
     "type": "rss", "needs_filter": False},

    # ── Tech media with AI-specific feeds ─────────────────────────────────────
    {"name": "TechCrunch AI",
     "url":  "https://techcrunch.com/category/artificial-intelligence/feed/",
     "type": "rss", "needs_filter": True},

    {"name": "VentureBeat AI",
     "url":  "https://venturebeat.com/category/ai/feed/",
     "type": "rss", "needs_filter": True},

    # The Verge: use AI-section feed, not general tech (avoids gear/gadget posts)
    {"name": "The Verge AI",
     "url":  "https://www.theverge.com/ai-artificial-intelligence/rss/index.xml",
     "type": "rss", "needs_filter": True},

    # Wired: use AI category feed, not general RSS
    {"name": "Wired AI",
     "url":  "https://www.wired.com/feed/category/artificial-intelligence/latest/rss",
     "type": "rss", "needs_filter": True},

    {"name": "MIT Tech Review AI",
     "url":  "https://www.technologyreview.com/feed/",
     "type": "rss", "needs_filter": True},

    # ── Research & papers ──────────────────────────────────────────────────────
    {"name": "arXiv cs.AI",
     "url":  "https://rss.arxiv.org/rss/cs.AI",
     "type": "rss", "needs_filter": False},

    {"name": "arXiv cs.LG",
     "url":  "https://rss.arxiv.org/rss/cs.LG",
     "type": "rss", "needs_filter": False},

    {"name": "arXiv cs.CL",
     "url":  "https://rss.arxiv.org/rss/cs.CL",
     "type": "rss", "needs_filter": False},

    {"name": "PapersWithCode",
     "url":  "https://paperswithcode.com/latest.xml",
     "type": "rss", "needs_filter": False},

    # ── Community ─────────────────────────────────────────────────────────────
    # HN: each q= term is an independent keyword (OR semantics); points≥5 cuts noise
    {"name": "Hacker News (AI)",
     "url":  "https://hnrss.org/newest?q=LLM&points=5",
     "type": "rss", "needs_filter": True},

    {"name": "Reddit r/MachineLearning",
     "url":  "https://www.reddit.com/r/MachineLearning/.rss",
     "type": "rss", "needs_filter": True},

    {"name": "Reddit r/LocalLLaMA",
     "url":  "https://www.reddit.com/r/LocalLLaMA/.rss",
     "type": "rss", "needs_filter": True},

    # The Batch: deeplearning.ai weekly newsletter
    {"name": "The Batch (deeplearning.ai)",
     "url":  "https://www.deeplearning.ai/the-batch/feed/",
     "type": "rss", "needs_filter": False},
]

# ─── AI/ML keyword whitelist ──────────────────────────────────────────────────
# At least ONE of these must appear (case-insensitive) in the title or summary
# for a mixed-topic source item to pass the relevance filter.
AI_KEYWORDS = {
    "artificial intelligence", "machine learning", "deep learning",
    "neural network", "large language model", "llm", "foundation model",
    "generative ai", "gpt", "transformer", "diffusion model",
    "reinforcement learning", "computer vision", "natural language",
    "nlp", "nlg", "speech recognition", "text-to-image", "text-to-video",
    "stable diffusion", "midjourney", "dall-e", "dall·e",
    "openai", "anthropic", "deepmind", "hugging face", "mistral",
    "gemini", "gemma", "claude", "llama", "grok", "falcon",
    "pytorch", "tensorflow", "jax", "cuda",
    "fine-tun", "rag", "retrieval-augmented", "embedding", "vector store",
    "multimodal", "agentic", "ai agent", "copilot", "autopilot",
    "robotics", "autonomous", "self-driving",
    "benchmark", "evals", "alignment", "safety",
    " ai ", " ml ", "ai-powered", "ai-generated",
}

# ─── Ad / promotional content patterns ───────────────────────────────────────
# Items matching ANY of these are dropped.
AD_TITLE_PATTERNS = [
    r"\bsponsored\b", r"\badvertisement\b", r"\bpromoted\b",
    r"\bpress release\b", r"\bbuy now\b", r"\bshop now\b",
    r"\bexclusive deal\b", r"\bdeal of the day\b",
    r"\bpromo code\b", r"\bdiscount code\b",
    r"\blimited.?time offer\b", r"\bsubscribe (now|today)\b",
    r"\d+%\s*off\b", r"\$\d+",                 # prices / discounts
    r"\bclick here\b", r"\blearn more ›?\b",
]

AD_URL_SEGMENTS = [
    "/advertise", "/sponsor", "/deals", "/shop",
    "/affiliate", "/promo", "?utm_campaign=ad",
]

# ─── Sources that are AI-only by definition (skip keyword check entirely) ─────
AI_ONLY_SOURCE_NAMES = {
    "openai blog", "google ai blog", "anthropic news", "deepmind blog",
    "meta ai blog", "hugging face blog", "microsoft ai blog",
    "arxiv cs.ai", "arxiv cs.lg", "arxiv cs.cl", "paperswithcode",
    "the batch (deeplearning.ai)",
}


# ─── Helpers ──────────────────────────────────────────────────────────────────

def compute_hash(title: str, url: str) -> str:
    content = f"{title.lower().strip()}{url.lower().strip()}"
    return hashlib.sha256(content.encode()).hexdigest()


def normalize_date(entry) -> datetime:
    if hasattr(entry, "published_parsed") and entry.published_parsed:
        return datetime(*entry.published_parsed[:6], tzinfo=timezone.utc)
    if hasattr(entry, "updated_parsed") and entry.updated_parsed:
        return datetime(*entry.updated_parsed[:6], tzinfo=timezone.utc)
    return datetime.now(tz=timezone.utc)


def extract_image(entry) -> Optional[str]:
    if hasattr(entry, "media_thumbnail") and entry.media_thumbnail:
        return entry.media_thumbnail[0].get("url")
    if hasattr(entry, "media_content") and entry.media_content:
        mc = entry.media_content[0]
        if mc.get("medium") in ("image", None):
            return mc.get("url")
    if hasattr(entry, "summary"):
        soup = BeautifulSoup(entry.summary, "html.parser")
        img = soup.find("img")
        if img and img.get("src"):
            src = img["src"]
            # Skip tracking pixels (tiny images)
            if not any(x in src for x in ["pixel", "beacon", "track", "1x1"]):
                return src
    return None


def clean_html(text: str) -> str:
    if not text:
        return ""
    soup = BeautifulSoup(text, "html.parser")
    return " ".join(soup.get_text().split())[:1200]


# ─── Relevance filter ─────────────────────────────────────────────────────────

def is_ai_relevant(title: str, summary: str, source_name: str, needs_filter: bool) -> bool:
    """
    Return True if the item is AI/ML relevant.
    - AI-only sources always pass.
    - Mixed sources must contain at least one AI keyword in title or summary.
    """
    if not needs_filter:
        return True
    if source_name.lower() in AI_ONLY_SOURCE_NAMES:
        return True

    haystack = f"{title} {summary}".lower()
    return any(kw in haystack for kw in AI_KEYWORDS)


# ─── Ad detection ─────────────────────────────────────────────────────────────

def is_ad(title: str, summary: str, url: str) -> bool:
    """Return True if the item looks like an advertisement or promotional post."""
    text = title.lower()

    # URL segment check
    url_lower = url.lower()
    if any(seg in url_lower for seg in AD_URL_SEGMENTS):
        return True

    # Title pattern check
    for pattern in AD_TITLE_PATTERNS:
        if re.search(pattern, text, re.IGNORECASE):
            return True

    # Very short title with no substance (< 5 words often = promo headline)
    words = title.split()
    if len(words) < 5 and not any(kw in title.lower() for kw in AI_KEYWORDS):
        return True

    # Summary looks purely promotional (no meaningful content)
    if summary and len(summary) < 60 and re.search(r"(sign up|register|free trial|get started)", summary, re.IGNORECASE):
        return True

    return False


# ─── RSS fetcher ──────────────────────────────────────────────────────────────

async def fetch_rss_source(source: Source, needs_filter: bool = True) -> list[dict]:
    """Fetch and parse an RSS feed. Returns filtered, normalised item dicts."""
    items = []
    fetched = rejected_relevance = rejected_ad = 0

    try:
        # Pass the URL directly to feedparser so it handles encoding/charset
        # correctly. Pre-fetching with httpx and passing .text drops charset
        # headers, which causes feedparser to silently return 0 entries on some
        # feeds (confirmed on hnrss.org and a few others).
        import asyncio
        loop = asyncio.get_event_loop()
        feed = await loop.run_in_executor(None, lambda: feedparser.parse(
            source.url,
            agent="Mozilla/5.0 (compatible; AI-News-Bot/1.0)",
            request_headers={"Accept": "application/rss+xml, application/atom+xml, */*"},
        ))

        raw_count = len(feed.entries)

        if raw_count == 0:
            # Log bozo flag and HTTP status to aid debugging
            status  = getattr(feed, "status", "?")
            bozo    = getattr(feed, "bozo", False)
            bozo_ex = str(getattr(feed, "bozo_exception", ""))
            logger.warning(
                f"[{source.name}] RSS returned 0 entries. "
                f"HTTP {status}, bozo={bozo} {bozo_ex!r}"
            )
            return []

        for entry in feed.entries[:40]:
            fetched += 1
            title = clean_title(getattr(entry, "title", "").strip())
            url   = getattr(entry, "link",  "").strip()
            if not title or not url:
                continue

            summary_raw = getattr(entry, "summary", "") or getattr(entry, "description", "")
            summary = clean_html(summary_raw)
            tags = [t.term for t in getattr(entry, "tags", []) if hasattr(t, "term")]

            # ── Filter: ad detection ──────────────────────────────────────────
            if is_ad(title, summary, url):
                rejected_ad += 1
                logger.debug(f"[{source.name}] AD filtered: {title[:60]}")
                continue

            # ── Filter: AI relevance ──────────────────────────────────────────
            if not is_ai_relevant(title, summary, source.name, needs_filter):
                rejected_relevance += 1
                logger.debug(f"[{source.name}] NOT AI-relevant: {title[:60]}")
                continue

            items.append({
                "title":        title,
                "url":          url,
                "summary":      summary,
                "author":       getattr(entry, "author", None),
                "published_at": normalize_date(entry),
                "image_url":    extract_image(entry),
                "tags":         tags[:10],
                "content_hash": compute_hash(title, url),
            })

        logger.info(
            f"[{source.name}] Fetched {raw_count} raw → "
            f"{len(items)} kept, {rejected_relevance} off-topic, {rejected_ad} ads"
        )

    except Exception as e:
        logger.error(f"[{source.name}] RSS fetch failed: {e}")

    return items


# ─── HTML scraper (for non-RSS sources) ───────────────────────────────────────

SCRAPER_CONFIG = {
    "anthropic news": {
        "base_url": "https://www.anthropic.com",
        "article_selector": "a[href*='/news/']",
        "title_selector": "h3, h2, strong",
        "summary_selector": "p",
    },
    "deepmind blog": {
        "base_url": "https://deepmind.google",
        "article_selector": "a[href*='/blog/']",
        "title_selector": "h3, h2",
        "summary_selector": "p",
    },
    "meta ai blog": {
        "base_url": "https://ai.meta.com",
        "article_selector": "a[href*='/blog/']",
        "title_selector": "h3, h2",
        "summary_selector": "p",
    },
}


async def fetch_scraper_source(source: Source, needs_filter: bool) -> list[dict]:
    """
    Generic HTML scraper for sites without RSS.
    Finds article links, extracts title + summary, applies filters.
    """
    items = []
    key = source.name.lower()
    cfg = SCRAPER_CONFIG.get(key, {
        "base_url": source.url,
        "article_selector": "a[href]",
        "title_selector": "h2, h3",
        "summary_selector": "p",
    })

    try:
        async with httpx.AsyncClient(timeout=20.0, follow_redirects=True) as client:
            resp = await client.get(
                source.url,
                headers={"User-Agent": "Mozilla/5.0 (compatible; AI-News-Bot/1.0)"},
            )
            resp.raise_for_status()

        soup = BeautifulSoup(resp.text, "html.parser")

        seen_urls: set[str] = set()
        for a_tag in soup.select(cfg["article_selector"])[:50]:
            href = a_tag.get("href", "").strip()
            if not href:
                continue

            # Resolve relative URLs
            if href.startswith("/"):
                href = cfg["base_url"].rstrip("/") + href
            if not href.startswith("http"):
                continue
            if href in seen_urls:
                continue
            seen_urls.add(href)

            # Extract title: prefer explicit heading inside link, else link text
            title_el = a_tag.find(cfg["title_selector"].split(",")[0].strip())
            raw_title = (title_el.get_text(strip=True) if title_el
                         else a_tag.get_text(strip=True))
            title = clean_title(" ".join(raw_title.split()))
            if not title or len(title) < 10:
                continue

            # Extract summary from sibling/parent paragraph
            parent = a_tag.find_parent(["article", "div", "li", "section"])
            summary = ""
            image_url = None
            if parent:
                p = parent.find("p")
                if p:
                    summary = " ".join(p.get_text(strip=True).split())[:600]
                # Try to grab an image from the card block itself
                img = parent.find("img")
                if img:
                    src = (img.get("src") or img.get("data-src") or "").strip()
                    if src and not any(bad in src.lower() for bad in ["pixel", "beacon", "1x1", "icon"]):
                        if src.startswith("/"):
                            src = cfg["base_url"].rstrip("/") + src
                        if src.startswith("http"):
                            image_url = src

            # Filters
            if is_ad(title, summary, href):
                continue
            if not is_ai_relevant(title, summary, source.name, needs_filter):
                continue

            items.append({
                "title":        title,
                "url":          href,
                "summary":      summary,
                "author":       None,
                "published_at": datetime.now(tz=timezone.utc),
                "image_url":    image_url,
                "tags":         [],
                "content_hash": compute_hash(title, href),
            })

        logger.info(f"[{source.name}] Scraper → {len(items)} items kept")

    except Exception as e:
        logger.error(f"[{source.name}] Scraper failed: {e}")

    return items


# ─── Unified entry point ──────────────────────────────────────────────────────

async def fetch_source(source: Source, needs_filter: bool = True) -> list[dict]:
    """Route to RSS or scraper based on source type."""
    if source.type.value == "scraper":
        return await fetch_scraper_source(source, needs_filter)
    return await fetch_rss_source(source, needs_filter)


# ─── DB helpers ───────────────────────────────────────────────────────────────

def seed_sources(db: Session) -> None:
    """
    Upsert default sources — updates URLs/types on existing records so
    corrected URLs take effect without a DB wipe.
    """
    added = updated = 0
    for s in DEFAULT_SOURCES:
        existing = db.query(Source).filter(Source.name == s["name"]).first()
        if existing:
            changed = False
            if existing.url != s["url"]:
                existing.url = s["url"]
                changed = True
            if existing.type.value != s["type"]:
                from app.models.source import SourceType
                existing.type = SourceType(s["type"])
                changed = True
            if changed:
                updated += 1
        else:
            from app.models.source import SourceType
            db.add(Source(
                name=s["name"],
                url=s["url"],
                type=SourceType(s["type"]),
                active=True,
            ))
            added += 1

    db.commit()
    if added or updated:
        logger.info(f"Sources: {added} added, {updated} updated.")


def save_news_items(db: Session, source: Source, raw_items: list[dict]) -> int:
    """
    Persist news items. Skips duplicates by hash and URL.
    Returns count of newly saved items.
    """
    from sqlalchemy.exc import IntegrityError

    saved = skipped = 0
    for item in raw_items:
        if db.query(NewsItem).filter(NewsItem.content_hash == item["content_hash"]).first():
            skipped += 1
            continue
        if db.query(NewsItem).filter(NewsItem.url == item["url"]).first():
            skipped += 1
            continue

        news = NewsItem(
            source_id=source.id,
            title=item.get("title") or "",
            url=item.get("url") or "",
            summary=item.get("summary"),
            author=item.get("author"),
            published_at=item.get("published_at"),
            image_url=item.get("image_url"),
            tags=item.get("tags") or [],
            content_hash=item.get("content_hash"),
        )

        # Prevent a single duplicate race (from parallel workers) from failing
        # the entire source batch.
        try:
            with db.begin_nested():
                db.add(news)
                db.flush()
            saved += 1
        except IntegrityError:
            skipped += 1
            continue

    db.commit()
    if skipped:
        logger.debug(f"[{source.name}] {skipped} already in DB, {saved} new")
    return saved