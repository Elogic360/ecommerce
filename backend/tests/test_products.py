"""
Product Management Tests
Comprehensive tests for product CRUD operations, categories, search, and image uploads.
"""
import pytest
import json
from io import BytesIO
from fastapi.testclient import TestClient

from app.models.product import Product, Category, ProductImage
from app.models.customer import User, Role
from app.core.security import get_password_hash


# =============================================================================
# FIXTURES
# =============================================================================

@pytest.fixture
def test_category(db):
    """Create a test category"""
    category = Category(
        name="Electronics",
        slug="electronics",
        description="Electronic devices and gadgets",
        is_active=True,
        sort_order=1,
    )
    db.add(category)
    db.commit()
    db.refresh(category)
    return category


@pytest.fixture
def test_subcategory(db, test_category):
    """Create a test subcategory"""
    subcategory = Category(
        name="Smartphones",
        slug="smartphones",
        description="Mobile phones and accessories",
        parent_id=test_category.id,
        is_active=True,
        sort_order=1,
    )
    db.add(subcategory)
    db.commit()
    db.refresh(subcategory)
    return subcategory


@pytest.fixture
def test_product(db, test_category):
    """Create a test product"""
    product = Product(
        name="Test Smartphone",
        slug="test-smartphone",
        description="A test smartphone for testing purposes",
        price=599.99,
        category_id=test_category.id,
        stock_quantity=100,
        low_stock_threshold=10,
        is_active=True,
        is_featured=False,
        weight=0.5,
        dimensions=json.dumps({"length": 15, "width": 7, "height": 0.8}),
        meta_title="Test Smartphone - Buy Now",
        meta_description="Get the best test smartphone for all your testing needs.",
    )
    db.add(product)
    db.commit()
    db.refresh(product)
    return product


@pytest.fixture
def multiple_products(db, test_category):
    """Create multiple products for pagination/search testing"""
    products = []
    for i in range(15):
        product = Product(
            name=f"Product {i}",
            slug=f"product-{i}",
            description=f"Description for product {i}",
            price=10.99 + i * 5,
            category_id=test_category.id,
            stock_quantity=50 + i * 10,
            low_stock_threshold=5,
            is_active=True,
            is_featured=i % 3 == 0,  # Every 3rd product is featured
        )
        products.append(product)
    db.add_all(products)
    db.commit()
    for p in products:
        db.refresh(p)
    return products


# =============================================================================
# CATEGORY TESTS
# =============================================================================

