import sys
from pathlib import Path

# Add backend to path (similar to test_db_connection.py)
# This must be at the very top before any 'from app.' imports
backend_path = Path(__file__).parent.parent
sys.path.insert(0, str(backend_path))

import asyncio
from decimal import Decimal
from sqlalchemy.orm import Session
from app.db.session import SessionLocal
from app.models.customer import User, Address, Role
from app.models.product import Product, Category, ProductImage, ProductVariation, Review, generate_slug
from app.core.security import get_password_hash
import random

# Sample Data
USERS = [
    {"email": "admin@shophub.com", "username": "admin", "full_name": "Admin User", "password": "Admin123!", "is_admin": True},
    {"email": "john.doe@example.com", "username": "john_doe", "full_name": "John Doe", "password": "Password123!", "is_admin": False},
    {"email": "jane.smith@example.com", "username": "jane_smith", "full_name": "Jane Smith", "password": "Password123!", "is_admin": False},
    {"email": "inventory@shophub.com", "username": "inventory_mgr", "full_name": "Inventory Manager", "password": "Inventory123!", "role": "INVENTORY_MANAGER"},
]

CATEGORIES = [
    {"name": "Electronics", "description": "Gadgets and electronic devices", "icon": "fa-laptop", "image_url": "https://images.unsplash.com/photo-1498049794561-7780e7231661?w=300", "sort_order": 1},
    {"name": "Smartphones", "description": "Mobile phones and accessories", "icon": "fa-mobile", "parent": "Electronics", "sort_order": 1},
    {"name": "Laptops", "description": "Portable computers", "icon": "fa-laptop", "parent": "Electronics", "sort_order": 2},
    {"name": "Audio", "description": "Headphones, speakers and audio equipment", "icon": "fa-headphones", "parent": "Electronics", "sort_order": 3},
    {"name": "Fashion", "description": "Clothing and accessories", "icon": "fa-tshirt", "image_url": "https://images.unsplash.com/photo-1445205170230-053b83016050?w=300", "sort_order": 2},
    {"name": "Men's Clothing", "description": "Apparel for men", "parent": "Fashion", "sort_order": 1},
    {"name": "Women's Clothing", "description": "Apparel for women", "parent": "Fashion", "sort_order": 2},
    {"name": "Home & Kitchen", "description": "Home appliances and kitchenware", "icon": "fa-home", "image_url": "https://images.unsplash.com/photo-1556911220-bff31c812dba?w=300", "sort_order": 3},
    {"name": "Books", "description": "Fiction, non-fiction, and educational books", "icon": "fa-book", "image_url": "https://images.unsplash.com/photo-1512820790803-83ca734da794?w=300", "sort_order": 4},
    {"name": "Sports & Outdoors", "description": "Sports equipment and outdoor gear", "icon": "fa-futbol", "image_url": "https://images.unsplash.com/photo-1461896836934-ffe607ba8211?w=300", "sort_order": 5},
    {"name": "Toys & Games", "description": "Toys, board games and puzzles", "icon": "fa-puzzle-piece", "image_url": "https://images.unsplash.com/photo-1558060370-d644479cb6f7?w=300", "sort_order": 6},
]

