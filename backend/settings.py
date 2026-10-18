"""Load configuration before importing clients, authentication or database modules."""
import os
import secrets
import warnings
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / "config" / ".env")

POKER_AGENT_MODE = os.getenv("POKER_AGENT_MODE", "strategy").lower()
if POKER_AGENT_MODE not in {"strategy", "llm"}:
    raise RuntimeError("POKER_AGENT_MODE must be strategy or llm")

JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "")
if len(JWT_SECRET_KEY) < 32 or JWT_SECRET_KEY == "poker-llm-secret-key-change-in-production-2024":
    if os.getenv("APP_ENV", "development").lower() == "production":
        raise RuntimeError("Production requires a private JWT_SECRET_KEY of at least 32 characters")
    JWT_SECRET_KEY = secrets.token_urlsafe(48)
    warnings.warn("Using a temporary JWT secret; development logins expire on server restart", stacklevel=1)
