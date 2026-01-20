#!/usr/bin/env python3
import requests

# Test the image URL
image_url = "http://localhost:8000/uploads/products/d0a0a241-f562-402f-80ab-bae29a8b0e3c.jpg"
print(f"Testing image URL: {image_url}")

try:
    response = requests.get(image_url)
    print(f"Status code: {response.status_code}")
    if response.status_code == 200:
        print("✅ Image is accessible!")
        print(f"Content type: {response.headers.get('content-type')}")
        print(f"Content length: {len(response.content)} bytes")
    else:
        print("❌ Image not accessible")
        print(f"Response: {response.text}")
except Exception as e:
    print(f"❌ Error: {e}")