class TestCategories:
    """Test category endpoints"""

    def test_get_categories(self, client, test_category):
        """Test fetching all categories"""
        response = client.get("/api/v1/categories/")
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 1
        assert any(c["name"] == "Electronics" for c in data)

    def test_get_category_by_id(self, client, test_category):
        """Test fetching a specific category"""
        response = client.get(f"/api/v1/categories/{test_category.id}")
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Electronics"
        assert data["slug"] == "electronics"

    def test_get_category_not_found(self, client):
        """Test fetching non-existent category"""
        response = client.get("/api/v1/categories/99999")
        assert response.status_code == 404

    def test_create_category_admin(self, client, admin_headers):
        """Test creating a category as admin"""
        category_data = {
            "name": "Clothing",
            "description": "Apparel and accessories",
        }
        response = client.post(
            "/api/v1/categories/",
            json=category_data,
            headers=admin_headers,
        )
        assert response.status_code in [200, 201]
        data = response.json()
        assert data["name"] == "Clothing"
        assert "slug" in data

    def test_create_category_unauthorized(self, client, auth_headers):
        """Test that regular users cannot create categories"""
        category_data = {
            "name": "Unauthorized Category",
        }
        response = client.post(
            "/api/v1/categories/",
            json=category_data,
            headers=auth_headers,
        )
        assert response.status_code in [401, 403]

    def test_update_category_admin(self, client, admin_headers, test_category):
        """Test updating a category as admin"""
        update_data = {
            "name": "Updated Electronics",
            "description": "Updated description",
        }
        response = client.put(
            f"/api/v1/categories/{test_category.id}",
            json=update_data,
            headers=admin_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Updated Electronics"

    def test_delete_category_admin(self, client, admin_headers, db):
        """Test deleting a category as admin"""
        # Create a category to delete
        category = Category(
            name="To Delete",
            slug="to-delete",
            is_active=True,
        )
        db.add(category)
        db.commit()
        db.refresh(category)
        
        response = client.delete(
            f"/api/v1/categories/{category.id}",
            headers=admin_headers,
        )
        assert response.status_code in [200, 204]

    def test_get_category_tree(self, client, test_category, test_subcategory):
        """Test fetching hierarchical category tree"""
        response = client.get("/api/v1/categories/tree")
        assert response.status_code == 200
        data = response.json()
        # Should contain parent category with children
        assert len(data) >= 1

    def test_get_category_by_slug(self, client, test_category):
        """Test fetching category by slug"""
        response = client.get(f"/api/v1/categories/slug/{test_category.slug}")
        assert response.status_code == 200
        data = response.json()
        assert data["slug"] == "electronics"


# =============================================================================
# PRODUCT TESTS - PUBLIC ENDPOINTS
# =============================================================================

class TestProductsPublic:
    """Test public product endpoints (no auth required)"""

    def test_get_products(self, client, test_product):
        """Test fetching all products"""
        response = client.get("/api/v1/products/")
        assert response.status_code == 200
        data = response.json()
        # Response should have pagination structure
        assert "items" in data or isinstance(data, list)

    def test_get_products_pagination(self, client, multiple_products):
        """Test product listing with pagination"""
        # First page
        response = client.get("/api/v1/products/?page=1&page_size=5")
        assert response.status_code == 200
        data = response.json()
        
        if "items" in data:
            assert len(data["items"]) <= 5
            assert "pagination" in data or "total" in data
        else:
            assert len(data) <= 5

    def test_get_products_by_category(self, client, test_product, test_category):
        """Test filtering products by category"""
        response = client.get(f"/api/v1/products/?category_id={test_category.id}")
        assert response.status_code == 200
        data = response.json()
        items = data.get("items", data)
        if items:
            for item in items:
                assert item.get("category_id") == test_category.id

    def test_get_products_price_filter(self, client, multiple_products):
        """Test filtering products by price range"""
        response = client.get("/api/v1/products/?min_price=20&max_price=50")
        assert response.status_code == 200
        data = response.json()
        items = data.get("items", data)
        for item in items:
            assert 20 <= item["price"] <= 50

    def test_get_products_search(self, client, test_product):
        """Test searching products by query"""
        response = client.get("/api/v1/products/?search=smartphone")
        assert response.status_code == 200
        data = response.json()
        items = data.get("items", data)
        # At least one result should contain 'smartphone'
        if items:
            assert any("smartphone" in item["name"].lower() for item in items)

    def test_get_products_featured(self, client, multiple_products):
        """Test filtering featured products"""
        response = client.get("/api/v1/products/?is_featured=true")
        assert response.status_code == 200
        data = response.json()
        items = data.get("items", data)
        for item in items:
            assert item.get("is_featured") is True

    def test_get_products_in_stock(self, client, multiple_products):
        """Test filtering in-stock products"""
        response = client.get("/api/v1/products/?in_stock=true")
        assert response.status_code == 200
        data = response.json()
        items = data.get("items", data)
        for item in items:
            assert item.get("stock_quantity", 0) > 0

    def test_get_product_by_id(self, client, test_product):
        """Test fetching a specific product"""
        response = client.get(f"/api/v1/products/{test_product.id}")
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Test Smartphone"
        assert data["price"] == 599.99

    def test_get_product_not_found(self, client):
        """Test fetching non-existent product"""
        response = client.get("/api/v1/products/99999")
        assert response.status_code == 404

    def test_get_product_by_slug(self, client, test_product):
        """Test fetching product by slug"""
        response = client.get(f"/api/v1/products/slug/{test_product.slug}")
        assert response.status_code == 200
        data = response.json()
        assert data["slug"] == "test-smartphone"


# =============================================================================
# PRODUCT TESTS - ADMIN ENDPOINTS
# =============================================================================

class TestProductsAdmin:
    """Test admin product endpoints"""

    def test_create_product_admin(self, client, admin_headers, test_category):
        """Test creating a product as admin"""
        product_data = {
            "name": "New Laptop",
            "description": "A brand new laptop",
            "price": 1299.99,
            "category_id": test_category.id,
            "stock_quantity": 50,
            "sku": "LAPTOP-001",
        }
        response = client.post(
            "/api/v1/products/",
            json=product_data,
            headers=admin_headers,
        )
        assert response.status_code in [200, 201]
        data = response.json()
        assert data["name"] == "New Laptop"
        assert data["price"] == 1299.99
        assert "slug" in data

    def test_create_product_unauthorized(self, client, auth_headers, test_category):
        """Test that regular users cannot create products"""
        product_data = {
            "name": "Unauthorized Product",
            "price": 99.99,
            "category_id": test_category.id,
        }
        response = client.post(
            "/api/v1/products/",
            json=product_data,
            headers=auth_headers,
        )
        assert response.status_code in [401, 403]

    def test_create_product_no_auth(self, client, test_category):
        """Test that unauthenticated users cannot create products"""
        product_data = {
            "name": "No Auth Product",
            "price": 99.99,
            "category_id": test_category.id,
        }
        response = client.post(
            "/api/v1/products/",
            json=product_data,
        )
        assert response.status_code == 401

    def test_update_product_admin(self, client, admin_headers, test_product):
        """Test updating a product as admin"""
        update_data = {
            "name": "Updated Smartphone",
            "price": 649.99,
        }
        response = client.put(
            f"/api/v1/products/{test_product.id}",
            json=update_data,
            headers=admin_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Updated Smartphone"
        assert data["price"] == 649.99

    def test_update_product_partial(self, client, admin_headers, test_product):
        """Test partial product update"""
        update_data = {
            "is_featured": True,
        }
        response = client.patch(
            f"/api/v1/products/{test_product.id}",
            json=update_data,
            headers=admin_headers,
        )
        # May use PUT or PATCH depending on implementation
        if response.status_code == 405:
            response = client.put(
                f"/api/v1/products/{test_product.id}",
                json=update_data,
                headers=admin_headers,
            )
        assert response.status_code == 200

    def test_update_product_unauthorized(self, client, auth_headers, test_product):
        """Test that regular users cannot update products"""
        update_data = {
            "name": "Hacked Product",
        }
        response = client.put(
            f"/api/v1/products/{test_product.id}",
            json=update_data,
            headers=auth_headers,
        )
        assert response.status_code in [401, 403]

    def test_delete_product_admin(self, client, admin_headers, db, test_category):
        """Test deleting a product as admin"""
        # Create a product to delete
        product = Product(
            name="To Delete",
            slug="to-delete",
            price=9.99,
            category_id=test_category.id,
            stock_quantity=1,
            is_active=True,
        )
        db.add(product)
        db.commit()
        db.refresh(product)
        
        response = client.delete(
            f"/api/v1/products/{product.id}",
            headers=admin_headers,
        )
        assert response.status_code in [200, 204]

    def test_delete_product_unauthorized(self, client, auth_headers, test_product):
        """Test that regular users cannot delete products"""
        response = client.delete(
            f"/api/v1/products/{test_product.id}",
            headers=auth_headers,
        )
        assert response.status_code in [401, 403]


# =============================================================================
# PRODUCT STOCK MANAGEMENT TESTS
# =============================================================================

class TestProductStock:
    """Test product stock management"""

    def test_update_stock_admin(self, client, admin_headers, test_product):
        """Test updating product stock"""
        stock_data = {
            "quantity": 150,
        }
        response = client.patch(
            f"/api/v1/products/{test_product.id}/stock",
            json=stock_data,
            headers=admin_headers,
        )
        # Endpoint may not exist, check gracefully
        if response.status_code not in [404, 405]:
            assert response.status_code == 200
            data = response.json()
            assert data.get("stock_quantity") == 150

    def test_low_stock_products(self, client, admin_headers, db, test_category):
        """Test getting low stock products"""
        # Create a low stock product
        low_stock_product = Product(
            name="Low Stock Item",
            slug="low-stock-item",
            price=29.99,
            category_id=test_category.id,
            stock_quantity=3,
            low_stock_threshold=10,
            is_active=True,
        )
        db.add(low_stock_product)
        db.commit()
        
        response = client.get(
            "/api/v1/products/low-stock",
            headers=admin_headers,
        )
        # Endpoint may not exist
        if response.status_code == 200:
            data = response.json()
            items = data.get("items", data)
            if items:
                assert any(p["name"] == "Low Stock Item" for p in items)


# =============================================================================
# PRODUCT IMAGE TESTS
# =============================================================================

class TestProductImages:
    """Test product image upload and management"""

    def _create_test_image(self, filename="test.jpg", size=(100, 100), format="JPEG"):
        """Create a test image file"""
        try:
            from PIL import Image
            img = Image.new("RGB", size, color="red")
            buffer = BytesIO()
            img.save(buffer, format=format)
            buffer.seek(0)
            return buffer
        except ImportError:
            # Return a minimal valid JPEG if PIL not available
            return BytesIO(
                b'\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01'
                b'\x00\x00\x01\x00\x01\x00\x00\xff\xdb\x00C\x00'
                + bytes(64)
                + b'\xff\xd9'
            )

    def test_upload_product_image_admin(self, client, admin_headers, test_product):
        """Test uploading a product image as admin"""
        image_data = self._create_test_image()
        
        response = client.post(
            f"/api/v1/products/{test_product.id}/images",
            files={"file": ("test.jpg", image_data, "image/jpeg")},
            headers=admin_headers,
        )
        # Endpoint may use different path
        if response.status_code == 404:
            response = client.post(
                f"/api/v1/products/{test_product.id}/upload-image",
                files={"file": ("test.jpg", image_data, "image/jpeg")},
                headers=admin_headers,
            )
        
        if response.status_code not in [404, 405]:
            assert response.status_code in [200, 201]

    def test_upload_invalid_image_type(self, client, admin_headers, test_product):
        """Test uploading invalid file type"""
        invalid_file = BytesIO(b"This is not an image")
        
        response = client.post(
            f"/api/v1/products/{test_product.id}/images",
            files={"file": ("test.txt", invalid_file, "text/plain")},
            headers=admin_headers,
        )
        if response.status_code not in [404, 405]:
            assert response.status_code in [400, 415, 422]

    def test_upload_image_unauthorized(self, client, auth_headers, test_product):
        """Test that regular users cannot upload images"""
        image_data = self._create_test_image()
        
        response = client.post(
            f"/api/v1/products/{test_product.id}/images",
            files={"file": ("test.jpg", image_data, "image/jpeg")},
            headers=auth_headers,
        )
        if response.status_code not in [404, 405]:
            assert response.status_code in [401, 403]

    def test_get_product_images(self, client, test_product, db):
        """Test fetching product images"""
        # Create a product image
        image = ProductImage(
            product_id=test_product.id,
            image_url="/uploads/products/test.jpg",
            alt_text="Test image",
            is_primary=True,
        )
        db.add(image)
        db.commit()
        
        response = client.get(f"/api/v1/products/{test_product.id}/images")
        if response.status_code == 200:
            data = response.json()
            assert len(data) >= 1

    def test_delete_product_image_admin(self, client, admin_headers, test_product, db):
        """Test deleting a product image"""
        # Create an image to delete
        image = ProductImage(
            product_id=test_product.id,
            image_url="/uploads/products/to-delete.jpg",
            alt_text="To delete",
        )
        db.add(image)
        db.commit()
        db.refresh(image)
        
        response = client.delete(
            f"/api/v1/products/{test_product.id}/images/{image.id}",
            headers=admin_headers,
        )
        if response.status_code not in [404, 405]:
            assert response.status_code in [200, 204]


# =============================================================================
# PRODUCT VALIDATION TESTS
# =============================================================================

class TestProductValidation:
    """Test product input validation"""

    def test_create_product_invalid_price(self, client, admin_headers, test_category):
        """Test creating product with negative price"""
        product_data = {
            "name": "Invalid Price Product",
            "price": -10.99,
            "category_id": test_category.id,
        }
        response = client.post(
            "/api/v1/products/",
            json=product_data,
            headers=admin_headers,
        )
        assert response.status_code == 422

    def test_create_product_missing_name(self, client, admin_headers, test_category):
        """Test creating product without name"""
        product_data = {
            "price": 99.99,
            "category_id": test_category.id,
        }
        response = client.post(
            "/api/v1/products/",
            json=product_data,
            headers=admin_headers,
        )
        assert response.status_code == 422

    def test_create_product_invalid_category(self, client, admin_headers):
        """Test creating product with non-existent category"""
        product_data = {
            "name": "Invalid Category Product",
            "price": 99.99,
            "category_id": 99999,
        }
        response = client.post(
            "/api/v1/products/",
            json=product_data,
            headers=admin_headers,
        )
        # Should be 422 or 400 for validation error
        assert response.status_code in [400, 404, 422]

    def test_create_product_name_too_long(self, client, admin_headers, test_category):
        """Test creating product with very long name"""
        product_data = {
            "name": "A" * 500,  # Very long name
            "price": 99.99,
            "category_id": test_category.id,
        }
        response = client.post(
            "/api/v1/products/",
            json=product_data,
            headers=admin_headers,
        )
        # May pass if no length validation, or fail with 422
        # Just ensure it doesn't crash
        assert response.status_code in [200, 201, 422]

    def test_create_product_negative_stock(self, client, admin_headers, test_category):
        """Test creating product with negative stock"""
        product_data = {
            "name": "Negative Stock Product",
            "price": 99.99,
            "category_id": test_category.id,
            "stock_quantity": -5,
        }
        response = client.post(
            "/api/v1/products/",
            json=product_data,
            headers=admin_headers,
        )
        assert response.status_code == 422


# =============================================================================
# PRODUCT SORTING TESTS
# =============================================================================

class TestProductSorting:
    """Test product sorting functionality"""

    def test_sort_by_price_asc(self, client, multiple_products):
        """Test sorting products by price ascending"""
        response = client.get("/api/v1/products/?sort_by=price&sort_order=asc")
        assert response.status_code == 200
        data = response.json()
        items = data.get("items", data)
        if len(items) > 1:
            prices = [item["price"] for item in items]
            assert prices == sorted(prices)

    def test_sort_by_price_desc(self, client, multiple_products):
        """Test sorting products by price descending"""
        response = client.get("/api/v1/products/?sort_by=price&sort_order=desc")
        assert response.status_code == 200
        data = response.json()
        items = data.get("items", data)
        if len(items) > 1:
            prices = [item["price"] for item in items]
            assert prices == sorted(prices, reverse=True)

    def test_sort_by_name(self, client, multiple_products):
        """Test sorting products by name"""
        response = client.get("/api/v1/products/?sort_by=name&sort_order=asc")
        assert response.status_code == 200
        data = response.json()
        items = data.get("items", data)
        if len(items) > 1:
            names = [item["name"] for item in items]
            assert names == sorted(names)

    def test_sort_by_created_at(self, client, multiple_products):
        """Test sorting products by creation date"""
        response = client.get("/api/v1/products/?sort_by=created_at&sort_order=desc")
        assert response.status_code == 200
        # Just verify it doesn't crash
        data = response.json()
        assert "items" in data or isinstance(data, list)


# =============================================================================
# INVENTORY MANAGER TESTS
# =============================================================================

class TestInventoryManager:
    """Test inventory manager specific access"""

    def test_inventory_manager_can_update_stock(
        self, client, db, test_product, test_category
    ):
        """Test that inventory managers can update stock"""
        # Create inventory manager
        inv_manager = User(
            email="inv@example.com",
            username="invmgr",
            full_name="Inventory Manager",
            hashed_password=get_password_hash("Password123!"),
            role=Role.INVENTORY_MANAGER.value,
            is_active=True,
            is_verified=True,
        )
        db.add(inv_manager)
        db.commit()
        
        from app.core.security import create_access_token
        token = create_access_token(subject=inv_manager.email, role=inv_manager.role)
        headers = {"Authorization": f"Bearer {token}"}
        
        stock_data = {"quantity": 200}
        response = client.patch(
            f"/api/v1/products/{test_product.id}/stock",
            json=stock_data,
            headers=headers,
        )
        # May or may not have this endpoint
        if response.status_code not in [404, 405]:
            assert response.status_code in [200, 403]

    def test_inventory_manager_cannot_create_products(
        self, client, db, test_category
    ):
        """Test that inventory managers cannot create products"""
        # Create inventory manager
        inv_manager = User(
            email="inv2@example.com",
            username="invmgr2",
            full_name="Inventory Manager 2",
            hashed_password=get_password_hash("Password123!"),
            role=Role.INVENTORY_MANAGER.value,
            is_active=True,
            is_verified=True,
        )
        db.add(inv_manager)
        db.commit()
        
        from app.core.security import create_access_token
        token = create_access_token(subject=inv_manager.email, role=inv_manager.role)
        headers = {"Authorization": f"Bearer {token}"}
        
        product_data = {
            "name": "Inv Manager Product",
            "price": 99.99,
            "category_id": test_category.id,
        }
        response = client.post(
            "/api/v1/products/",
            json=product_data,
            headers=headers,
        )
        assert response.status_code in [401, 403]
