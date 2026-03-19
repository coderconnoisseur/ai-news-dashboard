from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from app.database import get_db
from app.schemas.broadcast import BroadcastRequest, BroadcastResult, BroadcastLogOut
from app.models import BroadcastLog, BroadcastPlatform
from app.services import broadcast_service

router = APIRouter(prefix="/broadcast", tags=["broadcast"])


@router.post("/", response_model=BroadcastResult)
def broadcast(payload: BroadcastRequest, db: Session = Depends(get_db)):
    """
    Broadcast selected favorites to a platform.
    Supports: email, linkedin, whatsapp, newsletter.
    """
    if not payload.favorite_ids:
        raise HTTPException(status_code=400, detail="No favorites selected")

    platform = payload.platform

    if platform == BroadcastPlatform.EMAIL:
        if not payload.recipient_email:
            raise HTTPException(status_code=400, detail="recipient_email required for email broadcast")
        result = broadcast_service.broadcast_email(
            db,
            payload.favorite_ids,
            payload.recipient_email,
            payload.subject or "Your AI News Digest",
        )
    elif platform == BroadcastPlatform.LINKEDIN:
        result = broadcast_service.broadcast_linkedin(
            db, payload.favorite_ids, payload.generate_caption
        )
    elif platform == BroadcastPlatform.WHATSAPP:
        result = broadcast_service.broadcast_whatsapp(
            db, payload.favorite_ids, payload.phone_number
        )
    elif platform == BroadcastPlatform.NEWSLETTER:
        from app.services.ai_service import generate_newsletter_content
        from app.services.broadcast_service import _get_items_data
        from app.models import BroadcastStatus
        items = _get_items_data(db, payload.favorite_ids)
        content = generate_newsletter_content(items)
        result = {
            "status": BroadcastStatus.SIMULATED,
            "message": "Newsletter content generated",
            "generated_content": content,
            "log_ids": [],
        }
    else:
        raise HTTPException(status_code=400, detail=f"Unsupported platform: {platform}")

    return BroadcastResult(
        platform=platform,
        status=result["status"],
        message=result["message"],
        generated_content=result.get("generated_content"),
        log_ids=result.get("log_ids", []),
    )


@router.get("/logs", response_model=List[BroadcastLogOut])
def get_broadcast_logs(limit: int = 50, db: Session = Depends(get_db)):
    """Fetch recent broadcast history."""
    logs = (
        db.query(BroadcastLog)
        .order_by(BroadcastLog.timestamp.desc())
        .limit(limit)
        .all()
    )
    return logs