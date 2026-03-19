from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import desc, asc, or_
from typing import Optional, List
from datetime import datetime, timedelta, timezone

from app.database import get_db
from app.models import NewsItem, Source, Favorite
from app.schemas.news import NewsItemOut, NewsListResponse
from app.workers.fetcher import run_fetch_cycle
import asyncio

router = APIRouter(prefix="/news", tags=["news"])


def _build_query(db: Session, exclude_dupes: bool = True):
    q = db.query(NewsItem).options(joinedload(NewsItem.source))
    if exclude_dupes:
        q = q.filter(NewsItem.is_duplicate == False)
    return q


@router.get("/feed", response_model=NewsListResponse)
def get_feed(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=5, le=100),
    sort_by: str = Query("date", enum=["date", "source", "impact"]),
    sort_order: str = Query("desc", enum=["asc", "desc"]),
    source_id: Optional[int] = None,
    tags: Optional[str] = None,           # comma-separated
    search: Optional[str] = None,
    days_back: int = Query(7, ge=1, le=30),
    include_dupes: bool = False,
    db: Session = Depends(get_db),
):
    """Main feed endpoint with filtering, search, and pagination."""
    q = _build_query(db, exclude_dupes=not include_dupes)

    # Date filter
    cutoff = datetime.now(tz=timezone.utc) - timedelta(days=days_back)
    q = q.filter(NewsItem.fetched_at >= cutoff)

    # Source filter
    if source_id:
        q = q.filter(NewsItem.source_id == source_id)

    # Tag filter
    if tags:
        tag_list = [t.strip() for t in tags.split(",")]
        q = q.filter(NewsItem.tags.overlap(tag_list))

    # Search
    if search:
        q = q.filter(
            or_(
                NewsItem.title.ilike(f"%{search}%"),
                NewsItem.summary.ilike(f"%{search}%"),
                NewsItem.ai_summary.ilike(f"%{search}%"),
            )
        )

    # Sort
    sort_col = {
        "date": NewsItem.published_at,
        "source": NewsItem.source_id,
        "impact": NewsItem.impact_score,
    }.get(sort_by, NewsItem.published_at)

    q = q.order_by(desc(sort_col) if sort_order == "desc" else asc(sort_col))

    total = q.count()
    items = q.offset((page - 1) * page_size).limit(page_size).all()

    # Enrich with favorite status (no user auth for MVP - check if any favorite exists)
    favorited_ids = {
        f.news_item_id for f in db.query(Favorite).filter(
            Favorite.news_item_id.in_([i.id for i in items])
        ).all()
    }

    results = []
    for item in items:
        out = NewsItemOut.model_validate(item)
        out.is_favorited = item.id in favorited_ids
        out.source_name = item.source.name if item.source else None
        results.append(out)

    return NewsListResponse(
        items=results,
        total=total,
        page=page,
        page_size=page_size,
        has_more=(page * page_size) < total,
    )


@router.get("/{news_id}", response_model=NewsItemOut)
def get_news_item(news_id: int, db: Session = Depends(get_db)):
    item = db.query(NewsItem).options(joinedload(NewsItem.source)).filter(
        NewsItem.id == news_id
    ).first()
    if not item:
        raise HTTPException(status_code=404, detail="News item not found")
    out = NewsItemOut.model_validate(item)
    out.source_name = item.source.name if item.source else None
    return out


@router.post("/refresh")
async def refresh_feed():
    """Manually trigger a fetch cycle."""
    asyncio.create_task(run_fetch_cycle())
    return {"message": "Fetch cycle triggered in background"}


@router.get("/stats/summary")
def get_stats(db: Session = Depends(get_db)):
    from app.services.dedup import get_dedup_stats
    stats = get_dedup_stats(db)
    stats["sources_active"] = db.query(Source).filter(Source.active == True).count()
    stats["total_sources"] = db.query(Source).count()
    return stats