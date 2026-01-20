"""
Product Service
Business logic for product management including search, filtering, and pagination.
"""
from typing import Optional, List, Tuple
from decimal import Decimal
from datetime import datetime
import uuid
from sqlalchemy import or_, and_, func, desc, asc
from sqlalchemy.orm import Session, joinedload

from app.models.product import (
    Product, Category, ProductImage, ProductVariation, 
    Review, ProductCategoryAssociation, generate_slug
)
from app.schemas.product import (
    ProductCreate, ProductUpdate, ProductFilter, ProductCreateSimple,
    PaginationMeta, ProductListResponse, StockUpdateRequest
)


# =============================================================================
# PRODUCT QUERIES
# =============================================================================

def get_product_query(db: Session, include_inactive: bool = False):
    """Get base product query with eager loading"""
    query = db.query(Product).options(
        joinedload(Product.images),
        joinedload(Product.categories),
        joinedload(Product.variations)
    )
    
    if not include_inactive:
        query = query.filter(Product.is_active == True)
    
    return query


def get_product_by_id(
    db: Session, 
    product_id: int, 
    include_inactive: bool = False
) -> Optional[Product]:
    """Get a single product by ID"""
    query = get_product_query(db, include_inactive)
    return query.filter(Product.id == product_id).first()


def get_product_by_slug(
    db: Session, 
    slug: str, 
    include_inactive: bool = False
) -> Optional[Product]:
    """Get a single product by slug"""
    query = get_product_query(db, include_inactive)
    return query.filter(Product.slug == slug).first()


def get_product_by_sku(db: Session, sku: str) -> Optional[Product]:
    """Get a single product by SKU"""
    return db.query(Product).filter(Product.sku == sku.upper()).first()


# =============================================================================
# PRODUCT LISTING WITH FILTERS
# =============================================================================

def apply_product_filters(query, filters: ProductFilter):
    """Apply filters to product query"""
    
    # Text search
    if filters.search:
        search_term = f"%{filters.search}%"
        query = query.filter(
            or_(
                Product.name.ilike(search_term),
                Product.description.ilike(search_term),
                Product.brand.ilike(search_term),
                Product.sku.ilike(search_term)
            )
        )
    
    # Category filter
    if filters.category_id:
        query = query.join(Product.categories).filter(Category.id == filters.category_id)
    elif filters.category_ids:
        query = query.join(Product.categories).filter(Category.id.in_(filters.category_ids))
    
    # Brand filter
    if filters.brand:
        query = query.filter(Product.brand.ilike(f"%{filters.brand}%"))
    elif filters.brands:
        query = query.filter(Product.brand.in_(filters.brands))
    
    # Price range
    if filters.min_price is not None:
        query = query.filter(Product.price >= filters.min_price)
    if filters.max_price is not None:
        query = query.filter(Product.price <= filters.max_price)
    
    # Featured filter
    if filters.is_featured is not None:
        query = query.filter(Product.is_featured == filters.is_featured)
    
    # Active filter
    if filters.is_active is not None:
        query = query.filter(Product.is_active == filters.is_active)
    
    # Stock filter
    if filters.in_stock is True:
        query = query.filter(Product.stock > 0)
    elif filters.in_stock is False:
        query = query.filter(Product.stock <= 0)
    
    # Rating filter
    if filters.min_rating is not None:
        query = query.filter(Product.rating >= filters.min_rating)
    
    return query


def apply_sorting(query, sort_by: str, sort_order: str):
    """Apply sorting to product query"""
    sort_field = getattr(Product, sort_by, Product.created_at)
    
    if sort_order == "desc":
        query = query.order_by(desc(sort_field))
    else:
        query = query.order_by(asc(sort_field))
    
    return query


