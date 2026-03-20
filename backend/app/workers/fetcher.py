"""
Background worker: scheduled RSS fetch + dedup + enrichment.
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
from app.services.image_service import enrich_missing_images
from app.services.title_service import enrich_titles
from app.config import get_settings
from datetime import datetime, timezone

logger = logging.getLogger(__name__)
settings = get_settings()

scheduler = AsyncIOScheduler()


async def run_fetch_cycle():
    """
    Full pipeline per cycle:
      1. Fetch + filter all active sources
      2. Save new items (Stage-1 title cleaning applied at parse time)
      3. Dedup pass
      4. Image enrichment  — fetch og:image for items missing thumbnails
      5. Title enrichment  — Stage-1 regex + optional Stage-2 LLM polish
    """
    db: Session = SessionLocal()

    filter_map = {s["name"]: s.get("needs_filter", True) for s in DEFAULT_SOURCES}

    try:
        # Step 1 + 2: fetch and save
        sources = db.query(Source).filter(Source.active == True).all()
        total_new = 0

        for source in sources:
            needs_filter = filter_map.get(source.name, True)
            raw_items = await fetch_source(source, needs_filter=needs_filter)
            new_count = save_news_items(db, source, raw_items)
            source.last_fetched_at = datetime.now(tz=timezone.utc)
            db.commit()
            total_new += new_count

        # Step 3: dedup
        dupes = find_duplicates(db)

        # Step 4: image enrichment
        images_found = 0
        if total_new > 0:
            try:
                images_found = await enrich_missing_images(db)
            except Exception as e:
                logger.warning(f"Image enrichment error: {e}")

        # Step 5: title enrichment
        titles_updated = 0
        if total_new > 0:
            try:
                titles_updated = enrich_titles(db, use_llm=bool(settings.ANTHROPIC_API_KEY))
            except Exception as e:
                logger.warning(f"Title enrichment error: {e}")

        logger.info(
            f"Fetch cycle done: {total_new} new items, {dupes} dupes, "
            f"{images_found} images found, {titles_updated} titles polished."
        )

    except Exception as e:
        logger.error(f"Fetch cycle error: {e}")
    finally:
        db.close()


def start_scheduler():
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
    if scheduler.running:
        scheduler.shutdown(wait=False)