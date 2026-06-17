"""Database connection configuration"""
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from pathlib import Path

# Database file path - in backend directory
DATABASE_DIR = Path(__file__).parent.parent
DATABASE_URL = os.getenv("SQLITE_DATABASE_URL", f"sqlite:///{DATABASE_DIR}/poker.db")

# Create engine
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},  # Needed for SQLite
    echo=False  # Set to True for SQL debugging
)

# Session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    """Dependency for getting database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Initialize database tables"""
    from .models import Base
    Base.metadata.create_all(bind=engine)
    print(f"Database initialized at: {DATABASE_URL}")