def get_products_paginated(
    db: Session,
    page: int = 1,
    per_page: int = 20,
    filters: Optional[ProductFilter] = None
) -> ProductListResponse:
    """
    Get paginated list of products with optional filters.
    
    Args:
        db: Database session
        page: Page number (1-indexed)
        per_page: Items per page
        filters: Optional filter parameters
        
    Returns:
        ProductListResponse with items and pagination meta
    """
    if filters is None:
        filters = ProductFilter()
    
    # Base query with eager loading
    query = db.query(Product).options(
        joinedload(Product.images),
        joinedload(Product.categories)
    )
    
    # Apply active filter by default ONLY if not explicitly set in filters
    # This prevents duplicate is_active filters in SQL
    if filters.is_active is None:
        query = query.filter(Product.is_active == True)
    
    # Apply filters (will handle is_active if it was explicitly set)
    query = apply_product_filters(query, filters)
    
    # Get total count before pagination
    total = query.count()
    
    # Apply sorting
    query = apply_sorting(query, filters.sort_by, filters.sort_order)
    
    # Apply pagination
    offset = (page - 1) * per_page
    products = query.offset(offset).limit(per_page).all()
    
    # Calculate pagination meta
    total_pages = (total + per_page - 1) // per_page
    
    meta = PaginationMeta(
        total=total,
        page=page,
        per_page=per_page,
        total_pages=total_pages,
        has_next=page < total_pages,
        has_prev=page > 1
    )
    
    return ProductListResponse(items=products, meta=meta)


# =============================================================================
# PRODUCT CRUD OPERATIONS
# =============================================================================

def create_product(db: Session, product_data: ProductCreate) -> Product:
    """Create a new product"""
    # Check SKU uniqueness
    existing = get_product_by_sku(db, product_data.sku)
    if existing:
        raise ValueError(f"Product with SKU '{product_data.sku}' already exists")
    
    # Extract category IDs and variations
    category_ids = product_data.category_ids
    variations_data = product_data.variations
    
    # Create product
    product_dict = product_data.model_dump(exclude={'category_ids', 'variations'})
    product = Product(**product_dict)
    
    # Generate slug
    product.slug = generate_slug(product.name)
    
    # Ensure unique slug
    base_slug = product.slug
    counter = 1
    while db.query(Product).filter(Product.slug == product.slug).first():
        product.slug = f"{base_slug}-{counter}"
        counter += 1
    
    # Add categories
    if category_ids:
        categories = db.query(Category).filter(Category.id.in_(category_ids)).all()
        product.categories = categories
    
    db.add(product)
    db.flush()  # Get the product ID
    
    # Add variations
    for var_data in variations_data:
        variation = ProductVariation(
            product_id=product.id,
            **var_data.model_dump()
        )
        db.add(variation)
    
    db.commit()
    db.refresh(product)
    
    return product


def create_product_simple(db: Session, product_data: ProductCreateSimple) -> Product:
    """Create a new product with simplified data - auto-generates SKU"""
    # Auto-generate unique SKU
    sku = f"SKU-{datetime.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:8].upper()}"
    
    # Create product with defaults
    product = Product(
        name=product_data.name,
        price=product_data.price,
        # If new_price is set, the current price becomes original_price, and new_price becomes price
        original_price=product_data.price if product_data.new_price else None,
        sale_price=product_data.new_price,
        sku=sku,
        stock=100,  # Default stock
        is_active=True,
        is_featured=False,
    )
    
    # Generate slug
    product.slug = generate_slug(product.name)
    
    # Ensure unique slug
    base_slug = product.slug
    counter = 1
    while db.query(Product).filter(Product.slug == product.slug).first():
        product.slug = f"{base_slug}-{counter}"
        counter += 1
    
    # Add category if provided
    if product_data.category_id:
        category = db.query(Category).filter(Category.id == product_data.category_id).first()
        if category:
            product.categories = [category]
    
    db.add(product)
    db.commit()
    db.refresh(product)
    
    return product


def update_product(
    db: Session, 
    product_id: int, 
    product_data: ProductUpdate
) -> Optional[Product]:
    """Update an existing product"""
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        return None
    
    # Get update data excluding None values
    update_data = product_data.model_dump(exclude_unset=True)
    
    # Handle category update separately
    category_ids = update_data.pop('category_ids', None)
    
    # Update product fields
    for field, value in update_data.items():
        setattr(product, field, value)
    
    # Update slug if name changed
    if 'name' in update_data:
        new_slug = generate_slug(product.name)
        if new_slug != product.slug:
            base_slug = new_slug
            counter = 1
            while db.query(Product).filter(
                Product.slug == new_slug,
                Product.id != product_id
            ).first():
                new_slug = f"{base_slug}-{counter}"
                counter += 1
            product.slug = new_slug
    
    # Update categories if provided
    if category_ids is not None:
        categories = db.query(Category).filter(Category.id.in_(category_ids)).all()
        product.categories = categories
    
    db.commit()
    db.refresh(product)
    
    return product


