"""Admin endpoints for managing users and API keys."""

from datetime import datetime
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from .auth import (
    APIKey,
    APIKeyCreate,
    APIKeyResponse,
    User,
    UserCreate,
    UserResponse,
    generate_api_key,
    get_password_hash,
    require_admin,
    TokenData,
)
from .database import get_db

router = APIRouter(prefix="/admin", tags=["admin"])


@router.post("/api-keys", response_model=APIKeyResponse, status_code=201)
async def create_api_key(
    api_key_data: APIKeyCreate,
    current_user: TokenData = Depends(require_admin),
    db: Session = Depends(get_db),
) -> APIKeyResponse:
    """Create a new API key."""
    # Check if name already exists
    existing_key = db.query(APIKey).filter(APIKey.name == api_key_data.name).first()
    if existing_key:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="API key name already exists"
        )
    
    # Generate new API key
    api_key_value = generate_api_key()
    api_key_hash = get_password_hash(api_key_value)
    
    # Create API key record
    db_api_key = APIKey(
        name=api_key_data.name,
        key_hash=api_key_hash,
        description=api_key_data.description,
        expires_at=api_key_data.expires_at,
        can_create=api_key_data.can_create,
        can_read=api_key_data.can_read,
        can_update=api_key_data.can_update,
        can_delete=api_key_data.can_delete,
    )
    
    db.add(db_api_key)
    db.commit()
    db.refresh(db_api_key)
    
    # Return the API key (only shown once)
    response = APIKeyResponse(
        id=db_api_key.id,
        name=db_api_key.name,
        description=db_api_key.description,
        is_active=db_api_key.is_active,
        created_at=db_api_key.created_at,
        expires_at=db_api_key.expires_at,
        can_create=db_api_key.can_create,
        can_read=db_api_key.can_read,
        can_update=db_api_key.can_update,
        can_delete=db_api_key.can_delete,
        last_used=db_api_key.last_used,
    )
    
    # Log the API key value (in production, send via secure channel)
    print(f"NEW API KEY: {api_key_value}")
    
    return response


@router.get("/api-keys", response_model=List[APIKeyResponse])
async def list_api_keys(
    current_user: TokenData = Depends(require_admin),
    db: Session = Depends(get_db),
) -> List[APIKeyResponse]:
    """List all API keys."""
    api_keys = db.query(APIKey).all()
    return [
        APIKeyResponse(
            id=key.id,
            name=key.name,
            description=key.description,
            is_active=key.is_active,
            created_at=key.created_at,
            expires_at=key.expires_at,
            can_create=key.can_create,
            can_read=key.can_read,
            can_update=key.can_update,
            can_delete=key.can_delete,
            last_used=key.last_used,
        )
        for key in api_keys
    ]


@router.get("/api-keys/{key_id}", response_model=APIKeyResponse)
async def get_api_key(
    key_id: int,
    current_user: TokenData = Depends(require_admin),
    db: Session = Depends(get_db),
) -> APIKeyResponse:
    """Get a specific API key."""
    api_key = db.query(APIKey).filter(APIKey.id == key_id).first()
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="API key not found"
        )
    
    return APIKeyResponse(
        id=api_key.id,
        name=api_key.name,
        description=api_key.description,
        is_active=api_key.is_active,
        created_at=api_key.created_at,
        expires_at=api_key.expires_at,
        can_create=api_key.can_create,
        can_read=api_key.can_read,
        can_update=api_key.can_update,
        can_delete=api_key.can_delete,
        last_used=api_key.last_used,
    )


@router.put("/api-keys/{key_id}", response_model=APIKeyResponse)
async def update_api_key(
    key_id: int,
    api_key_data: APIKeyCreate,
    current_user: TokenData = Depends(require_admin),
    db: Session = Depends(get_db),
) -> APIKeyResponse:
    """Update an API key."""
    api_key = db.query(APIKey).filter(APIKey.id == key_id).first()
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="API key not found"
        )
    
    # Update fields
    api_key.name = api_key_data.name
    api_key.description = api_key_data.description
    api_key.expires_at = api_key_data.expires_at
    api_key.can_create = api_key_data.can_create
    api_key.can_read = api_key_data.can_read
    api_key.can_update = api_key_data.can_update
    api_key.can_delete = api_key_data.can_delete
    
    db.commit()
    db.refresh(api_key)
    
    return APIKeyResponse(
        id=api_key.id,
        name=api_key.name,
        description=api_key.description,
        is_active=api_key.is_active,
        created_at=api_key.created_at,
        expires_at=api_key.expires_at,
        can_create=api_key.can_create,
        can_read=api_key.can_read,
        can_update=api_key.can_update,
        can_delete=api_key.can_delete,
        last_used=api_key.last_used,
    )


