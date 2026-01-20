"""
Admin-only endpoints for managing users, products, orders, and system operations
"""
from typing import List, Optional
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from sqlalchemy.orm import Session
from sqlalchemy import func, desc

from app.dependencies import get_db, get_current_admin_user
from app.models.customer import User
from app.models.product import Product, Category, ProductImage
from app.models.order import Order, OrderItem
from app.models.payment import Payment
from app.models.inventory_log import InventoryLog
from app.schemas.user import UserResponse, UserUpdate
from app.schemas.product import ProductCreate, ProductUpdate, Product
from app.core.security import get_password_hash
from app.services.inventory import InventoryService

import os
import shutil
from pathlib import Path

router = APIRouter(prefix="/admin", tags=["admin"])

# Configuration
UPLOAD_DIR = Path("uploads/products")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".webp"}
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB


# ============================================
# DASHBOARD & STATISTICS
# ============================================

@router.get("/dashboard/stats")
def get_dashboard_stats(
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin_user)
):
    """
    Get comprehensive dashboard statistics
    
    Returns overview metrics for admin dashboard:
    - Total revenue, orders, products, users
    - Recent activity
    - Top products
    - Order status breakdown
    """
    # Calculate date ranges
    today = datetime.utcnow().date()
    month_start = today.replace(day=1)
    last_month_start = (month_start - timedelta(days=1)).replace(day=1)
    
    # Total counts
    total_users = db.query(User).filter(User.role == "user").count()
    total_products = db.query(Product).count()
    total_orders = db.query(Order).count()
    
    # Revenue calculations
    total_revenue = db.query(func.sum(Order.total_amount)).filter(
        Order.payment_status == "completed"
    ).scalar() or 0
    
    monthly_revenue = db.query(func.sum(Order.total_amount)).filter(
        Order.payment_status == "completed",
        func.date(Order.created_at) >= month_start
    ).scalar() or 0
    
    last_month_revenue = db.query(func.sum(Order.total_amount)).filter(
        Order.payment_status == "completed",
        func.date(Order.created_at) >= last_month_start,
        func.date(Order.created_at) < month_start
    ).scalar() or 0
    
    # Calculate growth percentage
    revenue_growth = 0
    if last_month_revenue > 0:
        revenue_growth = ((monthly_revenue - last_month_revenue) / last_month_revenue) * 100
    
    # Orders this month
    monthly_orders = db.query(Order).filter(
        func.date(Order.created_at) >= month_start
    ).count()
    
    # Order status breakdown
    order_statuses = db.query(
        Order.status,
        func.count(Order.id).label('count')
    ).group_by(Order.status).all()
    
    status_breakdown = {status: count for status, count in order_statuses}
    
    # Top selling products (by quantity)
    top_products = db.query(
        Product.id,
        Product.name,
        Product.primary_image,
        Product.price,
        func.sum(OrderItem.quantity).label('total_sold')
    ).join(OrderItem, Product.id == OrderItem.product_id)\
     .join(Order, OrderItem.order_id == Order.id)\
     .filter(Order.status != "cancelled")\
     .group_by(Product.id, Product.name, Product.primary_image, Product.price)\
     .order_by(desc('total_sold'))\
     .limit(5)\
     .all()
    
    # Low stock products
    low_stock_products = db.query(Product).filter(
        Product.stock < 10,
        Product.is_active == True
    ).order_by(Product.stock).limit(10).all()
    
    # Recent orders
    recent_orders = db.query(Order)\
        .order_by(desc(Order.created_at))\
        .limit(10)\
        .all()
    
    return {
        "total_users": total_users,
        "total_products": total_products,
        "total_orders": total_orders,
        "total_revenue": float(total_revenue),
        "monthly_revenue": float(monthly_revenue),
        "last_month_revenue": float(last_month_revenue),
        "revenue_growth": round(revenue_growth, 2),
        "monthly_orders": monthly_orders,
        "status_breakdown": status_breakdown,
        "top_products": [
            {
                "id": p.id,
                "name": p.name,
                "primary_image": p.primary_image,
                "total_sold": p.total_sold
            } for p in top_products
        ],
        "low_stock_products": [
            {
                "id": p.id,
                "name": p.name,
                "stock": p.stock
            } for p in low_stock_products
        ],
        "recent_orders": [
            {
                "id": o.id,
                "customer_name": o.customer.full_name if o.customer else "Unknown",
                "total_amount": float(o.total_amount),
                "status": o.status,
                "created_at": o.created_at.isoformat()
            } for o in recent_orders
        ]
    }


