"""
Product Router
Complete product management endpoints with CRUD operations, image upload, and search.
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File, Form, status
from sqlalchemy.orm import Session, joinedload

from app.db.session import get_db
from app.models.customer import User
from app.models.product import Product as ProductModel, Category as CategoryModel, ProductImage as ProductImageModel, Review as ReviewModel
from app.core.security import get_current_user, get_current_admin_user
from app.schemas.product import (
    Product, ProductCreate, ProductUpdate, ProductSimple, ProductDetail,
    ProductListResponse, ProductFilter, PaginationMeta, ProductCreateSimple,
    Review, ReviewCreate,
    ProductImage, ProductImageCreate,
    StockUpdateRequest
)
from app.services import product_service
from app.services.upload import save_product_image, delete_product_images, MAX_IMAGES_PER_PRODUCT


router = APIRouter()


# =============================================================================
# PUBLIC PRODUCT ENDPOINTS
# =============================================================================

@router.get("/products", response_model=ProductListResponse)
def list_products(
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(20, ge=1, le=100, description="Items per page"),
    search: Optional[str] = Query(None, max_length=100, description="Search in name, description, brand"),
    category_id: Optional[int] = Query(None, description="Filter by category ID"),
    brand: Optional[str] = Query(None, max_length=100, description="Filter by brand"),
    min_price: Optional[float] = Query(None, ge=0, description="Minimum price"),
    max_price: Optional[float] = Query(None, ge=0, description="Maximum price"),
    is_featured: Optional[bool] = Query(None, description="Filter featured products"),
    in_stock: Optional[bool] = Query(None, description="Filter by stock availability"),
    min_rating: Optional[float] = Query(None, ge=0, le=5, description="Minimum rating"),
    sort_by: str = Query("created_at", pattern="^(price|rating|created_at|name|view_count)$"),
    sort_order: str = Query("desc", pattern="^(asc|desc)$"),
    db: Session = Depends(get_db)
):
    """Get paginated list of products with filtering and sorting. Public endpoint."""
    filters = ProductFilter(
        search=search,
        category_id=category_id,
        brand=brand,
        min_price=min_price,
        max_price=max_price,
        is_featured=is_featured,
        in_stock=in_stock,
        min_rating=min_rating,
        sort_by=sort_by,
        sort_order=sort_order,
        is_active=True
    )
    return product_service.get_products_paginated(db, page, per_page, filters)


@router.get("/products/featured", response_model=List[ProductSimple])
def get_featured_products(
    limit: int = Query(10, ge=1, le=50),
    db: Session = Depends(get_db)
):
    """Get featured products for homepage"""
    return product_service.get_featured_products(db, limit)


@router.get("/products/new-arrivals", response_model=List[ProductSimple])
def get_new_arrivals(
    limit: int = Query(10, ge=1, le=50),
    db: Session = Depends(get_db)
):
    """Get newest products"""
    return product_service.get_new_arrivals(db, limit)


@router.get("/products/bestsellers", response_model=List[ProductSimple])
def get_bestsellers(
    limit: int = Query(10, ge=1, le=50),
    db: Session = Depends(get_db)
):
    """Get best-selling products"""
    return product_service.get_bestsellers(db, limit)


@router.get("/products/{product_id}", response_model=ProductDetail)
def get_product(product_id: int, db: Session = Depends(get_db)):
    """Get a single product by ID with full details"""
    product = product_service.get_product_by_id(db, product_id)
    if not product:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")
    product_service.increment_view_count(db, product_id)
    return product


@router.get("/products/slug/{slug}", response_model=ProductDetail)
def get_product_by_slug(slug: str, db: Session = Depends(get_db)):
    """Get a single product by slug"""
    product = product_service.get_product_by_slug(db, slug)
    if not product:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")
    product_service.increment_view_count(db, product.id)
    return product


@router.get("/products/{product_id}/related", response_model=List[ProductSimple])
def get_related_products(
    product_id: int,
    limit: int = Query(4, ge=1, le=20),
    db: Session = Depends(get_db)
):
    """Get related products based on categories"""
    return product_service.get_related_products(db, product_id, limit)


@router.get("/products/{product_id}/reviews", response_model=List[Review])
def get_product_reviews(
    product_id: int,
    page: int = Query(1, ge=1),
    per_page: int = Query(10, ge=1, le=50),
    db: Session = Depends(get_db)
):
    """Get reviews for a product"""
    product = product_service.get_product_by_id(db, product_id)
    if not product:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")
    offset = (page - 1) * per_page
    reviews = db.query(ReviewModel).options(
        joinedload(ReviewModel.user)
    ).filter(
        ReviewModel.product_id == product_id,
        ReviewModel.is_approved == True
    ).order_by(ReviewModel.created_at.desc()).offset(offset).limit(per_page).all()
    return reviews


@router.post("/products/{product_id}/reviews", response_model=Review, status_code=status.HTTP_201_CREATED)
def create_review(
    product_id: int,
    review_data: ReviewCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a review for a product (authenticated users only)"""
    product = product_service.get_product_by_id(db, product_id)
    if not product:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")
    existing = db.query(ReviewModel).filter(
        ReviewModel.product_id == product_id,
        ReviewModel.user_id == current_user.id
    ).first()
    if existing:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="You have already reviewed this product")
    review = ReviewModel(product_id=product_id, user_id=current_user.id, **review_data.model_dump())
    db.add(review)
    db.commit()
    product_service.update_product_rating(db, product_id)
    db.refresh(review)
    return review


