"""
Deduplication service.
Strategy: TF-IDF cosine similarity on titles for near-duplicate detection.
Falls back to simple Jaccard similarity if sklearn not available.
"""
import logging
import re
from typing import List, Tuple
from datetime import datetime, timedelta, timezone
from sqlalchemy.orm import Session
from app.models import NewsItem
from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


def tokenize(text: str) -> set:
    """Simple tokenizer: lowercase, alphanumeric only."""
    return set(re.findall(r'\b[a-z0-9]+\b', text.lower()))


def jaccard_similarity(a: str, b: str) -> float:
    """Jaccard similarity between two title strings."""
    tokens_a = tokenize(a)
    tokens_b = tokenize(b)
    if not tokens_a or not tokens_b:
        return 0.0
    intersection = tokens_a & tokens_b
    union = tokens_a | tokens_b
    return len(intersection) / len(union)


def find_duplicates(db: Session, lookback_hours: int = 48) -> int:
    """
    Scan recent news items and mark duplicates.
    An item is a duplicate if it has jaccard_similarity >= threshold with
    an earlier item (by published_at / fetched_at).

    Returns number of items marked as duplicate.
    """
    threshold = settings.DEDUP_SIMILARITY_THRESHOLD
    cutoff = datetime.now(tz=timezone.utc) - timedelta(hours=lookback_hours)

    items: List[NewsItem] = (
        db.query(NewsItem)
        .filter(NewsItem.fetched_at >= cutoff, NewsItem.is_duplicate == False)
        .order_by(NewsItem.published_at.asc())
        .all()
    )

    marked = 0
    # Compare each item against all earlier items
    for i, item in enumerate(items):
        for earlier in items[:i]:
            if earlier.is_duplicate:
                continue
            score = jaccard_similarity(item.title, earlier.title)
            if score >= threshold:
                item.is_duplicate = True
                item.duplicate_of_id = earlier.id
                item.similarity_score = score
                marked += 1
                break  # Only mark once

    db.commit()
    logger.info(f"Dedup scan: {marked} duplicates marked out of {len(items)} items.")
    return marked


def get_dedup_stats(db: Session) -> dict:
    total = db.query(NewsItem).count()
    dupes = db.query(NewsItem).filter(NewsItem.is_duplicate == True).count()
    return {
        "total_items": total,
        "duplicate_items": dupes,
        "unique_items": total - dupes,
        "dedup_rate": round(dupes / total, 3) if total else 0,
    }