from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from app.db.session import get_db
from app.schemas.inventory import InventoryAdjust, InventoryLogOut, InventoryItem
from app.models.inventory_log import InventoryLog
from app.models.product import Product
from app.core.security import get_current_admin_user
from app.models.customer import User
from datetime import datetime

router = APIRouter()

# ==================== INVENTORY MANAGEMENT ====================

@router.get("/inventory", response_model=List[InventoryItem])
def get_inventory(
    skip: int = 0,
    limit: int = 100,
    low_stock_only: bool = False,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin_user)
):
    """Get inventory list (Admin only)"""
    query = db.query(Product)
    
    if low_stock_only:
        query = query.filter(Product.stock < 10)  # Consider stock < 10 as low
    
    products = query.offset(skip).limit(limit).all()
    
    return [
        {
            "id": p.id,
            "name": p.name,
            "sku": p.sku,
            "stock": p.stock,
            "price": float(p.price),
            "is_active": p.is_active
        }
        for p in products
    ]

@router.post("/inventory/adjust")
def adjust_inventory(
    adjustment: InventoryAdjust,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin_user)
):
    """Adjust product inventory (Admin only)"""
    product = db.query(Product).filter(Product.id == adjustment.product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    old_stock = product.stock
    new_stock = old_stock + adjustment.change_quantity
    
    if new_stock < 0:
        raise HTTPException(
            status_code=400,
            detail="Adjustment would result in negative stock"
        )
    
    product.stock = new_stock
    
    # Create inventory log
    log = InventoryLog(
        product_id=adjustment.product_id,
        change_quantity=adjustment.change_quantity,
        new_stock=new_stock,
        reason=adjustment.reason,
        admin_id=current_admin.id
    )
    
    db.add(log)
    db.commit()
    db.refresh(product)
    
    return {
        "message": "Inventory adjusted successfully",
        "product_id": product.id,
        "old_stock": old_stock,
        "new_stock": new_stock
    }

@router.get("/inventory/logs", response_model=List[InventoryLogOut])
def get_inventory_logs(
    product_id: Optional[int] = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin_user)
):
    """Get inventory change logs (Admin only)"""
    query = db.query(InventoryLog)
    
    if product_id:
        query = query.filter(InventoryLog.product_id == product_id)
    
    logs = query.order_by(InventoryLog.created_at.desc()).offset(skip).limit(limit).all()
    return logs

@router.get("/inventory/{product_id}")
def get_product_inventory(
    product_id: int,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin_user)
):
    """Get inventory details for a specific product (Admin only)"""
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    # Get recent logs
    recent_logs = db.query(InventoryLog).filter(
        InventoryLog.product_id == product_id
    ).order_by(InventoryLog.created_at.desc()).limit(10).all()
    
    return {
        "product_id": product.id,
        "name": product.name,
        "sku": product.sku,
        "current_stock": product.stock,
        "price": float(product.price),
        "recent_changes": [
            {
                "change": log.change_quantity,
                "new_stock": log.new_stock,
                "reason": log.reason,
                "created_at": log.created_at.isoformat() if log.created_at else None
            }
            for log in recent_logs
        ]
    }