def delete_product(db: Session, product_id: int) -> bool:
    """Delete a product (soft delete by setting is_active=False)"""
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        return False
    
    product.is_active = False
    db.commit()
    return True


def hard_delete_product(db: Session, product_id: int) -> bool:
    """Permanently delete a product"""
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        return False
    
    db.delete(product)
    db.commit()
    return True


# =============================================================================
# STOCK MANAGEMENT
# =============================================================================

def update_stock(
    db: Session, 
    product_id: int, 
    quantity_change: int,
    reason: Optional[str] = None
) -> Optional[Product]:
    """
    Update product stock.
    
    Args:
        db: Database session
        product_id: Product ID
        quantity_change: Positive to add, negative to subtract
        reason: Optional reason for the change
        
    Returns:
        Updated product or None if not found
    """
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        return None
    
    new_stock = product.stock + quantity_change
    if new_stock < 0:
        raise ValueError("Stock cannot be negative")
    
    product.stock = new_stock
    db.commit()
    db.refresh(product)
    
    return product


def check_stock_availability(
    db: Session, 
    product_id: int, 
    quantity: int
) -> Tuple[bool, int]:
    """
    Check if requested quantity is available.
    
    Returns:
        Tuple of (is_available, current_stock)
    """
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        return False, 0
    
    return product.stock >= quantity, product.stock


def get_low_stock_products(
    db: Session, 
    threshold: Optional[int] = None
) -> List[Product]:
    """Get products that are below their low stock threshold"""
    query = db.query(Product).filter(Product.is_active == True)
    
    if threshold is not None:
        query = query.filter(Product.stock <= threshold)
    else:
        # Use default threshold of 10
        query = query.filter(Product.stock <= 10)
    
    return query.order_by(Product.stock.asc()).all()


def get_out_of_stock_products(db: Session) -> List[Product]:
    """Get products with zero stock"""
    return db.query(Product).filter(
        Product.is_active == True,
        Product.stock <= 0
    ).all()


# =============================================================================
# CATEGORY OPERATIONS
# =============================================================================

def get_all_categories(
    db: Session, 
    include_inactive: bool = False,
    parent_id: Optional[int] = None
) -> List[Category]:
    """Get all categories, optionally filtered by parent"""
    query = db.query(Category)
    
    if not include_inactive:
        query = query.filter(Category.is_active == True)
    
    if parent_id is not None:
        query = query.filter(Category.parent_id == parent_id)
    elif parent_id is None:
        # Get root categories only
        query = query.filter(Category.parent_id == None)
    
    return query.order_by(Category.sort_order, Category.name).all()


def get_category_tree(db: Session) -> List[Category]:
    """Get categories as a hierarchical tree"""
    # Get all active categories
    categories = db.query(Category).filter(
        Category.is_active == True
    ).order_by(Category.sort_order, Category.name).all()
    
    # Build tree structure
    category_map = {cat.id: cat for cat in categories}
    roots = []
    
    for cat in categories:
        if cat.parent_id is None:
            roots.append(cat)
        elif cat.parent_id in category_map:
            parent = category_map[cat.parent_id]
            if not hasattr(parent, '_children'):
                parent._children = []
            parent._children.append(cat)
    
    return roots


def create_category(db: Session, name: str, **kwargs) -> Category:
    """Create a new category"""
    # Generate slug
    slug = generate_slug(name)
    
    # Ensure unique slug
    base_slug = slug
    counter = 1
    while db.query(Category).filter(Category.slug == slug).first():
        slug = f"{base_slug}-{counter}"
        counter += 1
    
    category = Category(name=name, slug=slug, **kwargs)
    db.add(category)
    db.commit()
    db.refresh(category)
    
    return category


# =============================================================================
# PRODUCT IMAGES
# =============================================================================

def add_product_image(
    db: Session,
    product_id: int,
    image_url: str,
    alt_text: str = None,
    is_primary: bool = False
) -> ProductImage:
    """Add an image to a product"""
    # If this is primary, unset other primary images
    if is_primary:
        db.query(ProductImage).filter(
            ProductImage.product_id == product_id,
            ProductImage.is_primary == True
        ).update({"is_primary": False})
        
        # Also update product's primary_image field
        product = db.query(Product).filter(Product.id == product_id).first()
        if product:
            product.primary_image = image_url
    
    image = ProductImage(
        product_id=product_id,
        image_url=image_url,
        alt_text=alt_text,
        is_primary=is_primary
    )
    
    db.add(image)
    db.commit()
    db.refresh(image)
    
    return image


