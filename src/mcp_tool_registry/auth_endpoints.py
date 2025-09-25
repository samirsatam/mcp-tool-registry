"""Authentication endpoints for login and token management."""

from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from .auth import (
    APIKey,
    Token,
    TokenData,
    User,
    authenticate_api_key,
    create_access_token,
    create_refresh_token,
    get_current_user,
    get_password_hash,
    verify_password,
)
from .database import get_db

router = APIRouter(prefix="/auth", tags=["authentication"])


@router.post("/login", response_model=Token)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
) -> Token:
    """Authenticate user and return tokens."""
    # Authenticate user
    user = db.query(User).filter(User.username == form_data.username).first()
    
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account is disabled",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Update last login
    user.last_login = datetime.utcnow()
    db.commit()
    
    # Create tokens
    access_token_expires = timedelta(minutes=30)
    access_token = create_access_token(
        data={"sub": user.username, "is_admin": user.is_admin},
        expires_delta=access_token_expires
    )
    refresh_token = create_refresh_token(
        data={"sub": user.username, "is_admin": user.is_admin}
    )
    
    return Token(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        expires_in=1800  # 30 minutes
    )


@router.post("/api-key-login", response_model=Token)
async def api_key_login(
    api_key: str,
    db: Session = Depends(get_db),
) -> Token:
    """Authenticate using API key and return tokens."""
    # Authenticate API key
    api_key_obj = authenticate_api_key(api_key, db)
    
    if not api_key_obj:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not api_key_obj.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key is disabled",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Check if API key is expired
    if api_key_obj.expires_at and api_key_obj.expires_at < datetime.utcnow():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key expired",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Update last used
    api_key_obj.last_used = datetime.utcnow()
    db.commit()
    
    # Create tokens
    access_token_expires = timedelta(minutes=30)
    access_token = create_access_token(
        data={"api_key": api_key_obj.name, "is_admin": False},
        expires_delta=access_token_expires
    )
    refresh_token = create_refresh_token(
        data={"api_key": api_key_obj.name, "is_admin": False}
    )
    
    return Token(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        expires_in=1800  # 30 minutes
    )


@router.post("/refresh", response_model=Token)
async def refresh_token(
    refresh_token: str,
    db: Session = Depends(get_db),
) -> Token:
    """Refresh access token using refresh token."""
    try:
        from jose import jwt
        from .auth import SECRET_KEY, ALGORITHM
        
        # Decode refresh token
        payload = jwt.decode(refresh_token, SECRET_KEY, algorithms=[ALGORITHM])
        
        # Check if it's a refresh token
        if payload.get("type") != "refresh":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token type",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        username = payload.get("sub")
        api_key_name = payload.get("api_key")
        is_admin = payload.get("is_admin", False)
        
        # Verify user/API key still exists and is active
        if username:
            user = db.query(User).filter(User.username == username).first()
            if not user or not user.is_active:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="User not found or inactive",
                    headers={"WWW-Authenticate": "Bearer"},
                )
        elif api_key_name:
            api_key = db.query(APIKey).filter(
                APIKey.name == api_key_name,
                APIKey.is_active == True
            ).first()
            if not api_key:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="API key not found or inactive",
                    headers={"WWW-Authenticate": "Bearer"},
                )
            if api_key.expires_at and api_key.expires_at < datetime.utcnow():
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="API key expired",
                    headers={"WWW-Authenticate": "Bearer"},
                )
        else:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # Create new access token
        access_token_expires = timedelta(minutes=30)
        access_token = create_access_token(
            data={
                "sub": username,
                "api_key": api_key_name,
                "is_admin": is_admin
            },
            expires_delta=access_token_expires
        )
        
        # Create new refresh token
        new_refresh_token = create_refresh_token(
            data={
                "sub": username,
                "api_key": api_key_name,
                "is_admin": is_admin
            }
        )
        
        return Token(
            access_token=access_token,
            refresh_token=new_refresh_token,
            token_type="bearer",
            expires_in=1800  # 30 minutes
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
            headers={"WWW-Authenticate": "Bearer"},
        )


@router.get("/me")
async def get_current_user_info(
    current_user: TokenData = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    """Get current user information."""
    if current_user.username:
        # User authentication
        user = db.query(User).filter(User.username == current_user.username).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        return {
            "type": "user",
            "username": user.username,
            "email": user.email,
            "is_admin": user.is_admin,
            "is_active": user.is_active,
            "created_at": user.created_at,
            "last_login": user.last_login,
        }
    elif current_user.api_key_name:
        # API key authentication
        api_key = db.query(APIKey).filter(APIKey.name == current_user.api_key_name).first()
        if not api_key:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="API key not found"
            )
        
        return {
            "type": "api_key",
            "name": api_key.name,
            "description": api_key.description,
            "is_active": api_key.is_active,
            "created_at": api_key.created_at,
            "last_used": api_key.last_used,
            "expires_at": api_key.expires_at,
            "permissions": {
                "can_create": api_key.can_create,
                "can_read": api_key.can_read,
                "can_update": api_key.can_update,
                "can_delete": api_key.can_delete,
            }
        }
    else:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication"
        )


@router.post("/logout")
async def logout(
    current_user: TokenData = Depends(get_current_user),
) -> dict:
    """Logout user (client should discard tokens)."""
    # In a more sophisticated system, you might blacklist the token
    # For now, we just return a success message
    return {"message": "Logged out successfully"}