"""Authentication routes"""
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session

from database.connection import get_db
from database.models import User, PlayerStats, AuditLog
from database.schemas import (
    UserCreate, UserUpdate, UserResponse, Token, LoginRequest, PasswordChange
)
from .utils import verify_password, get_password_hash, create_access_token
from .dependencies import get_current_active_user

router = APIRouter(prefix="/api/auth", tags=["Authentication"])


def log_action(
    db: Session,
    user_id: Optional[int],
    action: str,
    resource_type: Optional[str] = None,
    resource_id: Optional[str] = None,
    details: Optional[dict] = None,
    request: Optional[Request] = None
):
    """Helper to log audit actions"""
    ip_address = None
    user_agent = None

    if request:
        ip_address = request.client.host if request.client else None
        user_agent = request.headers.get("user-agent", "")[:255]

    audit_log = AuditLog(
        user_id=user_id,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        details=details,
        ip_address=ip_address,
        user_agent=user_agent
    )
    db.add(audit_log)
    db.commit()


@router.post("/register", response_model=Token, status_code=status.HTTP_201_CREATED)
async def register(
    user_data: UserCreate,
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Register a new user account

    - Creates user with hashed password
    - Automatically creates player stats record
    - Returns JWT token for immediate login
    """
    # Check if username exists
    existing_user = db.query(User).filter(User.username == user_data.username).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already registered"
        )

    # Check if email exists
    existing_email = db.query(User).filter(User.email == user_data.email).first()
    if existing_email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )

    # Create user
    hashed_password = get_password_hash(user_data.password)
    user = User(
        username=user_data.username,
        email=user_data.email,
        hashed_password=hashed_password,
        last_login=datetime.utcnow()
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    # Create player stats record
    stats = PlayerStats(user_id=user.id)
    db.add(stats)
    db.commit()

    # Log registration
    log_action(db, user.id, "register", "user", str(user.id), request=request)

    # Create access token
    access_token = create_access_token(
        data={"sub": str(user.id), "username": user.username, "role": user.role}
    )

    return Token(
        access_token=access_token,
        user=UserResponse.model_validate(user)
    )


@router.post("/login", response_model=Token)
async def login(
    login_data: LoginRequest,
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Login with username and password

    - Validates credentials
    - Updates last_login timestamp
    - Returns JWT token
    """
    # Find user by username
    user = db.query(User).filter(User.username == login_data.username).first()

    if not user or not verify_password(login_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is disabled"
        )

    # Update last login
    user.last_login = datetime.utcnow()
    db.commit()

    # Log login
    log_action(db, user.id, "login", "user", str(user.id), request=request)

    # Create access token
    access_token = create_access_token(
        data={"sub": str(user.id), "username": user.username, "role": user.role}
    )

    return Token(
        access_token=access_token,
        user=UserResponse.model_validate(user)
    )


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: User = Depends(get_current_active_user)
):
    """Get current authenticated user's information"""
    return UserResponse.model_validate(current_user)


@router.put("/me", response_model=UserResponse)
async def update_current_user(
    user_update: UserUpdate,
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Update current user's profile (username/email)"""
    update_data = user_update.model_dump(exclude_unset=True)

    # Check username uniqueness
    if "username" in update_data:
        existing = db.query(User).filter(
            User.username == update_data["username"],
            User.id != current_user.id
        ).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username already taken"
            )

    # Check email uniqueness
    if "email" in update_data:
        existing = db.query(User).filter(
            User.email == update_data["email"],
            User.id != current_user.id
        ).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already taken"
            )

    # Update fields
    for field, value in update_data.items():
        setattr(current_user, field, value)

    current_user.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(current_user)

    # Log update
    log_action(
        db, current_user.id, "update_profile", "user",
        str(current_user.id), update_data, request
    )

    return UserResponse.model_validate(current_user)


@router.post("/change-password")
async def change_password(
    password_data: PasswordChange,
    request: Request,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Change current user's password"""
    # Verify old password
    if not verify_password(password_data.old_password, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Incorrect current password"
        )

    # Update password
    current_user.hashed_password = get_password_hash(password_data.new_password)
    current_user.updated_at = datetime.utcnow()
    db.commit()

    # Log password change
    log_action(
        db, current_user.id, "change_password", "user",
        str(current_user.id), request=request
    )

    return {"message": "Password changed successfully"}


@router.get("/me/stats")
async def get_current_user_stats(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get current user's game statistics"""
    stats = db.query(PlayerStats).filter(PlayerStats.user_id == current_user.id).first()

    if not stats:
        # Create stats if not exists
        stats = PlayerStats(user_id=current_user.id)
        db.add(stats)
        db.commit()
        db.refresh(stats)

    return {
        "user": UserResponse.model_validate(current_user),
        "stats": {
            "total_games": stats.total_games,
            "total_hands": stats.total_hands,
            "wins": stats.wins,
            "losses": stats.losses,
            "win_rate": stats.win_rate,
            "total_chips_won": stats.total_chips_won,
            "total_chips_lost": stats.total_chips_lost,
            "biggest_pot_won": stats.biggest_pot_won,
            "vpip": stats.vpip,
            "pfr": stats.pfr,
            "aggression_factor": stats.aggression_factor
        }
    }
