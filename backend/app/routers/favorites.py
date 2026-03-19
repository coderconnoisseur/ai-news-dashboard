from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload
from typing import List

from app.database import get_db
from app.models import Favorite, NewsItem
from app.schemas.news import FavoriteOut, NewsItemOut

router = APIRouter(prefix="/favorites", tags=["favorites"])


@router.get("/", response_model=List[FavoriteOut])
def list_favorites(db: Session = Depends(get_db)):
    """Return all favorited items with full news data."""
    favorites = (
        db.query(Favorite)
        .options(joinedload(Favorite.news_item).joinedload(NewsItem.source))
        .order_by(Favorite.created_at.desc())
        .all()
    )
    results = []
    for fav in favorites:
        item_out = NewsItemOut.model_validate(fav.news_item)
        item_out.source_name = fav.news_item.source.name if fav.news_item.source else None
        item_out.is_favorited = True
        results.append(FavoriteOut(
            id=fav.id,
            news_item_id=fav.news_item_id,
            created_at=fav.created_at,
            news_item=item_out,
        ))
    return results


@router.post("/{news_item_id}", response_model=FavoriteOut)
def add_favorite(news_item_id: int, db: Session = Depends(get_db)):
    """Add a news item to favorites."""
    item = db.query(NewsItem).filter(NewsItem.id == news_item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="News item not found")

    existing = db.query(Favorite).filter(Favorite.news_item_id == news_item_id).first()
    if existing:
        raise HTTPException(status_code=409, detail="Already in favorites")

    fav = Favorite(news_item_id=news_item_id)
    db.add(fav)
    db.commit()
    db.refresh(fav)

    # Reload with relationships
    fav = db.query(Favorite).options(
        joinedload(Favorite.news_item).joinedload(NewsItem.source)
    ).filter(Favorite.id == fav.id).first()

    item_out = NewsItemOut.model_validate(fav.news_item)
    item_out.source_name = fav.news_item.source.name if fav.news_item.source else None
    item_out.is_favorited = True

    return FavoriteOut(
        id=fav.id,
        news_item_id=fav.news_item_id,
        created_at=fav.created_at,
        news_item=item_out,
    )


@router.delete("/{news_item_id}")
def remove_favorite(news_item_id: int, db: Session = Depends(get_db)):
    """Remove a news item from favorites."""
    fav = db.query(Favorite).filter(Favorite.news_item_id == news_item_id).first()
    if not fav:
        raise HTTPException(status_code=404, detail="Favorite not found")
    db.delete(fav)
    db.commit()
    return {"message": "Removed from favorites", "news_item_id": news_item_id}