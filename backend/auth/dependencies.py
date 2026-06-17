"""Authentication dependencies for FastAPI dependency injection"""
from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from database.connection import get_db
from database.models import User, UserRole
from .utils import verify_token

# HTTP Bearer token security scheme
security = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: Session = Depends(get_db)
) -> Optional[User]:
    """
    Get current user from JWT token (optional - returns None if not authenticated)

    Args:
        credentials: Bearer token from Authorization header
        db: Database session

    Returns:
        User object if authenticated, None otherwise
    """
    if credentials is None:
        return None

    token = credentials.credentials
    payload = verify_token(token)

    if payload is None:
        return None

    user_id = payload.get("sub")
    if user_id is None:
        return None

    try:
        user_id = int(user_id)
    except (ValueError, TypeError):
        return None

    user = db.query(User).filter(User.id == user_id).first()
    return user


async def get_current_active_user(
    credentials: HTTPAuthorizationCredentials = Depends(HTTPBearer()),
    db: Session = Depends(get_db)
) -> User:
    """
    Get current active user - requires valid authentication

    Args:
        credentials: Bearer token from Authorization header
        db: Database session

    Returns:
        User object if authenticated and active

    Raises:
        HTTPException: If not authenticated or user is inactive
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    token = credentials.credentials
    payload = verify_token(token)

    if payload is None:
        raise credentials_exception

    user_id = payload.get("sub")
    if user_id is None:
        raise credentials_exception

    try:
        user_id = int(user_id)
    except (ValueError, TypeError):
        raise credentials_exception

    user = db.query(User).filter(User.id == user_id).first()

    if user is None:
        raise credentials_exception

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is disabled"
        )

    return user


async def get_admin_user(
    current_user: User = Depends(get_current_active_user)
) -> User:
    """
    Get current user with admin or super_admin role

    Args:
        current_user: Current authenticated user

    Returns:
        User object if user has admin privileges

    Raises:
        HTTPException: If user is not an admin
    """
    if current_user.role not in [UserRole.ADMIN.value, UserRole.SUPER_ADMIN.value]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Administrator privileges required"
        )
    return current_user


async def get_super_admin_user(
    current_user: User = Depends(get_current_active_user)
) -> User:
    """
    Get current user with super_admin role only

    Args:
        current_user: Current authenticated user

    Returns:
        User object if user has super admin privileges

    Raises:
        HTTPException: If user is not a super admin
    """
    if current_user.role != UserRole.SUPER_ADMIN.value:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Super administrator privileges required"
        )
    return current_user
