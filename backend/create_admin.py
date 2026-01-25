#!/usr/bin/env python3
"""
Admin User Creation Script
Creates an admin user for the Neatify - Cleaning Supplies & Tools platform.

Usage:
    python create_admin.py
    python create_admin.py --email admin@example.com --username admin --password securepass123

Environment variables (optional):
    ADMIN_EMAIL: Admin email address
    ADMIN_USERNAME: Admin username
    ADMIN_PASSWORD: Admin password (plain text, will be hashed)
"""
import argparse
import os
import sys
import getpass
from datetime import datetime, timezone

# Add the backend directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.db.session import SessionLocal
from app.models.customer import User, Role
from app.core.security import get_password_hash, check_password_strength
from app.core.config import settings


def validate_email(email: str) -> bool:
    """Basic email validation"""
    import re
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None


def validate_username(username: str) -> bool:
    """Validate username format"""
    import re
    if len(username) < 3 or len(username) > 50:
        return False
    return re.match(r'^[a-zA-Z0-9_-]+$', username) is not None


def create_admin_user(
    email: str,
    username: str,
    password: str,
    full_name: str = "Admin User",
    force: bool = False
) -> bool:
    """
    Create an admin user in the database.
    
    Args:
        email: Admin email address
        username: Admin username
        password: Plain text password (will be hashed)
        full_name: Full name for the admin user
        force: If True, update existing user to admin
        
    Returns:
        True if successful, False otherwise
    """
    db = SessionLocal()
    
    try:
        # Check if user exists by email
        existing_email = db.query(User).filter(User.email == email).first()
        
        if existing_email:
            if force:
                # Update existing user to admin
                existing_email.role = Role.ADMIN.value
                existing_email.is_active = True
                existing_email.hashed_password = get_password_hash(password)
                existing_email.updated_at = datetime.now(timezone.utc)
                db.commit()
                print(f"✅ Updated existing user '{email}' to admin role")
                return True
            else:
                print(f"❌ User with email '{email}' already exists!")
                print("   Use --force to update this user to admin role.")
                return False
        
        # Check if username exists
        existing_username = db.query(User).filter(User.username == username).first()
        if existing_username:
            print(f"❌ Username '{username}' is already taken!")
            return False
        
        # Create admin user
        admin = User(
            email=email,
            username=username,
            full_name=full_name,
            hashed_password=get_password_hash(password),
            role=Role.ADMIN.value,
            is_active=True,
            created_at=datetime.now(timezone.utc),
        )
        
        db.add(admin)
        db.commit()
        db.refresh(admin)
        
        print("\n" + "=" * 50)
        print("✅ ADMIN USER CREATED SUCCESSFULLY")
        print("=" * 50)
        print(f"   Email:    {email}")
        print(f"   Username: {username}")
        print(f"   Role:     {Role.ADMIN.value}")
        print(f"   ID:       {admin.id}")
        print("=" * 50)
        print("\n⚠️  IMPORTANT: Change the default password in production!")
        print("\n")
        
        return True
        
    except Exception as e:
        db.rollback()
        print(f"❌ Error creating admin user: {e}")
        return False
        
    finally:
        db.close()


def main():
    """Main entry point for admin creation script"""
    
    parser = argparse.ArgumentParser(
        description="Create an admin user for Neatify E-Commerce",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    # Interactive mode (prompts for input)
    python create_admin.py

    # Command line arguments
    python create_admin.py --email admin@shop.com --username admin --password MySecurePass123!

    # Use environment variables
    ADMIN_EMAIL=admin@shop.com ADMIN_PASSWORD=secret python create_admin.py
        """
    )
    
    parser.add_argument(
        "--email", "-e",
        help="Admin email address",
        default=os.environ.get("ADMIN_EMAIL")
    )
    parser.add_argument(
        "--username", "-u",
        help="Admin username",
        default=os.environ.get("ADMIN_USERNAME", "admin")
    )
    parser.add_argument(
        "--password", "-p",
        help="Admin password (will prompt if not provided)",
        default=os.environ.get("ADMIN_PASSWORD")
    )
    parser.add_argument(
        "--full-name", "-n",
        help="Full name for admin user",
        default="Admin User"
    )
    parser.add_argument(
        "--force", "-f",
        action="store_true",
        help="Force update if user already exists"
    )
    parser.add_argument(
        "--no-interactive",
        action="store_true",
        help="Don't prompt for missing values"
    )
    
    args = parser.parse_args()
    
    print("\n🔐 Neatify Admin User Creation")
    print("=" * 40 + "\n")
    
    # Get email
    email = args.email
    if not email and not args.no_interactive:
        email = input("Enter Neatify admin email [admin@neatify.market]: ").strip()
        if not email:
            email = "admin@neatify.market"
    
    if not email:
        print("❌ Email is required!")
        sys.exit(1)
    
    if not validate_email(email):
        print(f"❌ Invalid email format: {email}")
        sys.exit(1)
    
    # Get username
    username = args.username
    if not username and not args.no_interactive:
        username = input("Enter Neatify admin username [neatify_admin]: ").strip()
        if not username:
            username = "neatify_admin"
    
    if not username:
        username = "admin"
    
    if not validate_username(username):
        print(f"❌ Invalid username: {username}")
        print("   Username must be 3-50 characters, alphanumeric with underscores/hyphens only.")
        sys.exit(1)
    
    # Get password
    password = args.password
    if not password and not args.no_interactive:
        print("\nPassword requirements:")
        print("  - Minimum 8 characters")
        print("  - At least one uppercase letter")
        print("  - At least one lowercase letter")
        print("  - At least one digit")
        print("  - At least one special character")
        print()
        
        while True:
            password = getpass.getpass("Enter admin password: ")
            if len(password) < 8:
                print("❌ Password must be at least 8 characters!")
                continue
            
            password_confirm = getpass.getpass("Confirm password: ")
            if password != password_confirm:
                print("❌ Passwords don't match!")
                continue
            
            # Check password strength
            strength = check_password_strength(password)
            if strength["strength"] == "weak":
                print(f"⚠️  Password is weak. Suggestions: {', '.join(strength['suggestions'])}")
                if input("Use anyway? [y/N]: ").lower() != 'y':
                    continue
            
            break
    
    if not password:
        # Use default password for non-interactive mode
        password = "Admin123!"
        print(f"⚠️  Using default password: {password}")
    
    # Create the admin user
    success = create_admin_user(
        email=email,
        username=username,
        password=password,
        full_name=args.full_name,
        force=args.force
    )
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
