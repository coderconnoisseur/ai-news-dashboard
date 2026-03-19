from sqlalchemy import Column, Integer, ForeignKey, DateTime, String, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum
from app.database import Base


class Favorite(Base):
    __tablename__ = "favorites"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)  # nullable for single-user MVP
    news_item_id = Column(Integer, ForeignKey("news_items.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    news_item = relationship("NewsItem", back_populates="favorites")
    user = relationship("User", back_populates="favorites")
    broadcast_logs = relationship("BroadcastLog", back_populates="favorite")


class BroadcastPlatform(str, enum.Enum):
    EMAIL = "email"
    LINKEDIN = "linkedin"
    WHATSAPP = "whatsapp"
    BLOG = "blog"
    NEWSLETTER = "newsletter"


class BroadcastStatus(str, enum.Enum):
    PENDING = "pending"
    SUCCESS = "success"
    FAILED = "failed"
    SIMULATED = "simulated"


class BroadcastLog(Base):
    __tablename__ = "broadcast_logs"

    id = Column(Integer, primary_key=True, index=True)
    favorite_id = Column(Integer, ForeignKey("favorites.id"), nullable=False)
    platform = Column(
        Enum(
            BroadcastPlatform,
            name="broadcastplatform",
            values_callable=lambda enum_cls: [member.value for member in enum_cls],
            create_type=False,
        ),
        nullable=False,
    )
    status = Column(
        Enum(
            BroadcastStatus,
            name="broadcaststatus",
            values_callable=lambda enum_cls: [member.value for member in enum_cls],
            create_type=False,
        ),
        default=BroadcastStatus.PENDING,
    )
    payload = Column(String(5000), nullable=True)   # JSON-serialized content sent
    error_message = Column(String(1000), nullable=True)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())

    favorite = relationship("Favorite", back_populates="broadcast_logs")