# ============================================
# USER MANAGEMENT
# ============================================

@router.get("/users", response_model=List[UserResponse])
def get_all_users(
    skip: int = 0,
    limit: int = 100,
    search: Optional[str] = None,
    role: Optional[str] = None,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin_user)
):
    """
    Get all users with optional filtering
    
    Query parameters:
    - skip: Number of records to skip (pagination)
    - limit: Maximum number of records to return
    - search: Search by username or email
    - role: Filter by user role
    """
    query = db.query(User)
    
    if search:
        search_pattern = f"%{search}%"
        query = query.filter(
            (User.username.ilike(search_pattern)) |
            (User.email.ilike(search_pattern)) |
            (User.full_name.ilike(search_pattern))
        )
    
    if role:
        query = query.filter(User.role == role)
    
    users = query.offset(skip).limit(limit).all()
    return users


@router.get("/users/{user_id}", response_model=UserResponse)
def get_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin_user)
):
    """Get specific user by ID"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@router.put("/users/{user_id}", response_model=UserResponse)
def update_user(
    user_id: int,
    user_update: UserUpdate,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin_user)
):
    """
    Update user information
    
    Admin can update:
    - User role
    - Active status
    - Profile information
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Update fields
    update_data = user_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(user, field, value)
    
    db.commit()
    db.refresh(user)
    return user


@router.delete("/users/{user_id}")
def delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin_user)
):
    """
    Delete user account
    
    Note: This will cascade delete all related data:
    - Addresses
    - Cart items
    - Reviews
    - Orders remain but user_id set to NULL
    """
    if user_id == current_admin.id:
        raise HTTPException(
            status_code=400,
            detail="Cannot delete your own admin account"
        )
    
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    db.delete(user)
    db.commit()
    
    return {"message": f"User {user.username} deleted successfully"}


# ============================================
# PRODUCT MANAGEMENT
# ============================================

@router.post("/products", response_model=Product, status_code=status.HTTP_201_CREATED)
def create_product_admin(
    product: ProductCreate,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin_user)
):
    """
    Create new product
    
    Admin can create products with all fields including:
    - Basic info (name, description, price)
    - Stock and SKU
    - Categories
    - Featured status
    """
    # Check for duplicate SKU
    existing = db.query(Product).filter(Product.sku == product.sku).first()
    if existing:
        raise HTTPException(
            status_code=400,
            detail=f"Product with SKU '{product.sku}' already exists"
        )
    
    # Create product
    db_product = Product(**product.dict(exclude={'category_ids'}))
    
    # Add categories if provided
    if product.category_ids:
        categories = db.query(Category).filter(
            Category.id.in_(product.category_ids)
        ).all()
        db_product.categories = categories
    
    db.add(db_product)
    db.commit()
    db.refresh(db_product)
    
    return db_product


@router.put("/products/{product_id}", response_model=Product)
def update_product_admin(
    product_id: int,
    product_update: ProductUpdate,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin_user)
):
    """
    Update existing product
    
    Admin can update any product field
    """
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    # Update fields
    update_data = product_update.dict(exclude_unset=True, exclude={'category_ids'})
    for field, value in update_data.items():
        setattr(product, field, value)
    
    # Update categories if provided
    if product_update.category_ids is not None:
        categories = db.query(Category).filter(
            Category.id.in_(product_update.category_ids)
        ).all()
        product.categories = categories
    
    db.commit()
    db.refresh(product)
    
    return product


@router.delete("/products/{product_id}")
def delete_product_admin(
    product_id: int,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin_user)
):
    """
    Delete product
    
    Note: This will cascade delete:
    - Product images
    - Product variations
    - Product-category associations
    - Reviews
    
    Order items will remain for historical records
    """
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    product_name = product.name
    db.delete(product)
    db.commit()
    
    return {"message": f"Product '{product_name}' deleted successfully"}


