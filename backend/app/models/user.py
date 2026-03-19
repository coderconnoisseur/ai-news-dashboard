from sqlalchemy import Column, Integer, String, Enum, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum
from app.database import Base


class UserRole(str, enum.Enum):
    ADMIN = "admin"
    VIEWER = "viewer"


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False)
    email = Column(String(300), unique=True, nullable=False, index=True)
    role = Column(
        Enum(
            UserRole,
            name="userrole",
            values_callable=lambda enum_cls: [member.value for member in enum_cls],
            create_type=False,
        ),
        default=UserRole.VIEWER,
    )
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    favorites = relationship("Favorite", back_populates="user")