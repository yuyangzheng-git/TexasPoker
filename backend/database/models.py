"""SQLAlchemy database models"""
from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, Float, Boolean, DateTime, Text,
    ForeignKey, JSON, Enum as SQLEnum
)
from sqlalchemy.orm import relationship, declarative_base
import enum

Base = declarative_base()


class UserRole(str, enum.Enum):
    """User role enumeration"""
    USER = "user"
    ADMIN = "admin"
    SUPER_ADMIN = "super_admin"


class User(Base):
    """User account model"""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    email = Column(String(100), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    role = Column(String(20), default=UserRole.USER.value, nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_login = Column(DateTime, nullable=True)

    # Relationships
    stats = relationship("PlayerStats", back_populates="user", uselist=False, cascade="all, delete-orphan")
    game_sessions = relationship("GameSession", back_populates="user", cascade="all, delete-orphan")
    audit_logs = relationship("AuditLog", back_populates="user", cascade="all, delete-orphan")


class PlayerStats(Base):
    """Player statistics model"""
    __tablename__ = "player_stats"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False)
    total_games = Column(Integer, default=0)
    total_hands = Column(Integer, default=0)
    wins = Column(Integer, default=0)
    losses = Column(Integer, default=0)
    win_rate = Column(Float, default=0.0)
    total_chips_won = Column(Integer, default=0)
    total_chips_lost = Column(Integer, default=0)
    biggest_pot_won = Column(Integer, default=0)
    vpip = Column(Float, default=0.0)  # Voluntarily Put In Pot %
    pfr = Column(Float, default=0.0)   # Pre-Flop Raise %
    aggression_factor = Column(Float, default=0.0)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationship
    user = relationship("User", back_populates="stats")


class GameSession(Base):
    """Game session record model"""
    __tablename__ = "game_sessions"

    id = Column(Integer, primary_key=True, index=True)
    game_id = Column(String(50), unique=True, index=True, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=True)  # Nullable for guest games
    started_at = Column(DateTime, default=datetime.utcnow)
    ended_at = Column(DateTime, nullable=True)
    total_hands = Column(Integer, default=0)
    starting_stack = Column(Integer, default=10000)
    ending_stack = Column(Integer, nullable=True)
    result = Column(String(20), nullable=True)  # win, loss, draw
    ai_opponents = Column(JSON, default=list)  # List of AI agent IDs
    small_blind = Column(Integer, default=50)
    big_blind = Column(Integer, default=100)

    # Relationships
    user = relationship("User", back_populates="game_sessions")
    hand_records = relationship("HandRecord", back_populates="session", cascade="all, delete-orphan")


class HandRecord(Base):
    """Individual hand record model"""
    __tablename__ = "hand_records"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("game_sessions.id", ondelete="CASCADE"), nullable=False)
    hand_number = Column(Integer, nullable=False)
    player_cards = Column(JSON, nullable=True)  # [{"rank": 14, "suit": 0}, ...]
    community_cards = Column(JSON, nullable=True)
    pot_size = Column(Integer, default=0)
    player_result = Column(String(20), nullable=True)  # won, lost, folded
    chips_change = Column(Integer, default=0)
    final_hand_rank = Column(String(50), nullable=True)  # e.g., "FULL_HOUSE"
    actions = Column(JSON, default=list)  # List of player actions
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationship
    session = relationship("GameSession", back_populates="hand_records")


class AIAgentConfig(Base):
    """AI Agent configuration model"""
    __tablename__ = "ai_agent_configs"

    id = Column(Integer, primary_key=True, index=True)
    agent_id = Column(String(50), unique=True, index=True, nullable=False)
    name = Column(String(50), nullable=False)
    style = Column(String(50), nullable=True)
    persona = Column(Text, nullable=True)
    speech_style = Column(Text, nullable=True)
    temperature = Column(Float, default=0.7)
    vpip_target = Column(Float, default=0.25)
    pfr_target = Column(Float, default=0.15)
    risk_profile = Column(String(50), nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class SystemConfig(Base):
    """System configuration model"""
    __tablename__ = "system_configs"

    id = Column(Integer, primary_key=True, index=True)
    key = Column(String(100), unique=True, index=True, nullable=False)
    value = Column(Text, nullable=True)
    value_type = Column(String(20), default="string")  # string, int, float, bool, json
    description = Column(Text, nullable=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    updated_by = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)


class AuditLog(Base):
    """Audit log model for tracking sensitive operations"""
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    action = Column(String(100), nullable=False)  # login, logout, update_user, delete_user, etc.
    resource_type = Column(String(50), nullable=True)  # user, game, ai_agent, system_config
    resource_id = Column(String(50), nullable=True)
    details = Column(JSON, nullable=True)  # Additional context
    ip_address = Column(String(50), nullable=True)
    user_agent = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)

    # Relationship
    user = relationship("User", back_populates="audit_logs")
