"""
Database Integration Test Script
Location: backend/test_integration.py

Run this script to verify complete database integration
"""
import sys
import asyncio
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
import requests
import json

# Configuration
DB_URL = "postgresql://ecommerce_user:commercePASS@localhost:5432/ecommerce"
API_URL = "http://localhost:8000/api/v1"

def print_section(title):
    """Print formatted section header"""
    print("\n" + "="*60)
    print(f"  {title}")
    print("="*60)

def test_database_connection():
    """Test 1: Database Connection"""
    print_section("TEST 1: Database Connection")
    try:
        engine = create_engine(DB_URL)
        with engine.connect() as conn:
            result = conn.execute(text("SELECT version();"))
            row = result.fetchone()
            if row is None:
                print(f"❌ No version information returned")
                return False
            version = row[0]
            print(f"✅ Database connected successfully")
            print(f"   PostgreSQL version: {version}")
            return True
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        return False

def test_tables_exist():
    """Test 2: Check if all required tables exist"""
    print_section("TEST 2: Database Tables")

    required_tables = [
        'users', 'addresses', 'products', 'categories',
        'product_images', 'product_variations', 'reviews',
        'cart_items', 'orders', 'order_items', 'payments',
        'inventory_logs'
    ]

    try:
        engine = create_engine(DB_URL)
        with engine.connect() as conn:
            result = conn.execute(text("""
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = 'public'
            """))
            existing_tables = [row[0] for row in result]

            missing_tables = set(required_tables) - set(existing_tables)

            if not missing_tables:
                print(f"✅ All required tables exist ({len(required_tables)} tables)")
                for table in sorted(required_tables):
                    print(f"   ✓ {table}")
                return True
            else:
                print(f"❌ Missing tables: {missing_tables}")
                return False
    except Exception as e:
        print(f"❌ Error checking tables: {e}")
        return False

def test_admin_user_exists():
    """Test 3: Check if admin user exists"""
    print_section("TEST 3: Admin User")

    try:
        engine = create_engine(DB_URL)
        with engine.connect() as conn:
            result = conn.execute(text("""
                SELECT id, username, email, role, is_active
                FROM users
                WHERE role = 'admin'
                LIMIT 1
            """))
            admin = result.fetchone()

            if admin:
                print(f"✅ Admin user found")
                print(f"   ID: {admin[0]}")
                print(f"   Username: {admin[1]}")
                print(f"   Email: {admin[2]}")
                print(f"   Role: {admin[3]}")
                print(f"   Active: {admin[4]}")
                return True
            else:
                print(f"❌ No admin user found")
                print(f"   Please create an admin user first")
                return False
    except Exception as e:
        print(f"❌ Error checking admin user: {e}")
        return False

