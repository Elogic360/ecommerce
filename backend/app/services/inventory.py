from sqlalchemy.orm import Session
from app.models.product import Product
from app.models.inventory_log import InventoryLog
from fastapi import HTTPException

class InventoryService:
    @staticmethod
    def update_stock(db: Session, product_id: int, change_quantity: int, reason: str, admin_id: int = None):
        product = db.query(Product).filter(Product.id == product_id).first()
        if not product:
            raise HTTPException(status_code=404, detail="Product not found")
        
        # Calculate new stock
        new_stock = product.stock + change_quantity
        if new_stock < 0:
            raise HTTPException(status_code=400, detail="Stock cannot go below zero")
        
        product.stock = new_stock
        db.add(product) # Re-add to ensure session tracks changes
        db.flush() # Flush to get updated product.stock for logging
        
        # Log the change
        log_entry = InventoryLog(
            product_id=product_id,
            change_quantity=change_quantity,
            new_stock=new_stock,
            reason=reason,
            admin_id=admin_id
        )
        db.add(log_entry)
        db.commit()
        db.refresh(product)
        return product

    @staticmethod
    def reserve_stock(db: Session, product_id: int, quantity: int, order_id: int = None):
        product = db.query(Product).filter(Product.id == product_id).first()
        if not product:
            raise HTTPException(status_code=404, detail="Product not found")
        
        if product.stock < quantity:
            raise HTTPException(
                status_code=400,
                detail=f"Insufficient stock for {product.name}. Available: {product.stock}"
            )
        
        product.stock -= quantity
        db.add(product)
        db.flush() # Flush to get updated product.stock for logging
        
        # Log the reservation
        log_entry = InventoryLog(
            product_id=product_id,
            change_quantity=-quantity, # Negative for reservation
            new_stock=product.stock,
            reason="order_reservation",
            order_id=order_id
        )
        db.add(log_entry)
        db.commit()
        db.refresh(product)
        return product

    @staticmethod
    def release_stock(db: Session, product_id: int, quantity: int, order_id: int = None):
        product = db.query(Product).filter(Product.id == product_id).first()
        if not product:
            raise HTTPException(status_code=404, detail="Product not found")
        
        product.stock += quantity
        db.add(product)
        db.flush() # Flush to get updated product.stock for logging
        
        # Log the release
        log_entry = InventoryLog(
            product_id=product_id,
            change_quantity=quantity, # Positive for release
            new_stock=product.stock,
            reason="order_cancellation" if order_id else "admin_release",
            order_id=order_id
        )
        db.add(log_entry)
        db.commit()
        db.refresh(product)
        return product
    
    @staticmethod
    def get_inventory_history(db: Session, product_id: int, limit: int = 50):
        history = db.query(InventoryLog).filter(InventoryLog.product_id == product_id).order_by(InventoryLog.created_at.desc()).limit(limit)
        return history
