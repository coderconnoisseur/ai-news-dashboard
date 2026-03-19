from sqlalchemy import (
    Column, Integer, String, Text, Boolean,
    DateTime, ForeignKey, Float, ARRAY
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base


class NewsItem(Base):
    __tablename__ = "news_items"

    id = Column(Integer, primary_key=True, index=True)
    source_id = Column(Integer, ForeignKey("sources.id"), nullable=False)

    # Content
    title = Column(Text, nullable=False)           # Text: arXiv titles exceed 500 chars
    summary = Column(Text, nullable=True)
    ai_summary = Column(Text, nullable=True)
    url = Column(Text, nullable=False, unique=True)
    author = Column(Text, nullable=True)
    image_url = Column(Text, nullable=True)

    # Metadata
    published_at = Column(DateTime(timezone=True), nullable=True)
    fetched_at = Column(DateTime(timezone=True), server_default=func.now())
    tags = Column(ARRAY(String), nullable=True, default=[])

    # Dedup & clustering
    is_duplicate = Column(Boolean, default=False)
    duplicate_of_id = Column(Integer, ForeignKey("news_items.id"), nullable=True)
    cluster_id = Column(String(100), nullable=True)
    content_hash = Column(String(64), nullable=True, index=True)  # SHA-256 of title+url
    similarity_score = Column(Float, nullable=True)

    # Scoring
    impact_score = Column(Float, nullable=True)   # AI-assigned 0-10

    # Relationships
    source = relationship("Source", back_populates="news_items")
    favorites = relationship("Favorite", back_populates="news_item")
    duplicate_original = relationship("NewsItem", remote_side=[id])

    def __repr__(self):
        return f"<NewsItem {self.title[:50]}>"