PRODUCTS = [
    # Featured Products - Electronics
    {
        "name": "Wireless Gaming Headset Pro", "price": Decimal("89.99"), "original_price": Decimal("129.99"), "cost_price": Decimal("45.00"),
        "stock": 50, "low_stock_threshold": 10, "sku": "WGH-001", "brand": "TechPro",
        "description": "High-fidelity wireless gaming headset with advanced noise-cancelling microphone, 7.1 surround sound, and 30-hour battery life.",
        "short_description": "Premium wireless gaming headset with 7.1 surround sound",
        "is_featured": True, "category": "Audio", "weight": Decimal("0.35"),
        "meta_title": "Wireless Gaming Headset Pro | TechPro",
        "meta_description": "Experience immersive gaming with our professional wireless headset featuring 7.1 surround sound.",
        "primary_image": "https://images.unsplash.com/photo-1599669454699-248893623440?w=400",
        "images": ["https://images.unsplash.com/photo-1599669454699-248893623440?w=600"],
        "variations": [
            {"name": "Color", "value": "Black", "stock": 30},
            {"name": "Color", "value": "White", "stock": 15, "price_adjustment": Decimal("5.00")},
            {"name": "Color", "value": "Red", "stock": 5, "price_adjustment": Decimal("10.00")}
        ]
    },
    {
        "name": "Smart Fitness Watch X200", "price": Decimal("199.99"), "cost_price": Decimal("85.00"),
        "stock": 75, "sku": "SFW-002", "brand": "FitTech",
        "description": "Advanced smartwatch with heart rate monitoring, GPS tracking, sleep analysis, and 14-day battery life. Water resistant to 50m.",
        "short_description": "Premium fitness tracking smartwatch with GPS",
        "is_featured": True, "category": "Electronics", "weight": Decimal("0.05"),
        "primary_image": "https://images.unsplash.com/photo-1523275335684-37898b6baf30?w=400",
        "images": ["https://images.unsplash.com/photo-1523275335684-37898b6baf30?w=600"],
        "variations": [
            {"name": "Strap", "value": "Silicone - Black", "stock": 40},
            {"name": "Strap", "value": "Leather - Brown", "stock": 20, "price_adjustment": Decimal("25.00")},
            {"name": "Strap", "value": "Metal - Silver", "stock": 15, "price_adjustment": Decimal("50.00")}
        ]
    },
    {
        "name": "Portable Bluetooth Speaker M3", "price": Decimal("49.99"), "original_price": Decimal("79.99"),
        "stock": 120, "sku": "PBS-003", "brand": "SoundWave",
        "description": "Compact and powerful bluetooth speaker with 360° sound, IPX7 waterproof rating, and 24-hour battery life.",
        "short_description": "Waterproof portable Bluetooth speaker",
        "is_featured": True, "category": "Audio", "weight": Decimal("0.45"),
        "primary_image": "https://images.unsplash.com/photo-1608043152269-423dbba4e7e1?w=400",
        "images": ["https://images.unsplash.com/photo-1608043152269-423dbba4e7e1?w=600"],
        "variations": []
    },
    {
        "name": "MacBook Pro 14-inch", "price": Decimal("1999.00"), "cost_price": Decimal("1450.00"),
        "stock": 25, "sku": "MBP-014", "brand": "Apple",
        "description": "Powerful laptop with M3 Pro chip, 18GB unified memory, 512GB SSD, and stunning Liquid Retina XDR display.",
        "short_description": "Professional laptop with M3 Pro chip",
        "is_featured": True, "category": "Laptops", "weight": Decimal("1.55"),
        "primary_image": "https://images.unsplash.com/photo-1517336714731-489689fd1ca8?w=400",
        "images": [],
        "variations": [
            {"name": "Storage", "value": "512GB SSD", "stock": 15},
            {"name": "Storage", "value": "1TB SSD", "stock": 10, "price_adjustment": Decimal("200.00")}
        ]
    },
    # Fashion
    {
        "name": "Men's Premium Leather Jacket", "price": Decimal("250.00"), "cost_price": Decimal("120.00"),
        "stock": 30, "sku": "MLJ-101", "brand": "StyleHub", "category": "Men's Clothing",
        "description": "Genuine leather jacket with premium stitching, classic design, and warm inner lining.",
        "primary_image": "https://images.unsplash.com/photo-1521223890158-f9f7c3d5d504?w=400",
        "variations": [
            {"name": "Size", "value": "S", "stock": 5},
            {"name": "Size", "value": "M", "stock": 10},
            {"name": "Size", "value": "L", "stock": 10},
            {"name": "Size", "value": "XL", "stock": 5}
        ]
    },
    {
        "name": "Summer Floral Dress", "price": Decimal("75.00"), "original_price": Decimal("95.00"),
        "stock": 90, "sku": "SD-102", "brand": "StyleHub", "category": "Women's Clothing",
        "description": "Light and elegant summer dress with beautiful floral pattern, perfect for warm days.",
        "primary_image": "https://images.unsplash.com/photo-1572804013427-4d7ca7268211?w=400",
        "is_featured": True,
        "variations": [
            {"name": "Size", "value": "XS", "stock": 15},
            {"name": "Size", "value": "S", "stock": 25},
            {"name": "Size", "value": "M", "stock": 30},
            {"name": "Size", "value": "L", "stock": 20}
        ]
    },
    # Home & Kitchen
    {
        "name": "Espresso Coffee Machine Pro", "price": Decimal("350.00"), "cost_price": Decimal("180.00"),
        "stock": 20, "sku": "ECM-201", "brand": "HomePro", "category": "Home & Kitchen",
        "description": "Professional-grade espresso machine with 15-bar pressure pump, milk frother, and programmable settings.",
        "primary_image": "https://images.unsplash.com/photo-1517668808822-9ebb02f2a0e6?w=400"
    },
    {
        "name": "Modern LED Desk Lamp", "price": Decimal("65.00"),
        "stock": 60, "sku": "MDL-202", "brand": "LightUp", "category": "Home & Kitchen",
        "description": "Minimalist desk lamp with adjustable brightness, color temperature control, and USB charging port.",
        "primary_image": "https://images.unsplash.com/photo-1507473885765-e6ed0a0f252d?w=400"
    },
    # Books
    {
        "name": "The Alchemist", "price": Decimal("15.99"),
        "stock": 200, "sku": "BK-301", "brand": "Paulo Coelho", "category": "Books",
        "description": "A magical story about following your dreams and listening to your heart.",
        "primary_image": "https://images.unsplash.com/photo-1544947950-fa07a98d237f?w=400",
        "is_digital": False
    },
    {
        "name": "Science Fiction Anthology", "price": Decimal("22.50"),
        "stock": 120, "sku": "BK-302", "brand": "Various Authors", "category": "Books",
        "description": "Collection of the best science fiction short stories from award-winning authors.",
        "primary_image": "https://images.unsplash.com/photo-1532187863486-abf9dbad1b69?w=400"
    },
    # Sports & Outdoors
    {
        "name": "Premium Yoga Mat", "price": Decimal("45.00"), "original_price": Decimal("55.00"),
        "stock": 150, "sku": "YM-401", "brand": "FlexiFit", "category": "Sports & Outdoors",
        "description": "Extra thick yoga mat with non-slip surface, eco-friendly material, and carrying strap.",
        "primary_image": "https://images.unsplash.com/photo-1544367567-0f2fcb009e0b?w=400",
        "weight": Decimal("1.2"), "length": Decimal("183"), "width": Decimal("61")
    },
    {
        "name": "Professional Running Shoes", "price": Decimal("120.00"),
        "stock": 80, "sku": "RS-402", "brand": "RunFast", "category": "Sports & Outdoors",
        "description": "Lightweight running shoes with responsive cushioning and breathable mesh upper.",
        "primary_image": "https://images.unsplash.com/photo-1542291026-7eec264c27ab?w=400",
        "variations": [
            {"name": "Size", "value": "8", "stock": 15},
            {"name": "Size", "value": "9", "stock": 20},
            {"name": "Size", "value": "10", "stock": 25},
            {"name": "Size", "value": "11", "stock": 15},
            {"name": "Size", "value": "12", "stock": 5}
        ]
    },
    {
        "name": "Adjustable Dumbbell Set", "price": Decimal("199.00"), "original_price": Decimal("249.00"),
        "stock": 50, "sku": "DS-403", "brand": "IronGrip", "category": "Sports & Outdoors",
        "description": "Space-saving adjustable dumbbells from 5-52.5 lbs per dumbbell, perfect for home workouts.",
        "primary_image": "https://images.unsplash.com/photo-1584735935682-2f2b69dff9d2?w=400",
        "weight": Decimal("48")
    },
    # Toys & Games
    {
        "name": "Wooden Building Block Set", "price": Decimal("35.00"),
        "stock": 100, "sku": "WBS-501", "brand": "PlayfulMinds", "category": "Toys & Games",
        "description": "100-piece wooden block set in various shapes and colors for creative building.",
        "primary_image": "https://images.unsplash.com/photo-1596461404969-9ae70f2830c1?w=400"
    },
    {
        "name": "Classic Chess Set", "price": Decimal("65.00"),
        "stock": 70, "sku": "CS-502", "brand": "MindGames", "category": "Toys & Games",
        "description": "Handcrafted wooden chess set with weighted pieces and folding board.",
        "primary_image": "https://images.unsplash.com/photo-1580541832626-2a716248cb83?w=400",
        "is_featured": True
    },
]

