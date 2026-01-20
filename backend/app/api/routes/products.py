from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session
from typing import List, Optional
from app.db.session import get_db
from app.schemas.product import Product, ProductCreate, ProductUpdate, Review, ReviewCreate
from app.models.product import Product as ProductModel, Category as CategoryModel, Review as ReviewModel, ProductImage as ProductImageModel
from app.core.security import get_current_admin_user, get_current_user
from app.models.customer import User
import shutil
import os

router = APIRouter()

# Public endpoints
@router.get("/products", response_model=List[Product])
def get_products(
    skip: int = 0,
    limit: int = 20,
    search: Optional[str] = None,
    category_id: Optional[int] = None,
    min_price: Optional[float] = None,
    max_price: Optional[float] = None,
    sort_by: Optional[str] = None,
    sort_order: str = "asc",
    is_featured: Optional[bool] = None,
    db: Session = Depends(get_db)
):
    query = db.query(ProductModel)
    if search:
        query = query.filter(ProductModel.name.ilike(f"%{search}%"))
    if category_id:
        query = query.join(ProductModel.categories).filter(CategoryModel.id == category_id)
    if min_price:
        query = query.filter(ProductModel.price >= min_price)
    if max_price:
        query = query.filter(ProductModel.price <= max_price)
    if is_featured is not None:
        query = query.filter(ProductModel.is_featured == is_featured)

    if sort_by:
        if hasattr(ProductModel, sort_by):
            field = getattr(ProductModel, sort_by)
            if sort_order == "desc":
                query = query.order_by(field.desc())
            else:
                query = query.order_by(field.asc())

    products = query.offset(skip).limit(limit).all()
    return products

@router.get("/products/{id}", response_model=Product)
def get_product(id: int, db: Session = Depends(get_db)):
    product = db.query(ProductModel).filter(ProductModel.id == id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return product

@router.get("/products/{id}/reviews", response_model=List[Review])
def get_product_reviews(id: int, skip: int = 0, limit: int = 10, db: Session = Depends(get_db)):
    reviews = db.query(ReviewModel).filter(ReviewModel.product_id == id).offset(skip).limit(limit).all()
    return reviews

@router.post("/products/{id}/reviews", response_model=Review)
def create_review(id: int, review: ReviewCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    product = db.query(ProductModel).filter(ProductModel.id == id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    db_review = ReviewModel(**review.dict(), product_id=id, user_id=current_user.id)
    db.add(db_review)
    db.commit()
    db.refresh(db_review)

    # Update product rating
    reviews = db.query(ReviewModel).filter(ReviewModel.product_id == id).all()
    product.rating = sum([r.rating for r in reviews]) / len(reviews)
    product.review_count = len(reviews)
    db.commit()

    return db_review

# Admin endpoints
@router.post("/admin/products", response_model=Product, dependencies=[Depends(get_current_admin_user)])
def create_product(product: ProductCreate, db: Session = Depends(get_db)):
    db_product = ProductModel(**product.dict(exclude={"category_ids"}))
    if product.category_ids:
        categories = db.query(CategoryModel).filter(CategoryModel.id.in_(product.category_ids)).all()
        db_product.categories = categories
    db.add(db_product)
    db.commit()
    db.refresh(db_product)
    return db_product

@router.put("/admin/products/{id}", response_model=Product, dependencies=[Depends(get_current_admin_user)])
def update_product(id: int, product: ProductUpdate, db: Session = Depends(get_db)):
    db_product = db.query(ProductModel).filter(ProductModel.id == id).first()
    if not db_product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    update_data = product.dict(exclude_unset=True, exclude={"category_ids"})
    for key, value in update_data.items():
        setattr(db_product, key, value)

    if product.category_ids:
        categories = db.query(CategoryModel).filter(CategoryModel.id.in_(product.category_ids)).all()
        db_product.categories = categories

    db.commit()
    db.refresh(db_product)
    return db_product

@router.delete("/admin/products/{id}", status_code=204, dependencies=[Depends(get_current_admin_user)])
def delete_product(id: int, db: Session = Depends(get_db)):
    product = db.query(ProductModel).filter(ProductModel.id == id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    db.delete(product)
    db.commit()
    return

@router.post("/admin/products/{id}/images", response_model=Product, dependencies=[Depends(get_current_admin_user)])
def upload_image(id: int, file: UploadFile = File(...), is_primary: bool = Form(False), db: Session = Depends(get_db)):
    product = db.query(ProductModel).filter(ProductModel.id == id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    upload_dir = f"uploads/products/{id}"
    os.makedirs(upload_dir, exist_ok=True)
    file_path = os.path.join(upload_dir, file.filename)
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    image_url = f"/uploads/products/{id}/{file.filename}"

    if is_primary:
        product.primary_image = image_url
        for img in product.images:
            img.is_primary = False

    db_image = ProductImageModel(product_id=id, image_url=image_url, is_primary=is_primary)
    db.add(db_image)
    db.commit()
    db.refresh(product)
    return product

@router.delete("/admin/products/images/{image_id}", status_code=204, dependencies=[Depends(get_current_admin_user)])
def delete_image(image_id: int, db: Session = Depends(get_db)):
    image = db.query(ProductImageModel).filter(ProductImageModel.id == image_id).first()
    if not image:
        raise HTTPException(status_code=404, detail="Image not found")
    
    # Remove file from storage
    if os.path.exists(image.image_url[1:]): # remove leading '/'
        os.remove(image.image_url[1:])

    db.delete(image)
    db.commit()
    return