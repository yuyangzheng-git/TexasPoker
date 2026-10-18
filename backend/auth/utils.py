"""Authentication utilities - password hashing and JWT tokens"""
import hashlib
import hmac
import secrets
import bcrypt
from datetime import datetime, timedelta, timezone
from typing import Optional
from settings import JWT_SECRET_KEY
from jose import JWTError, jwt

# Security configuration
SECRET_KEY = JWT_SECRET_KEY
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_HOURS = 24

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify scrypt passwords and existing bcrypt records without passlib."""
    try:
        if hashed_password.startswith("scrypt$"):
            _, salt_hex, digest_hex = hashed_password.split("$")
            digest = hashlib.scrypt(plain_password.encode(), salt=bytes.fromhex(salt_hex),
                n=16384, r=8, p=1, dklen=32)
            return hmac.compare_digest(digest, bytes.fromhex(digest_hex))
        if hashed_password.startswith(("$2a$", "$2b$", "$2y$")):
            # Legacy bcrypt records were limited to their first 72 bytes.
            return bcrypt.checkpw(plain_password.encode()[:72], hashed_password.encode())
    except (ValueError, TypeError):
        pass
    return False


def get_password_hash(password: str) -> str:
    """New records use scrypt, including long Unicode passwords without truncation."""
    salt = secrets.token_bytes(16)
    digest = hashlib.scrypt(password.encode(), salt=salt, n=16384, r=8, p=1, dklen=32)
    return f"scrypt${salt.hex()}${digest.hex()}"


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    Create a JWT access token

    Args:
        data: Payload data to encode in the token
        expires_delta: Optional custom expiration time

    Returns:
        Encoded JWT token string
    """
    to_encode = data.copy()

    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(hours=ACCESS_TOKEN_EXPIRE_HOURS)

    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

    return encoded_jwt


def verify_token(token: str) -> Optional[dict]:
    """
    Verify and decode a JWT token

    Args:
        token: JWT token string

    Returns:
        Decoded payload dict if valid, None otherwise
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        return None