REVIEWS = [
    {"product_sku": "WGH-001", "user": "john_doe", "rating": 5, "title": "Amazing Sound Quality!", "comment": "The sound quality is incredible and they are very comfortable for long gaming sessions."},
    {"product_sku": "SFW-002", "user": "jane_smith", "rating": 4, "title": "Great fitness tracker", "comment": "I love this watch! Battery life is impressive, though GPS accuracy could be a bit better."},
    {"product_sku": "PBS-003", "user": "john_doe", "rating": 5, "title": "Perfect for beach days", "comment": "Loud and clear sound, truly waterproof, and the battery lasts forever!"},
    {"product_sku": "WGH-001", "user": "jane_smith", "rating": 4, "title": "Good for gaming", "comment": "Great for gaming, but not the best for music listening."},
    {"product_sku": "MBP-014", "user": "john_doe", "rating": 5, "title": "Best laptop ever", "comment": "Absolutely love this machine. Fast, beautiful display, and amazing battery life."},
    {"product_sku": "SD-102", "user": "jane_smith", "rating": 5, "title": "Perfect summer dress", "comment": "The fabric is so light and comfortable. Great for hot days!"},
    {"product_sku": "CS-502", "user": "john_doe", "rating": 5, "title": "Beautiful craftsmanship", "comment": "The pieces are weighted perfectly and the board is gorgeous."},
]