@router.delete("/api-keys/{key_id}")
async def delete_api_key(
    key_id: int,
    current_user: TokenData = Depends(require_admin),
    db: Session = Depends(get_db),
) -> dict:
    """Delete an API key."""
    api_key = db.query(APIKey).filter(APIKey.id == key_id).first()
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="API key not found"
        )
    
    db.delete(api_key)
    db.commit()
    
    return {"message": "API key deleted successfully"}


@router.post("/api-keys/{key_id}/toggle")
async def toggle_api_key(
    key_id: int,
    current_user: TokenData = Depends(require_admin),
    db: Session = Depends(get_db),
) -> APIKeyResponse:
    """Toggle API key active status."""
    api_key = db.query(APIKey).filter(APIKey.id == key_id).first()
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="API key not found"
        )
    
    api_key.is_active = not api_key.is_active
    db.commit()
    db.refresh(api_key)
    
    return APIKeyResponse(
        id=api_key.id,
        name=api_key.name,
        description=api_key.description,
        is_active=api_key.is_active,
        created_at=api_key.created_at,
        expires_at=api_key.expires_at,
        can_create=api_key.can_create,
        can_read=api_key.can_read,
        can_update=api_key.can_update,
        can_delete=api_key.can_delete,
        last_used=api_key.last_used,
    )


@router.post("/users", response_model=UserResponse, status_code=201)
async def create_user(
    user_data: UserCreate,
    current_user: TokenData = Depends(require_admin),
    db: Session = Depends(get_db),
) -> UserResponse:
    """Create a new user."""
    # Check if username already exists
    existing_user = db.query(User).filter(User.username == user_data.username).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already exists"
        )
    
    # Check if email already exists
    existing_email = db.query(User).filter(User.email == user_data.email).first()
    if existing_email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already exists"
        )
    
    # Create user
    hashed_password = get_password_hash(user_data.password)
    db_user = User(
        username=user_data.username,
        email=user_data.email,
        hashed_password=hashed_password,
        is_admin=user_data.is_admin,
    )
    
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    
    return UserResponse(
        id=db_user.id,
        username=db_user.username,
        email=db_user.email,
        is_active=db_user.is_active,
        is_admin=db_user.is_admin,
        created_at=db_user.created_at,
        last_login=db_user.last_login,
    )


@router.get("/users", response_model=List[UserResponse])
async def list_users(
    current_user: TokenData = Depends(require_admin),
    db: Session = Depends(get_db),
) -> List[UserResponse]:
    """List all users."""
    users = db.query(User).all()
    return [
        UserResponse(
            id=user.id,
            username=user.username,
            email=user.email,
            is_active=user.is_active,
            is_admin=user.is_admin,
            created_at=user.created_at,
            last_login=user.last_login,
        )
        for user in users
    ]


@router.get("/users/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: int,
    current_user: TokenData = Depends(require_admin),
    db: Session = Depends(get_db),
) -> UserResponse:
    """Get a specific user."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    return UserResponse(
        id=user.id,
        username=user.username,
        email=user.email,
        is_active=user.is_active,
        is_admin=user.is_admin,
        created_at=user.created_at,
        last_login=user.last_login,
    )


@router.delete("/users/{user_id}")
async def delete_user(
    user_id: int,
    current_user: TokenData = Depends(require_admin),
    db: Session = Depends(get_db),
) -> dict:
    """Delete a user."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Prevent self-deletion
    if user.username == current_user.username:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete your own account"
        )
    
    db.delete(user)
    db.commit()
    
    return {"message": "User deleted successfully"}


@router.post("/users/{user_id}/toggle")
async def toggle_user(
    user_id: int,
    current_user: TokenData = Depends(require_admin),
    db: Session = Depends(get_db),
) -> UserResponse:
    """Toggle user active status."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Prevent self-deactivation
    if user.username == current_user.username:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot deactivate your own account"
        )
    
    user.is_active = not user.is_active
    db.commit()
    db.refresh(user)
    
    return UserResponse(
        id=user.id,
        username=user.username,
        email=user.email,
        is_active=user.is_active,
        is_admin=user.is_admin,
        created_at=user.created_at,
        last_login=user.last_login,
    )