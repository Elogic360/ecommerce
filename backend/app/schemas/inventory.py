"""
Pydantic schemas for inventory management
"""
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class InventoryAdjust(BaseModel):
    """Schema for manual inventory adjustments"""
    product_id: int = Field(..., description="ID of product to adjust")
    change_quantity: int = Field(..., description="Amount to change stock by (positive or negative)")
    reason: str = Field(..., min_length=1, max_length=200, description="Reason for adjustment")


class InventoryAdjustment(InventoryAdjust):
    """Alias for backward compatibility"""
    pass


class InventoryLogOut(BaseModel):
    """Schema for inventory log entries"""
    id: int
    product_id: int
    change_quantity: int
    new_stock: Optional[int]
    reason: Optional[str]
    admin_id: Optional[int]
    order_id: Optional[int]
    created_at: Optional[datetime]
    
    class Config:
        from_attributes = True


class InventoryLogResponse(BaseModel):
    """Extended schema with additional details"""
    id: int
    product_id: int
    change_quantity: int
    new_stock: Optional[int]
    reason: Optional[str]
    admin_id: Optional[int]
    order_id: Optional[int]
    created_at: Optional[datetime]
    product_name: Optional[str] = None
    admin_username: Optional[str] = None
    
    class Config:
        from_attributes = True


class InventoryItem(BaseModel):
    """Schema for inventory list items"""
    id: int
    name: str
    sku: str
    stock: int
    price: float
    is_active: bool
    
    class Config:
        from_attributes = True