def seed_data():
    db: Session = SessionLocal()
    try:
        print("Seeding data...")

        # Clear existing data
        db.query(Review).delete()
        db.query(ProductVariation).delete()
        db.query(ProductImage).delete()
        db.query(Product).delete()
        db.query(Category).delete()
        db.query(User).delete()
        db.commit()
        print("Cleared existing data.")

        # Create users
        user_map = {}
        for user_data in USERS:
            role = Role.ADMIN if user_data.get("is_admin") else Role.USER
            if user_data.get("role") == "INVENTORY_MANAGER":
                role = Role.INVENTORY_MANAGER
            db_user = User(
                email=user_data["email"],
                username=user_data["username"],
                full_name=user_data["full_name"],
                hashed_password=get_password_hash(user_data["password"]),
                role=role,
                is_active=True
            )
            db.add(db_user)
            db.commit()
            db.refresh(db_user)
            user_map[user_data["username"]] = db_user
        print(f"Created {len(user_map)} users.")

        # Create categories (handle parent references)
        category_map = {}
        # First pass: create all categories without parents
        for cat_data in CATEGORIES:
            if "parent" not in cat_data:
                slug = generate_slug(cat_data["name"])
                cat_dict = {k: v for k, v in cat_data.items() if k != "parent"}
                db_cat = Category(slug=slug, **cat_dict)
                db.add(db_cat)
                db.commit()
                db.refresh(db_cat)
                category_map[cat_data["name"]] = db_cat
        
        # Second pass: create child categories
        for cat_data in CATEGORIES:
            if "parent" in cat_data:
                parent = category_map.get(cat_data["parent"])
                slug = generate_slug(cat_data["name"])
                cat_dict = {k: v for k, v in cat_data.items() if k != "parent"}
                db_cat = Category(slug=slug, parent_id=parent.id if parent else None, **cat_dict)
                db.add(db_cat)
                db.commit()
                db.refresh(db_cat)
                category_map[cat_data["name"]] = db_cat
        print(f"Created {len(category_map)} categories.")

        # Create products
        product_map = {}
        for prod_data in PRODUCTS:
            cat_name = prod_data.pop("category")
            images = prod_data.pop("images", [])
            variations = prod_data.pop("variations", [])
            
            # Generate slug
            slug = generate_slug(prod_data["name"])
            
            # Create product with enhanced fields
            db_prod = Product(
                slug=slug,
                rating=Decimal(str(random.uniform(3.5, 5.0))),
                review_count=random.randint(10, 500),
                view_count=random.randint(100, 5000),
                sales_count=random.randint(10, 500),
                **prod_data
            )
            
            # Add category
            if cat_name in category_map:
                db_prod.categories.append(category_map[cat_name])
            
            db.add(db_prod)
            db.commit()
            db.refresh(db_prod)
            product_map[prod_data["sku"]] = db_prod

            # Add images
            for i, img_url in enumerate(images):
                db_img = ProductImage(
                    product_id=db_prod.id, 
                    image_url=img_url,
                    is_primary=(i == 0),
                    sort_order=i
                )
                db.add(db_img)
            
            # Add variations
            for var_data in variations:
                var_sku = f"{prod_data['sku']}-{var_data['value'][:3].upper()}"
                db_var = ProductVariation(
                    product_id=db_prod.id,
                    sku=var_sku,
                    **var_data
                )
                db.add(db_var)

            db.commit()
        print(f"Created {len(product_map)} products.")

        # Create reviews
        review_count = 0
        for review_data in REVIEWS:
            product = product_map.get(review_data["product_sku"])
            user = user_map.get(review_data["user"])
            if product and user:
                db_review = Review(
                    product_id=product.id,
                    user_id=user.id,
                    rating=review_data["rating"],
                    title=review_data["title"],
                    comment=review_data["comment"],
                    is_verified_purchase=random.choice([True, False])
                )
                db.add(db_review)
                review_count += 1
        db.commit()
        print(f"Created {review_count} reviews.")

        print("\n✅ Data seeding complete!")
        print(f"   - Users: {len(user_map)}")
        print(f"   - Categories: {len(category_map)}")
        print(f"   - Products: {len(product_map)}")
        print(f"   - Reviews: {review_count}")
        print("\nAdmin credentials: admin@shophub.com / Admin123!")

    except Exception as e:
        print(f"Error seeding data: {e}")
        db.rollback()
        raise
    finally:
        db.close()

if __name__ == "__main__":
    seed_data()
