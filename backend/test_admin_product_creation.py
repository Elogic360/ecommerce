#!/usr/bin/env python3
import requests

# Test admin login and product creation
BASE_URL = "http://localhost:8000/api/v1"

def test_admin_login():
    print("Testing admin login...")
    response = requests.post(f"{BASE_URL}/auth/login", data={
        "username": "admin@shophub.com",
        "password": "admin123"
    })

    if response.status_code == 200:
        data = response.json()
        token = data.get("access_token")
        print("✅ Admin login successful")
        return token
    else:
        print(f"❌ Admin login failed: {response.status_code} - {response.text}")
        return None

def test_create_product(token):
    print("Testing product creation...")
    headers = {"Authorization": f"Bearer {token}"}
    product_data = {
        "name": "Test Product",
        "description": "A test product",
        "price": 29.99,
        "stock": 10,
        "sku": "TEST001",
        "is_active": True
    }

    response = requests.post(f"{BASE_URL}/admin/products", json=product_data, headers=headers)

    if response.status_code == 201:
        print("✅ Product creation successful")
        return response.json()
    else:
        print(f"❌ Product creation failed: {response.status_code} - {response.text}")
        return None

if __name__ == "__main__":
    token = test_admin_login()
    if token:
        product = test_create_product(token)
        if product:
            print(f"Created product: {product['name']} (ID: {product['id']})")