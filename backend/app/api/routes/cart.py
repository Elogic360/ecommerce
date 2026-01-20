from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from app.db.session import get_db
from app.schemas.cart import CartItem, CartItemCreate, CartItemUpdate
from app.models.cart import CartItem as CartItemModel
from app.core.security import get_current_user
from app.models.customer import User

router = APIRouter()

@router.get("/cart", response_model=List[CartItem])
def get_cart(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    cart_items = db.query(CartItemModel).filter(CartItemModel.user_id == current_user.id).all()
    return cart_items

@router.post("/cart", response_model=CartItem)
def add_to_cart(item: CartItemCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    db_item = db.query(CartItemModel).filter(
        CartItemModel.user_id == current_user.id,
        CartItemModel.product_id == item.product_id,
        CartItemModel.variation_id == item.variation_id
    ).first()

    if db_item:
        db_item.quantity += item.quantity
    else:
        db_item = CartItemModel(**item.dict(), user_id=current_user.id)
        db.add(db_item)
    
    db.commit()
    db.refresh(db_item)
    return db_item

@router.put("/cart/{id}", response_model=CartItem)
def update_cart_item(id: int, item: CartItemUpdate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    db_item = db.query(CartItemModel).filter(CartItemModel.id == id, CartItemModel.user_id == current_user.id).first()
    if not db_item:
        raise HTTPException(status_code=404, detail="Cart item not found")
    
    db_item.quantity = item.quantity
    db.commit()
    db.refresh(db_item)
    return db_item

@router.delete("/cart/{id}", status_code=204)
def remove_from_cart(id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    db_item = db.query(CartItemModel).filter(CartItemModel.id == id, CartItemModel.user_id == current_user.id).first()
    if not db_item:
        raise HTTPException(status_code=404, detail="Cart item not found")
    
    db.delete(db_item)
    db.commit()
    return

@router.delete("/cart", status_code=204)
def clear_cart(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    db.query(CartItemModel).filter(CartItemModel.user_id == current_user.id).delete()
    db.commit()
    return