def delete_product_image(db: Session, image_id: int) -> Optional[str]:
    """Delete a product image and return its URL for file deletion"""
    image = db.query(ProductImage).filter(ProductImage.id == image_id).first()
    if not image:
        return None
    
    image_url = image.image_url
    product_id = image.product_id
    was_primary = image.is_primary
    
    db.delete(image)
    
    # If this was primary, set another image as primary
    if was_primary:
        next_image = db.query(ProductImage).filter(
            ProductImage.product_id == product_id
        ).first()
        
        if next_image:
            next_image.is_primary = True
            product = db.query(Product).filter(Product.id == product_id).first()
            if product:
                product.primary_image = next_image.image_url
        else:
            # No more images, clear product's primary image
            product = db.query(Product).filter(Product.id == product_id).first()
            if product:
                product.primary_image = None
    
    db.commit()
    
    return image_url


def set_primary_image(db: Session, product_id: int, image_id: int) -> bool:
    """Set a specific image as the primary image"""
    # Unset current primary
    db.query(ProductImage).filter(
        ProductImage.product_id == product_id,
        ProductImage.is_primary == True
    ).update({"is_primary": False})
    
    # Set new primary
    image = db.query(ProductImage).filter(
        ProductImage.id == image_id,
        ProductImage.product_id == product_id
    ).first()
    
    if not image:
        return False
    
    image.is_primary = True
    
    # Update product
    product = db.query(Product).filter(Product.id == product_id).first()
    if product:
        product.primary_image = image.image_url
    
    db.commit()
    return True


# =============================================================================
# REVIEWS
# =============================================================================

def update_product_rating(db: Session, product_id: int) -> None:
    """Recalculate and update product rating based on reviews"""
    result = db.query(
        func.avg(Review.rating).label('avg_rating'),
        func.count(Review.id).label('count')
    ).filter(
        Review.product_id == product_id,
        Review.is_approved == True
    ).first()
    
    product = db.query(Product).filter(Product.id == product_id).first()
    if product:
        product.rating = result.avg_rating or 0
        product.review_count = result.count or 0
        db.commit()


# =============================================================================
# ANALYTICS
# =============================================================================

def increment_view_count(db: Session, product_id: int) -> None:
    """Increment product view count"""
    db.query(Product).filter(Product.id == product_id).update(
        {"view_count": Product.view_count + 1}
    )
    db.commit()


def increment_sales_count(db: Session, product_id: int, quantity: int = 1) -> None:
    """Increment product sales (tracked via orders, this is a no-op for now)"""
    # Note: sales_count column doesn't exist in DB, track sales via orders table
    pass


def get_bestsellers(db: Session, limit: int = 10) -> List[Product]:
    """Get best-selling products (by is_bestseller flag or view_count)"""
    return db.query(Product).filter(
        Product.is_active == True
    ).order_by(desc(Product.view_count)).limit(limit).all()


def get_featured_products(db: Session, limit: int = 10) -> List[Product]:
    """Get featured products"""
    return db.query(Product).options(
        joinedload(Product.images),
        joinedload(Product.categories)
    ).filter(
        Product.is_active == True,
        Product.is_featured == True
    ).order_by(desc(Product.created_at)).limit(limit).all()


def get_new_arrivals(db: Session, limit: int = 10) -> List[Product]:
    """Get newest products"""
    return db.query(Product).options(
        joinedload(Product.images),
        joinedload(Product.categories)
    ).filter(
        Product.is_active == True
    ).order_by(desc(Product.created_at)).limit(limit).all()


def get_related_products(
    db: Session, 
    product_id: int, 
    limit: int = 4
) -> List[Product]:
    """Get related products based on categories"""
    # Get product's categories
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product or not product.categories:
        return []
    
    category_ids = [cat.id for cat in product.categories]
    
    # Get products in same categories
    return db.query(Product).join(Product.categories).filter(
        Category.id.in_(category_ids),
        Product.id != product_id,
        Product.is_active == True
    ).order_by(desc(Product.rating)).limit(limit).all()
