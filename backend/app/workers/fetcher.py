"""
Background worker: scheduled RSS fetch + dedup run.
Uses APScheduler to run every N minutes.
"""
import asyncio
import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.models import Source
from app.services.ingestion import fetch_source, save_news_items, DEFAULT_SOURCES
from app.services.dedup import find_duplicates
from app.config import get_settings
from datetime import datetime, timezone

logger = logging.getLogger(__name__)
settings = get_settings()

scheduler = AsyncIOScheduler()


async def run_fetch_cycle():
    """Fetch all active sources, save items, run dedup."""
    db: Session = SessionLocal()

    # Build a lookup of needs_filter by source name from the registry
    filter_map = {s["name"]: s.get("needs_filter", True) for s in DEFAULT_SOURCES}

    try:
        sources = db.query(Source).filter(Source.active == True).all()
        total_new = 0

        for source in sources:
            needs_filter = filter_map.get(source.name, True)
            raw_items = await fetch_source(source, needs_filter=needs_filter)
            new_count = save_news_items(db, source, raw_items)
            source.last_fetched_at = datetime.now(tz=timezone.utc)
            db.commit()
            total_new += new_count

        # Run dedup after all fetches
        dupes = find_duplicates(db)
        logger.info(f"Fetch cycle done: {total_new} new items, {dupes} duplicates marked.")

    except Exception as e:
        logger.error(f"Fetch cycle error: {e}")
    finally:
        db.close()


def start_scheduler():
    """Start background scheduler."""
    scheduler.add_job(
        run_fetch_cycle,
        trigger="interval",
        minutes=settings.FETCH_INTERVAL_MINUTES,
        id="fetch_cycle",
        replace_existing=True,
    )
    scheduler.start()
    logger.info(f"Scheduler started (interval: {settings.FETCH_INTERVAL_MINUTES}m)")


def stop_scheduler():
    """Graceful shutdown."""
    if scheduler.running:
        scheduler.shutdown(wait=False)