"""
Categories Router
Complete category management endpoints.
Note: Database only has: id, name, description, image_url
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.customer import User
from app.models.product import Category as CategoryModel, Product as ProductModel
from app.core.security import get_current_admin_user
from app.schemas.product import Category, CategoryCreate, CategoryUpdate, CategorySimple


router = APIRouter()


# =============================================================================
# PUBLIC ENDPOINTS
# =============================================================================

@router.get("/categories", response_model=List[Category])
def get_categories(
    db: Session = Depends(get_db)
):
    """Get all categories"""
    query = db.query(CategoryModel)
    return query.order_by(CategoryModel.name).all()


@router.get("/categories/{category_id}", response_model=Category)
def get_category(category_id: int, db: Session = Depends(get_db)):
    """Get a single category by ID"""
    category = db.query(CategoryModel).filter(CategoryModel.id == category_id).first()
    if not category:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Category not found")
    return category


@router.get("/categories/{category_id}/products/count")
def get_category_product_count(category_id: int, db: Session = Depends(get_db)):
    """Get the count of products in a category"""
    category = db.query(CategoryModel).filter(CategoryModel.id == category_id).first()
    if not category:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Category not found")
    
    count = db.query(ProductModel).join(ProductModel.categories).filter(
        CategoryModel.id == category_id,
        ProductModel.is_active == True
    ).count()
    
    return {"category_id": category_id, "product_count": count}


# =============================================================================
# ADMIN ENDPOINTS
# =============================================================================

@router.get("/admin/categories", response_model=List[Category])
def admin_get_categories(
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin_user)
):
    """Get all categories (Admin only)"""
    return db.query(CategoryModel).order_by(CategoryModel.name).all()


@router.post("/admin/categories", response_model=Category, status_code=status.HTTP_201_CREATED)
def create_category(
    category_data: CategoryCreate,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin_user)
):
    """Create a new category (Admin only)"""
    # Check if category name already exists
    existing = db.query(CategoryModel).filter(CategoryModel.name == category_data.name).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Category with this name already exists"
        )
    
    # Create category (DB only has: name, description, image_url)
    category = CategoryModel(
        name=category_data.name,
        description=category_data.description,
        image_url=category_data.image_url
    )
    db.add(category)
    db.commit()
    db.refresh(category)
    return category


@router.put("/admin/categories/{category_id}", response_model=Category)
def update_category(
    category_id: int,
    category_data: CategoryUpdate,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin_user)
):
    """Update a category (Admin only)"""
    category = db.query(CategoryModel).filter(CategoryModel.id == category_id).first()
    if not category:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Category not found")
    
    update_data = category_data.model_dump(exclude_unset=True)
    
    # Check name uniqueness if name is being updated
    if 'name' in update_data:
        existing = db.query(CategoryModel).filter(
            CategoryModel.name == update_data['name'],
            CategoryModel.id != category_id
        ).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Category with this name already exists"
            )
    
    # Update allowed fields only (name, description, image_url)
    for field, value in update_data.items():
        if hasattr(category, field):
            setattr(category, field, value)
    
    db.commit()
    db.refresh(category)
    return category


@router.get("/admin/categories", response_model=list[Category])
def get_admin_categories(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin_user)
):
    """Get all categories for admin management"""
    categories = db.query(CategoryModel).offset(skip).limit(limit).all()
    return categories


@router.get("/admin/categories/{category_id}", response_model=Category)
def get_admin_category(
    category_id: int,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin_user)
):
    """Get a single category by ID (Admin only)"""
    category = db.query(CategoryModel).filter(CategoryModel.id == category_id).first()
    if not category:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Category not found")
    return category


@router.delete("/admin/categories/{category_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_category(
    category_id: int,
    force: bool = Query(False, description="Force delete even if category has products"),
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin_user)
):
    """Delete a category (Admin only)"""
    category = db.query(CategoryModel).filter(CategoryModel.id == category_id).first()
    if not category:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Category not found")
    
    # Check for products in this category
    product_count = db.query(ProductModel).join(ProductModel.categories).filter(
        CategoryModel.id == category_id
    ).count()
    
    if product_count > 0 and not force:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Category has {product_count} products. Use force=true to delete anyway."
        )
    
    # Note: categories table has no parent_id column - no child category check needed
    
    db.delete(category)
    db.commit()


@router.post("/admin/categories/{category_id}/image", response_model=Category)
async def upload_category_image(
    category_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin_user)
):
    """Upload an image for a category (Admin only)"""
    category = db.query(CategoryModel).filter(CategoryModel.id == category_id).first()
    if not category:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Category not found")
    
    image_url = await save_category_image(file, category_id)
    category.image_url = image_url
    db.commit()
    db.refresh(category)
    
    return category
