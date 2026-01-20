"""
Cart and Order Tests
Comprehensive tests for shopping cart and order management functionality.
"""
import pytest
from decimal import Decimal
from datetime import datetime, timedelta
from fastapi.testclient import TestClient

from app.models.cart import Cart, CartItem, CartStatus
from app.models.order import Order, OrderItem, OrderStatus, PaymentStatus
from app.models.product import Product, Category
from app.models.customer import User, Role, Address
from app.core.security import get_password_hash, create_access_token
from app.services.cart_service import CartService, CartError
from app.services.orders import OrderService, OrderError


# =============================================================================
# FIXTURES
# =============================================================================

@pytest.fixture
def test_category(db):
    """Create a test category"""
    category = Category(
        name="Test Category",
        slug="test-category",
        is_active=True,
    )
    db.add(category)
    db.commit()
    db.refresh(category)
    return category


@pytest.fixture
def test_product(db, test_category):
    """Create a test product with stock"""
    product = Product(
        name="Test Product",
        slug="test-product",
        description="A test product",
        price=Decimal("99.99"),
        stock=50,
        sku="TEST-001",
        is_active=True,
    )
    db.add(product)
    db.commit()
    db.refresh(product)
    return product


@pytest.fixture
def test_product_low_stock(db, test_category):
    """Create a product with low stock"""
    product = Product(
        name="Low Stock Product",
        slug="low-stock-product",
        price=Decimal("49.99"),
        stock=3,
        sku="LOW-001",
        is_active=True,
    )
    db.add(product)
    db.commit()
    db.refresh(product)
    return product


@pytest.fixture
def test_product_out_of_stock(db, test_category):
    """Create an out-of-stock product"""
    product = Product(
        name="Out of Stock Product",
        slug="out-of-stock-product",
        price=Decimal("29.99"),
        stock=0,
        sku="OOS-001",
        is_active=True,
    )
    db.add(product)
    db.commit()
    db.refresh(product)
    return product


@pytest.fixture
def test_address(db, test_user):
    """Create a test address for user"""
    address = Address(
        user_id=test_user.id,
        label="Home",
        address_line_1="123 Test Street",
        city="Test City",
        state="Test State",
        postal_code="12345",
        country="Tanzania",
        is_default=True,
    )
    db.add(address)
    db.commit()
    db.refresh(address)
    return address


@pytest.fixture
def user_cart(db, test_user):
    """Create a cart for test user"""
    cart = CartService.get_or_create_cart(db, user_id=test_user.id)
    return cart


@pytest.fixture
def session_cart(db):
    """Create an anonymous session cart"""
    session_id = CartService.generate_session_id()
    cart = CartService.get_or_create_cart(db, session_id=session_id)
    return cart


# =============================================================================
# CART SERVICE TESTS
# =============================================================================