def test_api_health():
    """Test 4: API Health Check"""
    print_section("TEST 4: API Health")

    try:
        response = requests.get(f"{API_URL}/health", timeout=5)
        if response.status_code == 200:
            data = response.json()
            print(f"✅ API is healthy")
            print(f"   Status: {data.get('status')}")
            print(f"   Database: {data.get('database')}")
            return True
        else:
            print(f"❌ API returned status code: {response.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        print(f"❌ Cannot connect to API at {API_URL}")
        print(f"   Make sure the backend server is running")
        return False
    except Exception as e:
        print(f"❌ API health check failed: {e}")
        return False

def test_api_categories():
    """Test 5: API Categories Endpoint"""
    print_section("TEST 5: API Categories")

    try:
        response = requests.get(f"{API_URL}/categories", timeout=5)
        if response.status_code == 200:
            categories = response.json()
            print(f"✅ Categories endpoint working")
            print(f"   Found {len(categories)} categories")
            for cat in categories[:3]:
                print(f"   - {cat['name']}")
            return True
        else:
            print(f"❌ Categories endpoint returned: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Categories test failed: {e}")
        return False

def test_api_products():
    """Test 6: API Products Endpoint"""
    print_section("TEST 6: API Products")

    try:
        response = requests.get(f"{API_URL}/products?limit=5", timeout=5)
        if response.status_code == 200:
            data = response.json()
            products = data.get('products', [])
            print(f"✅ Products endpoint working")
            print(f"   Total products: {data.get('total', 0)}")
            print(f"   Showing first {len(products)} products")
            for prod in products[:3]:
                print(f"   - {prod['name']} (${prod['price']})")
            return True
        else:
            print(f"❌ Products endpoint returned: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Products test failed: {e}")
        return False

def test_admin_login():
    """Test 7: Admin Login"""
    print_section("TEST 7: Admin Login")

    try:
        response = requests.post(
            f"{API_URL}/auth/login",
            data={"username": "admin", "password": "admin123"},
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            timeout=5
        )

        if response.status_code == 200:
            data = response.json()
            token = data.get('access_token')
            print(f"✅ Admin login successful")
            print(f"   Token type: {data.get('token_type')}")
            print(f"   Token (first 50 chars): {token[:50]}...")
            return token
        else:
            print(f"❌ Admin login failed: {response.status_code}")
            print(f"   Response: {response.text}")
            return None
    except Exception as e:
        print(f"❌ Admin login test failed: {e}")
        return None

def test_admin_dashboard(token):
    """Test 8: Admin Dashboard Stats"""
    print_section("TEST 8: Admin Dashboard Stats")

    if not token:
        print(f"⚠️  Skipping (no auth token)")
        return False

    try:
        response = requests.get(
            f"{API_URL}/admin/dashboard/stats",
            headers={"Authorization": f"Bearer {token}"},
            timeout=5
        )

        if response.status_code == 200:
            data = response.json()
            print(f"✅ Admin dashboard working")
            print(f"   Total Revenue: ${data.get('total_revenue', 0)}")
            print(f"   Total Orders: {data.get('total_orders', 0)}")
            print(f"   Total Products: {data.get('total_products', 0)}")
            print(f"   Total Users: {data.get('total_users', 0)}")
            return True
        else:
            print(f"❌ Dashboard returned: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Dashboard test failed: {e}")
        return False

def test_database_relationships():
    """Test 9: Database Relationships"""
    print_section("TEST 9: Database Relationships")

    try:
        engine = create_engine(DB_URL)
        with engine.connect() as conn:
            # Test product-category relationship
            result = conn.execute(text("""
                SELECT p.name, c.name as category_name
                FROM products p
                JOIN product_category_association pca ON p.id = pca.product_id
                JOIN categories c ON c.id = pca.category_id
                LIMIT 3
            """))
            product_cats = result.fetchall()

            if product_cats:
                print(f"✅ Product-Category relationships working")
                for pc in product_cats:
                    print(f"   {pc[0]} → {pc[1]}")

            # Test order-user relationship
            result = conn.execute(text("""
                SELECT o.order_number, u.username
                FROM orders o
                JOIN users u ON o.user_id = u.id
                LIMIT 3
            """))
            order_users = result.fetchall()

            if order_users:
                print(f"✅ Order-User relationships working")
                for ou in order_users:
                    print(f"   Order {ou[0]} → User {ou[1]}")

            return True
    except Exception as e:
        print(f"❌ Relationships test failed: {e}")
        return False

def test_inventory_logging():
    """Test 10: Inventory Logging"""
    print_section("TEST 10: Inventory Logging System")

    try:
        engine = create_engine(DB_URL)
        with engine.connect() as conn:
            result = conn.execute(text("""
                SELECT COUNT(*) FROM inventory_logs
            """))
            count_row = result.fetchone()
            count = count_row[0] if count_row else 0

            result = conn.execute(text("""
                SELECT il.reason, p.name, il.change_quantity, il.new_stock
                FROM inventory_logs il
                LEFT JOIN products p ON il.product_id = p.id
                ORDER BY il.created_at DESC
                LIMIT 5
            """))
            logs = result.fetchall()

            print(f"✅ Inventory logging system active")
            print(f"   Total logs: {count}")
            print(f"   Recent changes:")
            for log in logs:
                print(f"   - {log[0]}: {log[1]} ({log[2]:+d} → {log[3]})")

            return True
    except Exception as e:
        print(f"❌ Inventory logging test failed: {e}")
        return False

def run_all_tests():
    """Run all integration tests"""
    print("\n" + "🚀 " * 20)
    print("  E-COMMERCE SYSTEM INTEGRATION TEST SUITE")
    print("🚀 " * 20)

    results = []

    # Run tests in sequence
    results.append(("Database Connection", test_database_connection()))
    results.append(("Database Tables", test_tables_exist()))
    results.append(("Admin User", test_admin_user_exists()))
    results.append(("API Health", test_api_health()))
    results.append(("API Categories", test_api_categories()))
    results.append(("API Products", test_api_products()))

    admin_token = test_admin_login()
    results.append(("Admin Login", admin_token is not None))
    results.append(("Admin Dashboard", test_admin_dashboard(admin_token)))

    results.append(("Database Relationships", test_database_relationships()))
    results.append(("Inventory Logging", test_inventory_logging()))

    # Print summary
    print_section("TEST SUMMARY")
    passed = sum(1 for _, result in results if result)
    total = len(results)

    print(f"\nTests Passed: {passed}/{total}")
    print("\nDetailed Results:")
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"  {status} - {test_name}")

    if passed == total:
        print("\n" + "🎉 " * 20)
        print("  ALL TESTS PASSED - SYSTEM FULLY INTEGRATED!")
        print("🎉 " * 20)
        return True
    else:
        print("\n" + "⚠️  " * 20)
        print(f"  {total - passed} TEST(S) FAILED - CHECK CONFIGURATION")
        print("⚉ " * 20)
        return False

if __name__ == "__main__":
    print("\n⚙️  Starting Integration Tests...")
    print("📝 Make sure:")
    print("   1. PostgreSQL is running")
    print("   2. Database is created and schema is applied")
    print("   3. Backend server is running (uvicorn)")
    print("   4. Admin user exists in database")

    input("\nPress Enter to continue...")

    success = run_all_tests()
    sys.exit(0 if success else 1)