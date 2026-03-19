from pydantic import BaseModel, EmailStr
from typing import Optional, List
from datetime import datetime
from app.models.favorite import BroadcastPlatform, BroadcastStatus


class BroadcastRequest(BaseModel):
    favorite_ids: List[int]
    platform: BroadcastPlatform
    # Email-specific
    recipient_email: Optional[str] = None
    subject: Optional[str] = None
    # LinkedIn-specific
    generate_caption: bool = True
    # WhatsApp-specific
    phone_number: Optional[str] = None
    group_id: Optional[str] = None


class BroadcastResult(BaseModel):
    platform: BroadcastPlatform
    status: BroadcastStatus
    message: str
    generated_content: Optional[str] = None  # AI-generated caption / email body
    log_ids: List[int] = []


class BroadcastLogOut(BaseModel):
    id: int
    favorite_id: int
    platform: BroadcastPlatform
    status: BroadcastStatus
    timestamp: datetime
    error_message: Optional[str]

    class Config:
        from_attributes = True