class TestCartService:
    """Test CartService class methods"""

    def test_create_user_cart(self, db, test_user):
        """Test creating a cart for authenticated user"""
        cart = CartService.get_or_create_cart(db, user_id=test_user.id)
        
        assert cart is not None
        assert cart.user_id == test_user.id
        assert cart.status == CartStatus.ACTIVE.value
        assert cart.expires_at is not None

    def test_create_session_cart(self, db):
        """Test creating a cart for anonymous session"""
        session_id = CartService.generate_session_id()
        cart = CartService.get_or_create_cart(db, session_id=session_id)
        
        assert cart is not None
        assert cart.session_id == session_id
        assert cart.user_id is None
        assert cart.status == CartStatus.ACTIVE.value

    def test_add_item_to_cart(self, db, user_cart, test_product):
        """Test adding an item to cart"""
        from app.schemas.cart import CartItemCreate
        
        item_data = CartItemCreate(product_id=test_product.id, quantity=2)
        cart_item = CartService.add_item(db, user_cart, item_data)
        
        assert cart_item is not None
        assert cart_item.product_id == test_product.id
        assert cart_item.quantity == 2
        assert cart_item.unit_price == test_product.price

    def test_add_item_updates_quantity_if_exists(self, db, user_cart, test_product):
        """Test that adding same item updates quantity"""
        from app.schemas.cart import CartItemCreate
        
        item_data = CartItemCreate(product_id=test_product.id, quantity=2)
        CartService.add_item(db, user_cart, item_data)
        
        # Add same product again
        CartService.add_item(db, user_cart, item_data)
        
        # Should have one item with quantity 4
        assert len(user_cart.items) == 1
        assert user_cart.items[0].quantity == 4

    def test_add_item_max_quantity_limit(self, db, user_cart, test_product):
        """Test maximum quantity per item limit"""
        from app.schemas.cart import CartItemCreate
        
        item_data = CartItemCreate(product_id=test_product.id, quantity=11)
        
        with pytest.raises(CartError) as exc_info:
            CartService.add_item(db, user_cart, item_data)
        
        assert "Maximum quantity" in exc_info.value.message

    def test_add_item_insufficient_stock(self, db, user_cart, test_product_low_stock):
        """Test adding item with insufficient stock"""
        from app.schemas.cart import CartItemCreate
        
        item_data = CartItemCreate(product_id=test_product_low_stock.id, quantity=5)
        
        with pytest.raises(CartError) as exc_info:
            CartService.add_item(db, user_cart, item_data)
        
        assert "Insufficient stock" in exc_info.value.message

    def test_add_item_product_not_found(self, db, user_cart):
        """Test adding non-existent product"""
        from app.schemas.cart import CartItemCreate
        
        item_data = CartItemCreate(product_id=99999, quantity=1)
        
        with pytest.raises(CartError) as exc_info:
            CartService.add_item(db, user_cart, item_data)
        
        assert "not found" in exc_info.value.message.lower()

    def test_update_item_quantity(self, db, user_cart, test_product):
        """Test updating cart item quantity"""
        from app.schemas.cart import CartItemCreate
        
        item_data = CartItemCreate(product_id=test_product.id, quantity=2)
        cart_item = CartService.add_item(db, user_cart, item_data)
        
        updated_item = CartService.update_item_quantity(db, user_cart, cart_item.id, 5)
        
        assert updated_item.quantity == 5

    def test_remove_item(self, db, user_cart, test_product):
        """Test removing item from cart"""
        from app.schemas.cart import CartItemCreate
        
        item_data = CartItemCreate(product_id=test_product.id, quantity=2)
        cart_item = CartService.add_item(db, user_cart, item_data)
        
        CartService.remove_item(db, user_cart, cart_item.id)
        
        assert len(user_cart.items) == 0

    def test_clear_cart(self, db, user_cart, test_product):
        """Test clearing entire cart"""
        from app.schemas.cart import CartItemCreate
        
        item_data = CartItemCreate(product_id=test_product.id, quantity=2)
        CartService.add_item(db, user_cart, item_data)
        
        CartService.clear_cart(db, user_cart)
        
        assert len(user_cart.items) == 0
        assert user_cart.total == 0

    def test_cart_totals_calculation(self, db, user_cart, test_product):
        """Test cart totals are calculated correctly"""
        from app.schemas.cart import CartItemCreate
        
        item_data = CartItemCreate(product_id=test_product.id, quantity=2)
        CartService.add_item(db, user_cart, item_data)
        
        expected_subtotal = test_product.price * 2
        expected_tax = expected_subtotal * Decimal("0.18")
        
        db.refresh(user_cart)
        
        assert user_cart.subtotal == expected_subtotal
        assert user_cart.tax_amount == expected_tax

    def test_validate_cart_for_checkout(self, db, user_cart, test_product):
        """Test cart validation for checkout"""
        from app.schemas.cart import CartItemCreate
        
        item_data = CartItemCreate(product_id=test_product.id, quantity=2)
        CartService.add_item(db, user_cart, item_data)
        
        is_valid, issues = CartService.validate_cart_for_checkout(db, user_cart)
        
        assert is_valid is True
        assert len(issues) == 0

    def test_validate_empty_cart(self, db, user_cart):
        """Test validation fails for empty cart"""
        is_valid, issues = CartService.validate_cart_for_checkout(db, user_cart)
        
        assert is_valid is False
        assert "Cart is empty" in issues

    def test_merge_session_cart(self, db, test_user, test_product):
        """Test merging session cart into user cart"""
        from app.schemas.cart import CartItemCreate
        
        # Create session cart with items
        session_id = CartService.generate_session_id()
        session_cart = CartService.get_or_create_cart(db, session_id=session_id)
        CartService.add_item(db, session_cart, CartItemCreate(product_id=test_product.id, quantity=2))
        
        # Merge into user cart
        merged_cart = CartService.merge_session_cart(db, test_user, session_id)
        
        assert merged_cart is not None
        assert merged_cart.user_id == test_user.id
        assert len(merged_cart.items) == 1
        assert merged_cart.items[0].quantity == 2
        
        # Session cart should be marked as converted
        db.refresh(session_cart)
        assert session_cart.status == CartStatus.CONVERTED.value


# =============================================================================
# CART ROUTER TESTS
# =============================================================================

