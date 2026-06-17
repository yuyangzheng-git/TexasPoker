"""Pydantic schemas for request/response validation"""
from datetime import datetime
from typing import Optional, List, Any
from pydantic import BaseModel, EmailStr, Field, field_validator
import re


# ============== User Schemas ==============

class UserCreate(BaseModel):
    """Schema for user registration"""
    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr
    password: str = Field(..., min_length=6, max_length=100)

    @field_validator('username')
    @classmethod
    def username_alphanumeric(cls, v: str) -> str:
        if not re.match(r'^[a-zA-Z0-9_\u4e00-\u9fff]+$', v):
            raise ValueError('Username must be alphanumeric (letters, numbers, underscores, or Chinese characters)')
        return v


class UserUpdate(BaseModel):
    """Schema for updating user profile"""
    username: Optional[str] = Field(None, min_length=3, max_length=50)
    email: Optional[EmailStr] = None

    @field_validator('username')
    @classmethod
    def username_alphanumeric(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and not re.match(r'^[a-zA-Z0-9_\u4e00-\u9fff]+$', v):
            raise ValueError('Username must be alphanumeric')
        return v


class UserAdminUpdate(BaseModel):
    """Schema for admin updating user"""
    role: Optional[str] = None
    is_active: Optional[bool] = None


class PasswordChange(BaseModel):
    """Schema for password change"""
    old_password: str
    new_password: str = Field(..., min_length=6, max_length=100)


class UserResponse(BaseModel):
    """Schema for user response (public data)"""
    id: int
    username: str
    email: str
    role: str
    is_active: bool
    created_at: datetime
    last_login: Optional[datetime] = None

    class Config:
        from_attributes = True


class UserInDB(UserResponse):
    """Schema for user with hashed password (internal use)"""
    hashed_password: str


class UserWithStats(UserResponse):
    """Schema for user with statistics"""
    stats: Optional["PlayerStatsResponse"] = None


# ============== Auth Schemas ==============

class Token(BaseModel):
    """JWT token response"""
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


class TokenData(BaseModel):
    """Token payload data"""
    user_id: Optional[int] = None
    username: Optional[str] = None
    role: Optional[str] = None


class LoginRequest(BaseModel):
    """Login request schema"""
    username: str
    password: str


# ============== Player Stats Schemas ==============

class PlayerStatsResponse(BaseModel):
    """Player statistics response"""
    id: int
    user_id: int
    total_games: int
    total_hands: int
    wins: int
    losses: int
    win_rate: float
    total_chips_won: int
    total_chips_lost: int
    biggest_pot_won: int
    vpip: float
    pfr: float
    aggression_factor: float
    updated_at: datetime

    class Config:
        from_attributes = True


# ============== Game Session Schemas ==============

class GameSessionResponse(BaseModel):
    """Game session response"""
    id: int
    game_id: str
    user_id: Optional[int]
    started_at: datetime
    ended_at: Optional[datetime]
    total_hands: int
    starting_stack: int
    ending_stack: Optional[int]
    result: Optional[str]
    ai_opponents: List[str]
    small_blind: int
    big_blind: int

    class Config:
        from_attributes = True


class GameSessionCreate(BaseModel):
    """Create game session schema"""
    game_id: str
    ai_opponents: List[str] = []
    starting_stack: int = 10000
    small_blind: int = 50
    big_blind: int = 100


class GameSessionUpdate(BaseModel):
    """Update game session schema"""
    ended_at: Optional[datetime] = None
    total_hands: Optional[int] = None
    ending_stack: Optional[int] = None
    result: Optional[str] = None


# ============== Hand Record Schemas ==============

class HandRecordResponse(BaseModel):
    """Hand record response"""
    id: int
    session_id: int
    hand_number: int
    player_cards: Optional[List[dict]]
    community_cards: Optional[List[dict]]
    pot_size: int
    player_result: Optional[str]
    chips_change: int
    final_hand_rank: Optional[str]
    actions: List[dict]
    created_at: datetime

    class Config:
        from_attributes = True


class HandRecordCreate(BaseModel):
    """Create hand record schema"""
    session_id: int
    hand_number: int
    player_cards: Optional[List[dict]] = None
    community_cards: Optional[List[dict]] = None
    pot_size: int = 0
    player_result: Optional[str] = None
    chips_change: int = 0
    final_hand_rank: Optional[str] = None
    actions: List[dict] = []


# ============== AI Agent Config Schemas ==============

class AIAgentConfigCreate(BaseModel):
    """Create AI agent config schema"""
    agent_id: str = Field(..., min_length=2, max_length=50)
    name: str = Field(..., min_length=1, max_length=50)
    style: Optional[str] = None
    persona: Optional[str] = None
    speech_style: Optional[str] = None
    temperature: float = Field(0.7, ge=0.0, le=2.0)
    vpip_target: float = Field(0.25, ge=0.0, le=1.0)
    pfr_target: float = Field(0.15, ge=0.0, le=1.0)
    risk_profile: Optional[str] = None
    is_active: bool = True


class AIAgentConfigUpdate(BaseModel):
    """Update AI agent config schema"""
    name: Optional[str] = Field(None, min_length=1, max_length=50)
    style: Optional[str] = None
    persona: Optional[str] = None
    speech_style: Optional[str] = None
    temperature: Optional[float] = Field(None, ge=0.0, le=2.0)
    vpip_target: Optional[float] = Field(None, ge=0.0, le=1.0)
    pfr_target: Optional[float] = Field(None, ge=0.0, le=1.0)
    risk_profile: Optional[str] = None
    is_active: Optional[bool] = None


class AIAgentConfigResponse(BaseModel):
    """AI agent config response"""
    id: int
    agent_id: str
    name: str
    style: Optional[str]
    persona: Optional[str]
    speech_style: Optional[str]
    temperature: float
    vpip_target: float
    pfr_target: float
    risk_profile: Optional[str]
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ============== System Config Schemas ==============

class SystemConfigUpdate(BaseModel):
    """Update system config schema"""
    value: str
    value_type: Optional[str] = None
    description: Optional[str] = None


class SystemConfigResponse(BaseModel):
    """System config response"""
    id: int
    key: str
    value: Optional[str]
    value_type: str
    description: Optional[str]
    updated_at: datetime
    updated_by: Optional[int]

    class Config:
        from_attributes = True


class SystemConfigCreate(BaseModel):
    """Create system config schema"""
    key: str = Field(..., min_length=1, max_length=100)
    value: Optional[str] = None
    value_type: str = "string"
    description: Optional[str] = None


# ============== Audit Log Schemas ==============

class AuditLogResponse(BaseModel):
    """Audit log response"""
    id: int
    user_id: Optional[int]
    action: str
    resource_type: Optional[str]
    resource_id: Optional[str]
    details: Optional[dict]
    ip_address: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


# ============== Statistics Schemas ==============

class OverviewStats(BaseModel):
    """Overview statistics for admin dashboard"""
    total_users: int
    active_users: int
    total_games: int
    games_today: int
    total_hands_played: int
    active_ai_agents: int


class DailyGameStats(BaseModel):
    """Daily game statistics"""
    date: str
    games_count: int
    hands_count: int
    unique_players: int


class LeaderboardEntry(BaseModel):
    """Leaderboard entry"""
    rank: int
    user_id: int
    username: str
    total_chips_won: int
    win_rate: float
    total_games: int


class SystemStatus(BaseModel):
    """System status for monitoring"""
    cpu_percent: float
    memory_percent: float
    disk_percent: float
    active_games: int
    active_connections: int
    uptime_seconds: float


# Update forward references
UserWithStats.model_rebuild()
