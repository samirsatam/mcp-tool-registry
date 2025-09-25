#!/usr/bin/env python3
"""Setup script for initial security configuration."""

import os
import sys
from datetime import datetime, timedelta

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from mcp_tool_registry.auth import User, APIKey, get_password_hash, generate_api_key
from mcp_tool_registry.database import SessionLocal, engine
from sqlalchemy.orm import Session


def create_admin_user(db: Session, username: str = "admin", email: str = "admin@example.com", password: str = "admin"):
    """Create initial admin user."""
    # Check if admin user already exists
    existing_user = db.query(User).filter(User.username == username).first()
    if existing_user:
        print(f"Admin user '{username}' already exists")
        return existing_user
    
    # Create admin user
    hashed_password = get_password_hash(password)
    admin_user = User(
        username=username,
        email=email,
        hashed_password=hashed_password,
        is_admin=True,
        is_active=True
    )
    
    db.add(admin_user)
    db.commit()
    db.refresh(admin_user)
    
    print(f"✅ Created admin user: {username}")
    print(f"   Email: {email}")
    print(f"   Password: {password}")
    print(f"   ⚠️  Please change the password immediately!")
    
    return admin_user


def create_default_api_key(db: Session, name: str = "default-service"):
    """Create a default API key for service access."""
    # Check if API key already exists
    existing_key = db.query(APIKey).filter(APIKey.name == name).first()
    if existing_key:
        print(f"API key '{name}' already exists")
        return existing_key
    
    # Generate API key
    api_key_value = generate_api_key()
    api_key_hash = get_password_hash(api_key_value)
    
    # Create API key with full permissions
    api_key = APIKey(
        name=name,
        key_hash=api_key_hash,
        description="Default API key for service access",
        is_active=True,
        can_create=True,
        can_read=True,
        can_update=True,
        can_delete=False,  # Only admins can delete
        expires_at=datetime.utcnow() + timedelta(days=365)  # 1 year
    )
    
    db.add(api_key)
    db.commit()
    db.refresh(api_key)
    
    print(f"✅ Created API key: {name}")
    print(f"   Key: {api_key_value}")
    print(f"   Permissions: create, read, update")
    print(f"   Expires: {api_key.expires_at}")
    print(f"   ⚠️  Store this key securely!")
    
    return api_key


def main():
    """Main setup function."""
    print("🔐 Setting up MCP Tool Registry Security...")
    
    # Create database session
    db = SessionLocal()
    
    try:
        # Create admin user
        admin_user = create_admin_user(db)
        
        # Create default API key
        api_key = create_default_api_key(db)
        
        print("\n🎉 Security setup complete!")
        print("\n📋 Next steps:")
        print("1. Change the admin password:")
        print("   curl -X POST 'http://localhost:8000/auth/login' \\")
        print("     -H 'Content-Type: application/x-www-form-urlencoded' \\")
        print("     -d 'username=admin&password=admin'")
        print("\n2. Use the API key for service access:")
        print(f"   Authorization: Bearer {api_key.name}")
        print("\n3. Create additional API keys via admin panel:")
        print("   http://localhost:8000/docs")
        
    except Exception as e:
        print(f"❌ Error during setup: {e}")
        db.rollback()
        sys.exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    main()