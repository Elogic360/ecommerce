"""
Services module for e-commerce application.
Contains business logic for cart, orders, inventory, products, and file uploads.
"""

from .cart_service import CartService
from .orders import OrderService
from .inventory import InventoryService
from . import product_service
from .upload import (
    save_product_image,
    save_multiple_product_images,
    save_category_image,
    delete_image,
    delete_product_images,
    cleanup_orphaned_images,
    MAX_IMAGES_PER_PRODUCT,
)

__all__ = [
    "CartService",
    "OrderService",
    "InventoryService",
    "product_service",
    "save_product_image",
    "save_multiple_product_images",
    "save_category_image",
    "delete_image",
    "delete_product_images",
    "cleanup_orphaned_images",
    "MAX_IMAGES_PER_PRODUCT",
]
