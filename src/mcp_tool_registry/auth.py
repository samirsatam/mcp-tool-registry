"""Authentication and authorization system for MCP Tool Registry."""

import os
from datetime import datetime, timedelta
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel
from sqlalchemy.orm import Session

from .database import get_db
from .models import Base
from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text

# Security configuration
SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key-change-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30
REFRESH_TOKEN_EXPIRE_DAYS = 7

# Password hashing
pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")

# HTTP Bearer token scheme
security = HTTPBearer()


class APIKey(Base):
    """API Key model for service authentication."""
    __tablename__ = "api_keys"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, index=True, nullable=False)
    key_hash = Column(String(255), nullable=False)
    description = Column(Text)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_used = Column(DateTime)
    expires_at = Column(DateTime)
    
    # Permissions
    can_create = Column(Boolean, default=True)
    can_read = Column(Boolean, default=True)
    can_update = Column(Boolean, default=True)
    can_delete = Column(Boolean, default=False)


class User(Base):
    """User model for admin authentication."""
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    email = Column(String(100), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True)
    is_admin = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_login = Column(DateTime)


class Token(BaseModel):
    """Token response model."""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class TokenData(BaseModel):
    """Token data model."""
    username: Optional[str] = None
    api_key_name: Optional[str] = None
    is_admin: bool = False


class APIKeyCreate(BaseModel):
    """API Key creation model."""
    name: str
    description: Optional[str] = None
    expires_at: Optional[datetime] = None
    can_create: bool = True
    can_read: bool = True
    can_update: bool = True
    can_delete: bool = False


class APIKeyResponse(BaseModel):
    """API Key response model."""
    id: int
    name: str
    description: Optional[str]
    is_active: bool
    created_at: datetime
    expires_at: Optional[datetime]
    can_create: bool
    can_read: bool
    can_update: bool
    can_delete: bool
    last_used: Optional[datetime]


class UserCreate(BaseModel):
    """User creation model."""
    username: str
    email: str
    password: str
    is_admin: bool = False


class UserResponse(BaseModel):
    """User response model."""
    id: int
    username: str
    email: str
    is_active: bool
    is_admin: bool
    created_at: datetime
    last_login: Optional[datetime]


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash."""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Hash a password."""
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create a JWT access token."""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def create_refresh_token(data: dict) -> str:
    """Create a JWT refresh token."""
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire, "type": "refresh"})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def verify_token(token: str) -> TokenData:
    """Verify and decode a JWT token."""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        api_key_name: str = payload.get("api_key")
        is_admin: bool = payload.get("is_admin", False)
        
        if username is None and api_key_name is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        return TokenData(
            username=username,
            api_key_name=api_key_name,
            is_admin=is_admin
        )
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
            headers={"WWW-Authenticate": "Bearer"},
        )


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> TokenData:
    """Get current authenticated user from token."""
    token = credentials.credentials
    
    # Check if this is an API key (starts with "mcp_")
    if token.startswith("mcp_"):
        # This is an API key, authenticate it directly
        api_key = authenticate_api_key(token, db)
        if not api_key:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid API key",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        if not api_key.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="API key is disabled",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # Check if API key is expired
        if api_key.expires_at and api_key.expires_at < datetime.utcnow():
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="API key expired",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # Update last_used timestamp
        api_key.last_used = datetime.utcnow()
        db.commit()
        
        return TokenData(
            username=None,
            api_key_name=api_key.name,
            is_admin=False
        )
    else:
        # This is a JWT token
        token_data = verify_token(token)
        
        # Update last_used for API keys
        if token_data.api_key_name:
            api_key = db.query(APIKey).filter(
                APIKey.name == token_data.api_key_name,
                APIKey.is_active == True
            ).first()
            
            if not api_key:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="API key not found or inactive",
                    headers={"WWW-Authenticate": "Bearer"},
                )
            
            # Check if API key is expired
            if api_key.expires_at and api_key.expires_at < datetime.utcnow():
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="API key expired",
                    headers={"WWW-Authenticate": "Bearer"},
                )
            
            # Update last_used timestamp
            api_key.last_used = datetime.utcnow()
            db.commit()
        
        return token_data


def require_permission(permission: str):
    """Decorator to require specific permission."""
    def permission_checker(current_user: TokenData = Depends(get_current_user), db: Session = Depends(get_db)):
        if current_user.is_admin:
            return current_user
        
        # For API keys, check specific permission
        if current_user.api_key_name:
            api_key = db.query(APIKey).filter(
                APIKey.name == current_user.api_key_name,
                APIKey.is_active == True
            ).first()
            
            if not api_key:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="API key not found",
                )
            
            # Check permission
            if permission == "create" and not api_key.can_create:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Insufficient permissions: cannot create tools",
                )
            elif permission == "read" and not api_key.can_read:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Insufficient permissions: cannot read tools",
                )
            elif permission == "update" and not api_key.can_update:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Insufficient permissions: cannot update tools",
                )
            elif permission == "delete" and not api_key.can_delete:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Insufficient permissions: cannot delete tools",
                )
        
        return current_user
    
    return permission_checker


def require_admin(current_user: TokenData = Depends(get_current_user)) -> TokenData:
    """Require admin privileges."""
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required",
        )
    return current_user


def authenticate_api_key(api_key: str, db: Session) -> Optional[APIKey]:
    """Authenticate an API key."""
    # Hash the provided key and compare with stored hashes
    for stored_key in db.query(APIKey).filter(APIKey.is_active == True).all():
        if verify_password(api_key, stored_key.key_hash):
            return stored_key
    return None


def generate_api_key() -> str:
    """Generate a new API key."""
    import secrets
    return f"mcp_{secrets.token_urlsafe(32)}"