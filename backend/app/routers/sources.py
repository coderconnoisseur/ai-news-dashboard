from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from app.database import get_db
from app.models import Source
from app.schemas.news import SourceCreate, SourceOut
from app.services.ingestion import seed_sources

router = APIRouter(prefix="/sources", tags=["sources"])


@router.get("/", response_model=List[SourceOut])
def list_sources(db: Session = Depends(get_db)):
    return db.query(Source).order_by(Source.name).all()


@router.post("/", response_model=SourceOut, status_code=201)
def create_source(payload: SourceCreate, db: Session = Depends(get_db)):
    existing = db.query(Source).filter(Source.url == payload.url).first()
    if existing:
        raise HTTPException(status_code=409, detail="Source with this URL already exists")
    source = Source(**payload.model_dump())
    db.add(source)
    db.commit()
    db.refresh(source)
    return source


@router.patch("/{source_id}/toggle", response_model=SourceOut)
def toggle_source(source_id: int, db: Session = Depends(get_db)):
    source = db.query(Source).filter(Source.id == source_id).first()
    if not source:
        raise HTTPException(status_code=404, detail="Source not found")
    source.active = not source.active
    db.commit()
    db.refresh(source)
    return source


@router.delete("/{source_id}")
def delete_source(source_id: int, db: Session = Depends(get_db)):
    source = db.query(Source).filter(Source.id == source_id).first()
    if not source:
        raise HTTPException(status_code=404, detail="Source not found")
    db.delete(source)
    db.commit()
    return {"message": "Source deleted"}


@router.post("/seed")
def seed(db: Session = Depends(get_db)):
    """Seed default sources (safe to call multiple times)."""
    seed_sources(db)
    return {"message": "Sources seeded", "count": db.query(Source).count()}