# =============================================================================
# ADMIN PRODUCT ENDPOINTS
# =============================================================================

@router.post("/admin/products/simple", response_model=Product, status_code=status.HTTP_201_CREATED)
def create_product_simple(
    product_data: ProductCreateSimple,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin_user)
):
    """Create a new product with simplified form (Admin only)
    
    Fields: name, category_id (optional), price, new_price (optional for discounts)
    SKU is auto-generated.
    """
    try:
        return product_service.create_product_simple(db, product_data)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/admin/products", response_model=Product, status_code=status.HTTP_201_CREATED)
def create_product(
    product_data: ProductCreate,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin_user)
):
    """Create a new product (Admin only)"""
    try:
        return product_service.create_product(db, product_data)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.put("/admin/products/{product_id}", response_model=Product)
def update_product(
    product_id: int,
    product_data: ProductUpdate,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin_user)
):
    """Update a product (Admin only)"""
    product = product_service.update_product(db, product_id, product_data)
    if not product:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")
    return product


@router.delete("/admin/products/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_product(
    product_id: int,
    hard_delete: bool = Query(False, description="Permanently delete"),
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin_user)
):
    """Delete a product (Admin only). Soft delete by default."""
    success = product_service.hard_delete_product(db, product_id) if hard_delete else product_service.delete_product(db, product_id)
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")


@router.get("/admin/products", response_model=ProductListResponse)
def admin_list_products(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    search: Optional[str] = None,
    category_id: Optional[int] = None,
    is_active: Optional[bool] = None,
    is_featured: Optional[bool] = None,
    in_stock: Optional[bool] = None,
    sort_by: str = Query("created_at", pattern="^(price|rating|created_at|name|stock|view_count)$"),
    sort_order: str = Query("desc", pattern="^(asc|desc)$"),
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin_user)
):
    """Get all products including inactive ones (Admin only)"""
    filters = ProductFilter(
        search=search, category_id=category_id, is_active=is_active,
        is_featured=is_featured, in_stock=in_stock, sort_by=sort_by, sort_order=sort_order
    )
    return product_service.get_products_paginated(db, page, per_page, filters)


# =============================================================================
# PRODUCT IMAGE ENDPOINTS
# =============================================================================

@router.post("/admin/products/{product_id}/images", response_model=ProductImage, status_code=status.HTTP_201_CREATED)
async def upload_product_image(
    product_id: int,
    file: UploadFile = File(...),
    is_primary: Optional[str] = Form(None),
    alt_text: Optional[str] = Form(None),
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin_user)
):
    """Upload an image for a product (Admin only)"""
    product = product_service.get_product_by_id(db, product_id, include_inactive=True)
    if not product:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")
    current_count = len(product.images)
    if current_count >= MAX_IMAGES_PER_PRODUCT:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Maximum {MAX_IMAGES_PER_PRODUCT} images allowed")
    result = await save_product_image(file, product_id)
    
    # Parse is_primary - handle both "true" string and boolean
    set_as_primary = is_primary and is_primary.lower() == 'true'
    if current_count == 0:
        set_as_primary = True
    
    image = product_service.add_product_image(
        db=db, product_id=product_id, image_url=result.image_url,
        alt_text=alt_text or file.filename, is_primary=set_as_primary
    )
    return image


@router.delete("/admin/products/images/{image_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_image(
    image_id: int,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin_user)
):
    """Delete a product image (Admin only)"""
    result = product_service.delete_product_image(db, image_id)
    if not result:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Image not found")
    # result is image_url string - delete the file
    delete_product_images(result, None)


@router.patch("/admin/products/{product_id}/images/{image_id}/primary", status_code=status.HTTP_200_OK)
def set_primary_image(
    product_id: int,
    image_id: int,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin_user)
):
    """Set an image as the primary image (Admin only)"""
    if not product_service.set_primary_image(db, product_id, image_id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Image not found")
    return {"message": "Primary image updated"}


# =============================================================================
# STOCK MANAGEMENT
# =============================================================================

@router.patch("/admin/products/{product_id}/stock", response_model=Product)
def update_stock(
    product_id: int,
    stock_update: StockUpdateRequest,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin_user)
):
    """Update product stock (Admin only)"""
    try:
        product = product_service.update_stock(db, product_id, stock_update.quantity, stock_update.reason)
        if not product:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")
        return product
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get("/admin/products/low-stock", response_model=List[ProductSimple])
def get_low_stock_products(
    threshold: Optional[int] = Query(None, ge=0),
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin_user)
):
    """Get products with low stock (Admin only)"""
    return product_service.get_low_stock_products(db, threshold)


@router.get("/admin/products/out-of-stock", response_model=List[ProductSimple])
def get_out_of_stock_products(
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin_user)
):
    """Get products that are out of stock (Admin only)"""
    return product_service.get_out_of_stock_products(db)
