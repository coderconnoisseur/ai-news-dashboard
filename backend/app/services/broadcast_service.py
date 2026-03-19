"""
Broadcast service: sends favorites via Email, LinkedIn, WhatsApp.
Email: real SMTP. LinkedIn & WhatsApp: simulated with mock responses for MVP.
"""
import json
import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import List
from sqlalchemy.orm import Session

from app.models import Favorite, BroadcastLog, BroadcastPlatform, BroadcastStatus
from app.services.ai_service import (
    generate_linkedin_post, generate_email_body, generate_newsletter_content
)
from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


def _get_items_data(db: Session, favorite_ids: List[int]) -> List[dict]:
    """Fetch favorites with their news items."""
    favorites = db.query(Favorite).filter(Favorite.id.in_(favorite_ids)).all()
    return [
        {
            "favorite_id": f.id,
            "title": f.news_item.title,
            "summary": f.news_item.ai_summary or f.news_item.summary or "",
            "url": f.news_item.url,
            "source_name": f.news_item.source.name if f.news_item.source else "",
        }
        for f in favorites if f.news_item
    ]


def _log_broadcast(
    db: Session,
    favorite_id: int,
    platform: BroadcastPlatform,
    status: BroadcastStatus,
    payload: str = "",
    error: str = None,
) -> BroadcastLog:
    log = BroadcastLog(
        favorite_id=favorite_id,
        platform=platform,
        status=status,
        payload=payload[:5000] if payload else "",
        error_message=error,
    )
    db.add(log)
    db.commit()
    return log


# ─── Email ────────────────────────────────────────────────────────────────────

def broadcast_email(
    db: Session,
    favorite_ids: List[int],
    recipient_email: str,
    subject: str = "Your AI News Digest",
) -> dict:
    items = _get_items_data(db, favorite_ids)
    body = generate_email_body(items)
    log_ids = []

    try:
        if settings.SMTP_USER and settings.SMTP_PASSWORD:
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = settings.EMAIL_FROM
            msg["To"] = recipient_email
            msg.attach(MIMEText(body, "plain"))

            with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
                server.starttls()
                server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
                server.sendmail(settings.EMAIL_FROM, recipient_email, msg.as_string())

            status = BroadcastStatus.SUCCESS
            message = f"Email sent to {recipient_email}"
        else:
            # Simulate
            status = BroadcastStatus.SIMULATED
            message = f"[SIMULATED] Email would be sent to {recipient_email}"

        for fid in favorite_ids:
            log = _log_broadcast(db, fid, BroadcastPlatform.EMAIL, status, body)
            log_ids.append(log.id)

    except Exception as e:
        for fid in favorite_ids:
            log = _log_broadcast(db, fid, BroadcastPlatform.EMAIL,
                                 BroadcastStatus.FAILED, error=str(e))
            log_ids.append(log.id)
        message = f"Email failed: {e}"
        status = BroadcastStatus.FAILED

    return {"status": status, "message": message, "generated_content": body, "log_ids": log_ids}


# ─── LinkedIn ─────────────────────────────────────────────────────────────────

def broadcast_linkedin(
    db: Session,
    favorite_ids: List[int],
    generate_caption: bool = True,
) -> dict:
    items = _get_items_data(db, favorite_ids)
    caption = generate_linkedin_post(items) if generate_caption else \
              "\n".join(f"- {i['title']}" for i in items)

    log_ids = []
    # LinkedIn API is simulated for MVP
    status = BroadcastStatus.SIMULATED
    message = "[SIMULATED] LinkedIn post ready. Copy caption to post manually."

    for fid in favorite_ids:
        log = _log_broadcast(db, fid, BroadcastPlatform.LINKEDIN, status, caption)
        log_ids.append(log.id)

    return {"status": status, "message": message, "generated_content": caption, "log_ids": log_ids}


# ─── WhatsApp ─────────────────────────────────────────────────────────────────

def broadcast_whatsapp(
    db: Session,
    favorite_ids: List[int],
    phone_number: str = None,
) -> dict:
    items = _get_items_data(db, favorite_ids)
    text = "🤖 *AI News Update*\n\n" + \
           "\n".join(f"📰 *{i['title']}*\n{i['url']}" for i in items[:5])

    log_ids = []
    status = BroadcastStatus.SIMULATED
    message = "[SIMULATED] WhatsApp message composed. Integrate with WhatsApp Business API."

    for fid in favorite_ids:
        log = _log_broadcast(db, fid, BroadcastPlatform.WHATSAPP, status, text)
        log_ids.append(log.id)

    return {"status": status, "message": message, "generated_content": text, "log_ids": log_ids}