@router.post("/products/{product_id}/images")
async def upload_product_images(
    product_id: int,
    file: Optional[UploadFile] = File(None),
    files: Optional[List[UploadFile]] = File(None),
    is_primary: Optional[str] = Form(None),
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin_user)
):
    """
    Upload images for a product
    
    - Accepts single file (field: 'file') or multiple files (field: 'files')
    - Validates file type and size
    - is_primary: 'true' to set as primary image
    - Stores in uploads/products directory
    """
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    # Collect all files to process
    files_to_process = []
    if file:
        files_to_process.append(file)
    if files:
        files_to_process.extend(files)
    
    if not files_to_process:
        raise HTTPException(status_code=400, detail="No files provided")
    
    uploaded_images = []
    set_as_primary = is_primary and is_primary.lower() == 'true'
    
    for index, upload_file in enumerate(files_to_process):
        # Validate file extension
        file_ext = os.path.splitext(upload_file.filename)[1].lower()
        if file_ext not in ALLOWED_EXTENSIONS:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid file type: {file_ext}. Allowed: {', '.join(ALLOWED_EXTENSIONS)}"
            )
        
        # Read file content to check size
        content = await upload_file.read()
        if len(content) > MAX_FILE_SIZE:
            raise HTTPException(
                status_code=400,
                detail=f"File {upload_file.filename} exceeds maximum size of 5MB"
            )
        
        # Generate unique filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"product_{product_id}_{timestamp}_{index}{file_ext}"
        file_path = UPLOAD_DIR / filename
        
        # Save file
        with open(file_path, "wb") as f:
            f.write(content)
        
        # Create database record
        image_url = f"/uploads/products/{filename}"
        # Make primary if: explicitly requested, or first image and no existing primary
        make_primary = (set_as_primary and index == 0) or (index == 0 and not product.primary_image)
        
        product_image = ProductImage(
            product_id=product_id,
            image_url=image_url,
            alt_text=product.name,
            is_primary=make_primary
        )
        db.add(product_image)
        
        # Set as primary image on product
        if make_primary:
            product.primary_image = image_url
        
        uploaded_images.append({
            "id": None,  # Will be set after commit
            "url": image_url,
            "is_primary": make_primary
        })
    
    db.commit()
    
    # Get the image IDs after commit
    for i, img_data in enumerate(uploaded_images):
        img = db.query(ProductImage).filter(
            ProductImage.product_id == product_id,
            ProductImage.image_url == img_data["url"]
        ).first()
        if img:
            uploaded_images[i]["id"] = img.id
    
    return {
        "message": f"Uploaded {len(files_to_process)} image(s) successfully",
        "images": uploaded_images
    }


@router.delete("/products/{product_id}/images/{image_id}")
def delete_product_image(
    product_id: int,
    image_id: int,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin_user)
):
    """Delete product image"""
    image = db.query(ProductImage).filter(
        ProductImage.id == image_id,
        ProductImage.product_id == product_id
    ).first()
    
    if not image:
        raise HTTPException(status_code=404, detail="Image not found")
    
    # Delete physical file
    file_path = UPLOAD_DIR / os.path.basename(image.image_url)
    if file_path.exists():
        file_path.unlink()
    
    # If primary image, clear product primary_image
    product = db.query(Product).filter(Product.id == product_id).first()
    if product.primary_image == image.image_url:
        product.primary_image = None
    
    db.delete(image)
    db.commit()
    
    return {"message": "Image deleted successfully"}


# ============================================
# ORDER MANAGEMENT
# ============================================

