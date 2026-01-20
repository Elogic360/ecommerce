"""
Wishlist Router
CRUD endpoints for user wishlists with price tracking.
"""
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import select, func

from app.db.session import get_db
from app.models.customer import User
from app.models.product import Product
from app.models.features import Wishlist
from app.schemas.features import WishlistItem, WishlistItemCreate, WishlistResponse
from app.core.security import get_current_user

router = APIRouter(prefix="/wishlist", tags=["wishlist"])


@router.get("", response_model=WishlistResponse)
def get_wishlist(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get current user's wishlist"""
    items = db.query(Wishlist).filter(Wishlist.user_id == current_user.id).all()
    # Convert ORM objects to Pydantic via from_attributes
    return WishlistResponse(items=items, total=len(items))  # type: ignore[arg-type]


@router.post("/{product_id}", response_model=WishlistItem, status_code=status.HTTP_201_CREATED)
def add_to_wishlist(
    product_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Add a product to wishlist"""
    # Check product exists
    product = db.query(Product).filter(Product.id == product_id, Product.is_active == True).first()
    if not product:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")

    # Check if already in wishlist
    existing = db.query(Wishlist).filter(
        Wishlist.user_id == current_user.id,
        Wishlist.product_id == product_id
    ).first()
    if existing:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Product already in wishlist")

    wishlist_item = Wishlist(
        user_id=current_user.id,
        product_id=product_id,
        price_at_addition=product.price,
        notify_on_price_drop=True,
    )
    db.add(wishlist_item)
    db.commit()
    db.refresh(wishlist_item)
    return wishlist_item


@router.delete("/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_from_wishlist(
    product_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Remove a product from wishlist"""
    item = db.query(Wishlist).filter(
        Wishlist.user_id == current_user.id,
        Wishlist.product_id == product_id
    ).first()
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not in wishlist")

    db.delete(item)
    db.commit()


@router.get("/price-drops", response_model=List[WishlistItem])
def get_price_drops(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get wishlist items where price has dropped"""
    items = (
        db.query(Wishlist)
        .join(Product)
        .filter(
            Wishlist.user_id == current_user.id,
            Wishlist.notify_on_price_drop == True,
            Product.price < Wishlist.price_at_addition,
        )
        .all()
    )
    return items


@router.patch("/{product_id}/notify", response_model=WishlistItem)
def toggle_price_notification(
    product_id: int,
    notify: bool,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Toggle price drop notification for wishlist item"""
    item = db.query(Wishlist).filter(
        Wishlist.user_id == current_user.id,
        Wishlist.product_id == product_id
    ).first()
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not in wishlist")

    setattr(item, 'notify_on_price_drop', notify)
    db.commit()
    db.refresh(item)
    return item
