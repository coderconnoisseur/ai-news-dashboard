
from pydantic import BaseModel, HttpUrl
from typing import Optional, List
from datetime import datetime
from app.models.source import SourceType


# ─── Source ──────────────────────────────────────────────────────────────────

class SourceBase(BaseModel):
    name: str
    url: str
    type: SourceType = SourceType.RSS
    active: bool = True
    fetch_interval_minutes: int = 15


class SourceCreate(SourceBase):
    pass


class SourceOut(SourceBase):
    id: int
    last_fetched_at: Optional[datetime]
    created_at: datetime

    class Config:
        from_attributes = True


# ─── NewsItem ─────────────────────────────────────────────────────────────────

class NewsItemBase(BaseModel):
    title: str
    summary: Optional[str]
    url: str
    author: Optional[str]
    image_url: Optional[str]
    published_at: Optional[datetime]
    tags: Optional[List[str]] = []


class NewsItemOut(NewsItemBase):
    id: int
    source_id: int
    ai_summary: Optional[str]
    is_duplicate: bool
    impact_score: Optional[float]
    fetched_at: datetime
    is_favorited: bool = False
    source_name: Optional[str] = None

    class Config:
        from_attributes = True


class NewsListResponse(BaseModel):
    items: List[NewsItemOut]
    total: int
    page: int
    page_size: int
    has_more: bool


# ─── Favorite ────────────────────────────────────────────────────────────────

class FavoriteOut(BaseModel):
    id: int
    news_item_id: int
    created_at: datetime
    news_item: NewsItemOut

    class Config:
        from_attributes = True