class TestCartRouter:
    """Test cart API endpoints"""

    def test_get_cart(self, client, auth_headers, db, test_user):
        """Test getting user's cart"""
        response = client.get("/api/v1/cart", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data

    def test_add_to_cart(self, client, auth_headers, test_product):
        """Test adding item to cart via API"""
        response = client.post(
            "/api/v1/cart/items",
            json={"product_id": test_product.id, "quantity": 2},
            headers=auth_headers,
        )
        
        assert response.status_code in [200, 201]
        data = response.json()
        assert data["product_id"] == test_product.id
        assert data["quantity"] == 2

    def test_update_cart_item(self, client, auth_headers, db, test_user, test_product):
        """Test updating cart item quantity via API"""
        # First add item
        response = client.post(
            "/api/v1/cart/items",
            json={"product_id": test_product.id, "quantity": 2},
            headers=auth_headers,
        )
        item_id = response.json()["id"]
        
        # Update quantity
        response = client.put(
            f"/api/v1/cart/items/{item_id}",
            json={"quantity": 5},
            headers=auth_headers,
        )
        
        assert response.status_code == 200
        assert response.json()["quantity"] == 5

    def test_remove_from_cart(self, client, auth_headers, test_product):
        """Test removing item from cart via API"""
        # First add item
        response = client.post(
            "/api/v1/cart/items",
            json={"product_id": test_product.id, "quantity": 2},
            headers=auth_headers,
        )
        item_id = response.json()["id"]
        
        # Remove item
        response = client.delete(
            f"/api/v1/cart/items/{item_id}",
            headers=auth_headers,
        )
        
        assert response.status_code == 200

    def test_clear_cart(self, client, auth_headers, test_product):
        """Test clearing cart via API"""
        # Add item
        client.post(
            "/api/v1/cart/items",
            json={"product_id": test_product.id, "quantity": 2},
            headers=auth_headers,
        )
        
        # Clear cart
        response = client.delete("/api/v1/cart", headers=auth_headers)
        
        assert response.status_code == 200

    def test_get_cart_summary(self, client, auth_headers, test_product):
        """Test getting cart summary"""
        # Add item
        client.post(
            "/api/v1/cart/items",
            json={"product_id": test_product.id, "quantity": 2},
            headers=auth_headers,
        )
        
        response = client.get("/api/v1/cart/summary", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert "subtotal" in data
        assert "total" in data
        assert "item_count" in data

    def test_session_cart_endpoints(self, client, test_product):
        """Test session cart endpoints for anonymous users"""
        # Get new session ID
        response = client.get("/api/v1/cart/session/new")
        assert response.status_code == 200
        session_id = response.json()["session_id"]
        
        # Add item to session cart
        response = client.post(
            f"/api/v1/cart/session/{session_id}/items",
            json={"product_id": test_product.id, "quantity": 1},
        )
        assert response.status_code in [200, 201]
        
        # Get session cart
        response = client.get(f"/api/v1/cart/session/{session_id}")
        assert response.status_code == 200
        assert len(response.json()["items"]) == 1


# =============================================================================
# ORDER SERVICE TESTS
# =============================================================================

class TestOrderService:
    """Test OrderService class methods"""

    def test_create_order_from_cart(self, db, test_user, test_product, test_address):
        """Test creating order from user's cart"""
        from app.schemas.cart import CartItemCreate
        from app.schemas.order import OrderFromCart
        
        # Add items to cart
        cart = CartService.get_or_create_cart(db, user_id=test_user.id)
        CartService.add_item(db, cart, CartItemCreate(product_id=test_product.id, quantity=2))
        
        # Create order
        order_data = OrderFromCart(
            address_id=test_address.id,
            payment_method="cod",
            notes="Test order",
        )
        
        order = OrderService.create_order_from_cart(db, test_user, order_data)
        
        assert order is not None
        assert order.user_id == test_user.id
        assert order.status == OrderStatus.PENDING.value
        assert order.payment_status == PaymentStatus.PENDING.value
        assert len(order.items) == 1
        assert order.items[0].quantity == 2
        
        # Verify stock was deducted
        db.refresh(test_product)
        assert test_product.stock == 48  # 50 - 2

    def test_create_order_empty_cart_fails(self, db, test_user, test_address):
        """Test that order creation fails with empty cart"""
        from app.schemas.order import OrderFromCart
        
        order_data = OrderFromCart(
            address_id=test_address.id,
            payment_method="cod",
        )
        
        with pytest.raises(OrderError) as exc_info:
            OrderService.create_order_from_cart(db, test_user, order_data)
        
        assert "empty" in exc_info.value.message.lower()

    def test_cancel_order(self, db, test_user, test_product, test_address):
        """Test cancelling an order"""
        from app.schemas.cart import CartItemCreate
        from app.schemas.order import OrderFromCart
        
        original_stock = test_product.stock
        
        # Create order
        cart = CartService.get_or_create_cart(db, user_id=test_user.id)
        CartService.add_item(db, cart, CartItemCreate(product_id=test_product.id, quantity=2))
        
        order_data = OrderFromCart(address_id=test_address.id, payment_method="cod")
        order = OrderService.create_order_from_cart(db, test_user, order_data)
        
        # Cancel order
        cancelled_order = OrderService.cancel_order(db, order.id, test_user.id, "Changed my mind")
        
        assert cancelled_order.status == OrderStatus.CANCELLED.value
        
        # Stock should be restored
        db.refresh(test_product)
        assert test_product.stock == original_stock

    def test_update_order_status(self, db, admin_user, test_user, test_product, test_address):
        """Test updating order status (admin)"""
        from app.schemas.cart import CartItemCreate
        from app.schemas.order import OrderFromCart
        
        # Create order
        cart = CartService.get_or_create_cart(db, user_id=test_user.id)
        CartService.add_item(db, cart, CartItemCreate(product_id=test_product.id, quantity=1))
        
        order = OrderService.create_order_from_cart(
            db, test_user,
            OrderFromCart(address_id=test_address.id, payment_method="cod")
        )
        
        # Update status
        updated_order = OrderService.update_order_status(
            db, order.id, OrderStatus.CONFIRMED.value, admin_user.id
        )
        
        assert updated_order.status == OrderStatus.CONFIRMED.value

    def test_invalid_status_transition(self, db, admin_user, test_user, test_product, test_address):
        """Test that invalid status transitions are rejected"""
        from app.schemas.cart import CartItemCreate
        from app.schemas.order import OrderFromCart
        
        cart = CartService.get_or_create_cart(db, user_id=test_user.id)
        CartService.add_item(db, cart, CartItemCreate(product_id=test_product.id, quantity=1))
        
        order = OrderService.create_order_from_cart(
            db, test_user,
            OrderFromCart(address_id=test_address.id, payment_method="cod")
        )
        
        # Try to go directly from pending to delivered
        with pytest.raises(OrderError) as exc_info:
            OrderService.update_order_status(
                db, order.id, OrderStatus.DELIVERED.value, admin_user.id
            )
        
        assert "Cannot transition" in exc_info.value.message


# =============================================================================
# ORDER ROUTER TESTS
# =============================================================================

class TestOrderRouter:
    """Test order API endpoints"""

    def test_create_order(self, client, auth_headers, db, test_user, test_product, test_address):
        """Test creating order via API"""
        from app.schemas.cart import CartItemCreate
        
        # Add to cart first
        cart = CartService.get_or_create_cart(db, user_id=test_user.id)
        CartService.add_item(db, cart, CartItemCreate(product_id=test_product.id, quantity=1))
        
        response = client.post(
            "/api/v1/orders",
            json={
                "address_id": test_address.id,
                "payment_method": "cod",
                "notes": "Test order",
            },
            headers=auth_headers,
        )
        
        assert response.status_code in [200, 201]
        data = response.json()
        assert "order_number" in data
        assert data["status"] == "pending"
        # Client should clear cart after successful order
        assert data.get("clear_client_cart") is True

    def test_get_user_orders(self, client, auth_headers):
        """Test getting user's order history"""
        response = client.get("/api/v1/orders", headers=auth_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data

    def test_get_order_by_id(self, client, auth_headers, db, test_user, test_product, test_address):
        """Test getting specific order"""
        from app.schemas.cart import CartItemCreate
        from app.schemas.order import OrderFromCart
        
        # Create an order
        cart = CartService.get_or_create_cart(db, user_id=test_user.id)
        CartService.add_item(db, cart, CartItemCreate(product_id=test_product.id, quantity=1))
        order = OrderService.create_order_from_cart(
            db, test_user,
            OrderFromCart(address_id=test_address.id, payment_method="cod")
        )
        
        response = client.get(f"/api/v1/orders/{order.id}", headers=auth_headers)
        
        assert response.status_code == 200
        assert response.json()["id"] == order.id

    def test_cancel_order_api(self, client, auth_headers, db, test_user, test_product, test_address):
        """Test cancelling order via API"""
        from app.schemas.cart import CartItemCreate
        from app.schemas.order import OrderFromCart
        
        cart = CartService.get_or_create_cart(db, user_id=test_user.id)
        CartService.add_item(db, cart, CartItemCreate(product_id=test_product.id, quantity=1))
        order = OrderService.create_order_from_cart(
            db, test_user,
            OrderFromCart(address_id=test_address.id, payment_method="cod")
        )
        
        response = client.post(
            f"/api/v1/orders/{order.id}/cancel",
            json={"reason": "Test cancellation"},
            headers=auth_headers,
        )
        
        assert response.status_code == 200
        assert response.json()["status"] == "cancelled"

    def test_guest_order(self, client, test_product):
        """Test creating guest order"""
        response = client.post(
            "/api/v1/orders/guest",
            json={
                "guest_email": "guest@example.com",
                "guest_name": "Guest User",
                "guest_phone": "+255123456789",
                "address_line_1": "123 Guest Street",
                "city": "Dar es Salaam",
                "state": "Dar es Salaam",
                "postal_code": "11000",
                "country": "Tanzania",
                "items": [{"product_id": test_product.id, "quantity": 1}],
                "payment_method": "cod",
            },
        )
        
        assert response.status_code in [200, 201]
        data = response.json()
        assert "order_number" in data
        assert data["tracking_email"] == "guest@example.com"
        # Guest response should instruct client to clear local cart
        assert data.get("clear_client_cart") is True


# =============================================================================
# ADMIN ORDER TESTS
# =============================================================================

class TestAdminOrderEndpoints:
    """Test admin order management endpoints"""

    def test_admin_get_all_orders(self, client, admin_headers):
        """Test admin can get all orders"""
        response = client.get("/api/v1/orders/admin/all", headers=admin_headers)
        
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data

    def test_admin_update_order_status(
        self, client, admin_headers, db, test_user, test_product, test_address
    ):
        """Test admin can update order status"""
        from app.schemas.cart import CartItemCreate
        from app.schemas.order import OrderFromCart
        
        cart = CartService.get_or_create_cart(db, user_id=test_user.id)
        CartService.add_item(db, cart, CartItemCreate(product_id=test_product.id, quantity=1))
        order = OrderService.create_order_from_cart(
            db, test_user,
            OrderFromCart(address_id=test_address.id, payment_method="cod")
        )
        
        response = client.put(
            f"/api/v1/orders/admin/{order.id}/status",
            json={"status": "confirmed"},
            headers=admin_headers,
        )
        
        assert response.status_code == 200
        assert response.json()["status"] == "confirmed"

    def test_admin_add_tracking(
        self, client, admin_headers, db, test_user, test_product, test_address
    ):
        """Test admin can add tracking info"""
        from app.schemas.cart import CartItemCreate
        from app.schemas.order import OrderFromCart
        
        cart = CartService.get_or_create_cart(db, user_id=test_user.id)
        CartService.add_item(db, cart, CartItemCreate(product_id=test_product.id, quantity=1))
        order = OrderService.create_order_from_cart(
            db, test_user,
            OrderFromCart(address_id=test_address.id, payment_method="cod")
        )
        
        response = client.put(
            f"/api/v1/orders/admin/{order.id}/shipping",
            json={
                "tracking_number": "TRK123456",
                "shipping_carrier": "DHL",
            },
            headers=admin_headers,
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["tracking_number"] == "TRK123456"
        assert data["shipping_carrier"] == "DHL"

    def test_user_cannot_access_admin_endpoints(self, client, auth_headers):
        """Test regular user cannot access admin endpoints"""
        response = client.get("/api/v1/orders/admin/all", headers=auth_headers)
        
        assert response.status_code in [401, 403]

    def test_admin_cancel_order_no_time_limit(
        self, client, admin_headers, db, test_user, test_product, test_address
    ):
        """Test admin can cancel order without time restriction"""
        from app.schemas.cart import CartItemCreate
        from app.schemas.order import OrderFromCart
        
        cart = CartService.get_or_create_cart(db, user_id=test_user.id)
        CartService.add_item(db, cart, CartItemCreate(product_id=test_product.id, quantity=1))
        order = OrderService.create_order_from_cart(
            db, test_user,
            OrderFromCart(address_id=test_address.id, payment_method="cod")
        )
        
        # Simulate old order by modifying created_at
        order.created_at = datetime.utcnow() - timedelta(days=7)
        db.commit()
        
        response = client.post(
            f"/api/v1/orders/admin/{order.id}/cancel",
            json={"reason": "Admin cancellation"},
            headers=admin_headers,
        )
        
        assert response.status_code == 200
        assert response.json()["status"] == "cancelled"