@router.get("/orders")
def get_all_orders(
    skip: int = 0,
    limit: int = 100,
    status: Optional[str] = None,
    payment_status: Optional[str] = None,
    search: Optional[str] = None,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin_user)
):
    """
    Get all orders with filtering
    
    Query parameters:
    - status: Filter by order status
    - payment_status: Filter by payment status
    - search: Search by order number
    """
    query = db.query(Order)
    
    if status:
        query = query.filter(Order.status == status)
    
    if payment_status:
        query = query.filter(Order.payment_status == payment_status)
    
    if search:
        query = query.filter(Order.order_number.ilike(f"%{search}%"))
    
    total = query.count()
    orders = query.order_by(desc(Order.created_at)).offset(skip).limit(limit).all()
    
    return {
        "total": total,
        "orders": [
            {
                "id": o.id,
                "order_number": o.order_number,
                "user_id": o.user_id,
                "total_amount": float(o.total_amount),
                "status": o.status,
                "payment_status": o.payment_status,
                "payment_method": o.payment_method,
                "created_at": o.created_at.isoformat(),
                "items_count": len(o.items) if o.items else 0
            } for o in orders
        ]
    }


@router.get("/orders/{order_id}")
def get_order_details(
    order_id: int,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin_user)
):
    """Get detailed order information"""
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    return {
        "id": order.id,
        "order_number": order.order_number,
        "user_id": order.user_id,
        "user": {
            "id": order.user.id,
            "username": order.user.username,
            "email": order.user.email
        } if order.user else None,
        "address_id": order.address_id,
        "address": {
            "address_line_1": order.address.address_line_1,
            "address_line_2": order.address.address_line_2,
            "city": order.address.city,
            "state": order.address.state,
            "postal_code": order.address.postal_code,
            "country": order.address.country
        } if order.address else None,
        "items": [
            {
                "id": item.id,
                "product_id": item.product_id,
                "product_name": item.product.name if item.product else "Deleted Product",
                "quantity": item.quantity,
                "price": float(item.price),
                "subtotal": float(item.price * item.quantity)
            } for item in order.items
        ],
        "total_amount": float(order.total_amount),
        "shipping_cost": float(order.shipping_cost),
        "tax_amount": float(order.tax_amount),
        "status": order.status,
        "payment_status": order.payment_status,
        "payment_method": order.payment_method,
        "notes": order.notes,
        "created_at": order.created_at.isoformat(),
        "updated_at": order.updated_at.isoformat()
    }


@router.put("/orders/{order_id}/status")
def update_order_status(
    order_id: int,
    status: str,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin_user)
):
    """
    Update order status
    
    Valid statuses: pending, processing, shipped, delivered, cancelled
    """
    valid_statuses = ["pending", "processing", "shipped", "delivered", "cancelled"]
    if status not in valid_statuses:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid status. Must be one of: {', '.join(valid_statuses)}"
        )
    
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    old_status = order.status
    order.status = status
    
    # If cancelling order, restore inventory
    if status == "cancelled" and old_status != "cancelled":
        for item in order.items:
            if item.product:
                item.product.stock += item.quantity
                
                # Log inventory change
                log = InventoryLog(
                    product_id=item.product_id,
                    order_id=order_id,
                    change_quantity=item.quantity,
                    new_stock=item.product.stock,
                    reason=f"Order {order.order_number} cancelled",
                    admin_id=current_admin.id
                )
                db.add(log)
    
    db.commit()
    db.refresh(order)
    
    return {
        "message": f"Order status updated from {old_status} to {status}",
        "order": {
            "id": order.id,
            "order_number": order.order_number,
            "status": order.status
        }
    }


@router.put("/orders/{order_id}/payment-status")
def update_payment_status(
    order_id: int,
    payment_status: str,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin_user)
):
    """
    Update payment status
    
    Valid statuses: pending, completed, failed, refunded
    """
    valid_statuses = ["pending", "completed", "failed", "refunded"]
    if payment_status not in valid_statuses:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid payment status. Must be one of: {', '.join(valid_statuses)}"
        )
    
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    
    order.payment_status = payment_status
    db.commit()
    
    return {
        "message": f"Payment status updated to {payment_status}",
        "order": {
            "id": order.id,
            "order_number": order.order_number,
            "payment_status": order.payment_status
        }
    }


# ============================================
# INVENTORY MANAGEMENT
# ============================================

