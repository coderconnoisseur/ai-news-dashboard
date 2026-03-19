from sqlalchemy import Column, Integer, String, Boolean, DateTime, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum
from app.database import Base


class SourceType(str, enum.Enum):
    RSS = "rss"
    API = "api"
    SCRAPER = "scraper"
    YOUTUBE = "youtube"
    REDDIT = "reddit"


class Source(Base):
    __tablename__ = "sources"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False)
    url = Column(String(500), nullable=False, unique=True)
    type = Column(
        Enum(
            SourceType,
            name="sourcetype",
            values_callable=lambda enum_cls: [member.value for member in enum_cls],
            create_type=False,
        ),
        default=SourceType.RSS,
    )
    active = Column(Boolean, default=True)
    fetch_interval_minutes = Column(Integer, default=15)
    last_fetched_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    news_items = relationship("NewsItem", back_populates="source")

    def __repr__(self):
        return f"<Source {self.name}>"