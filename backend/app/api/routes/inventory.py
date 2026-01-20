"""
Inventory management endpoints
"""
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.dependencies import get_db, get_current_admin_user
from app.models.customer import User
from app.models.product import Product
from app.models.inventory_log import InventoryLog
from app.schemas.inventory import InventoryAdjustment

router = APIRouter(prefix="/inventory", tags=["inventory"])


@router.post("/adjust")
def adjust_inventory(
    adjustment: InventoryAdjustment,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin_user)
):
    """
    Adjust product stock levels
    
    Body:
    - product_id: ID of product to adjust
    - quantity_change: Amount to change stock by (positive or negative)
    - reason: Reason for adjustment
    """
    product = db.query(Product).filter(Product.id == adjustment.product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    new_stock = product.stock + adjustment.quantity_change
    
    if new_stock < 0:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot reduce stock below 0. Current stock: {product.stock}"
        )
    
    old_stock = product.stock
    product.stock = new_stock
    
    # Create log entry
    log = InventoryLog(
        product_id=adjustment.product_id,
        change_quantity=adjustment.quantity_change,
        new_stock=new_stock,
        reason=adjustment.reason,
        admin_id=current_admin.id
    )
    db.add(log)
    
    db.commit()
    db.refresh(product)
    
    return {
        "product_id": product.id,
        "product_name": product.name,
        "old_stock": old_stock,
        "new_stock": new_stock,
        "change": adjustment.quantity_change,
        "reason": adjustment.reason
    }


@router.get("/logs")
def get_inventory_logs(
    product_id: Optional[int] = None,
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin_user)
):
    """
    Get inventory adjustment logs
    
    Optional filters:
    - product_id: Filter by specific product
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
                "product_sku": log.product.sku if log.product else None,
                "change_quantity": log.change_quantity,
                "new_stock": log.new_stock,
                "reason": log.reason,
                "admin_id": log.admin_id,
                "admin_username": log.admin.username if log.admin else None,
                "order_id": log.order_id,
                "created_at": log.created_at.isoformat()
            } for log in logs
        ]
    }


@router.get("/low-stock")
def get_low_stock_products(
    threshold: int = 10,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin_user)
):
    """
    Get products with stock below threshold
    
    Query parameters:
    - threshold: Stock level to consider "low" (default: 10)
    """
    products = db.query(Product).filter(
        Product.stock < threshold,
        Product.is_active == True
    ).order_by(Product.stock).offset(skip).limit(limit).all()
    
    return [
        {
            "id": p.id,
            "name": p.name,
            "sku": p.sku,
            "stock": p.stock,
            "primary_image": p.primary_image,
            "price": float(p.price)
        } for p in products
    ]