@router.get("/inventory/logs")
def get_inventory_logs(
    skip: int = 0,
    limit: int = 100,
    product_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin_user)
):
    """
    Get inventory change logs
    
    Track all stock changes with reasons and admin who made the change
    """
    query = db.query(InventoryLog)
    
    if product_id:
        query = query.filter(InventoryLog.product_id == product_id)
    
    total = query.count()
    logs = query.order_by(desc(InventoryLog.created_at)).offset(skip).limit(limit).all()
    
    return {
        "total": total,
        "logs": [
            {
                "id": log.id,
                "product_id": log.product_id,
                "product_name": log.product.name if log.product else None,
                "change_quantity": log.change_quantity,
                "new_stock": log.new_stock,
                "reason": log.reason,
                "admin_id": log.admin_id,
                "admin_username": log.admin.username if log.admin else None,
                "order_id": log.order_id,
                "order_number": log.order.order_number if log.order else None,
                "created_at": log.created_at.isoformat()
            } for log in logs
        ]
    }


@router.post("/inventory/adjust")
def adjust_inventory(
    product_id: int,
    quantity_change: int,
    reason: str,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin_user)
):
    """
    Manually adjust product inventory
    
    - quantity_change: Positive to add stock, negative to remove
    - reason: Explanation for the adjustment
    - Logs all changes with admin who made them
    """
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    new_stock = product.stock + quantity_change
    if new_stock < 0:
        raise HTTPException(
            status_code=400,
            detail=f"Insufficient stock. Current: {product.stock}, Requested change: {quantity_change}"
        )
    
    old_stock = product.stock
    product.stock = new_stock
    
    # Log the change
    log = InventoryLog(
        product_id=product_id,
        change_quantity=quantity_change,
        new_stock=new_stock,
        reason=reason,
        admin_id=current_admin.id
    )
    db.add(log)
    
    db.commit()
    
    return {
        "message": "Inventory adjusted successfully",
        "product": {
            "id": product.id,
            "name": product.name,
            "sku": product.sku,
            "old_stock": old_stock,
            "new_stock": new_stock,
            "change": quantity_change
        }
    }


# ============================================
# CATEGORY MANAGEMENT
# ============================================

@router.get("/categories")
def get_all_categories_admin(
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin_user)
):
    """Get all categories with product counts"""
    categories = db.query(Category).all()
    
    return [
        {
            "id": cat.id,
            "name": cat.name,
            "description": cat.description,
            "image_url": cat.image_url,
            "product_count": len(cat.products) if cat.products else 0
        } for cat in categories
    ]


@router.post("/categories", status_code=status.HTTP_201_CREATED)
def create_category_admin(
    name: str = Form(...),
    description: Optional[str] = Form(None),
    image_url: Optional[str] = Form(None),
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin_user)
):
    """Create new category"""
    # Check for duplicate
    existing = db.query(Category).filter(Category.name == name).first()
    if existing:
        raise HTTPException(
            status_code=400,
            detail=f"Category '{name}' already exists"
        )
    
    category = Category(
        name=name,
        description=description,
        image_url=image_url
    )
    
    db.add(category)
    db.commit()
    db.refresh(category)
    
    return {
        "id": category.id,
        "name": category.name,
        "description": category.description,
        "image_url": category.image_url
    }


@router.put("/categories/{category_id}")
def update_category_admin(
    category_id: int,
    name: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
    image_url: Optional[str] = Form(None),
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin_user)
):
    """Update category"""
    category = db.query(Category).filter(Category.id == category_id).first()
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")
    
    if name:
        category.name = name
    if description is not None:
        category.description = description
    if image_url is not None:
        category.image_url = image_url
    
    db.commit()
    db.refresh(category)
    
    return {
        "id": category.id,
        "name": category.name,
        "description": category.description,
        "image_url": category.image_url
    }


@router.delete("/categories/{category_id}")
def delete_category_admin(
    category_id: int,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin_user)
):
    """Delete category"""
    category = db.query(Category).filter(Category.id == category_id).first()
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")
    
    category_name = category.name
    db.delete(category)
    db.commit()
    
    return {"message": f"Category '{category_name}' deleted successfully"}
