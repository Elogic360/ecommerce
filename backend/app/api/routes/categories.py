from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List
from app.db.session import get_db
from app.schemas.product import Category
from app.models.product import Category as CategoryModel

router = APIRouter()

@router.get("/categories", response_model=List[Category])
def get_categories(db: Session = Depends(get_db)):
    categories = db.query(CategoryModel).all()
    return categories

@router.get("/categories/{id}", response_model=Category)
def get_category(id: int, db: Session = Depends(get_db)):
    category = db.query(CategoryModel).filter(CategoryModel.id == id).first()
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")
    return category
