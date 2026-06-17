"""Admin management routes"""
import os
import time
from datetime import datetime, timedelta
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, status, Query, Request
from sqlalchemy.orm import Session
from sqlalchemy import func, desc

from database.connection import get_db
from database.models import (
    User, PlayerStats, GameSession, HandRecord,
    AIAgentConfig, SystemConfig, AuditLog, UserRole
)
from database.schemas import (
    UserResponse, UserAdminUpdate, PlayerStatsResponse,
    GameSessionResponse, AIAgentConfigCreate, AIAgentConfigUpdate,
    AIAgentConfigResponse, SystemConfigCreate, SystemConfigUpdate,
    SystemConfigResponse, AuditLogResponse,
    OverviewStats, DailyGameStats, LeaderboardEntry, SystemStatus
)
from auth.dependencies import get_admin_user, get_super_admin_user

router = APIRouter(prefix="/api/admin", tags=["Admin"])

# Server start time for uptime calculation
SERVER_START_TIME = time.time()


def log_admin_action(
    db: Session,
    user_id: int,
    action: str,
    resource_type: str,
    resource_id: Optional[str] = None,
    details: Optional[dict] = None,
    request: Optional[Request] = None
):
    """Log admin action to audit log"""
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


# ============== User Management ==============

@router.get("/users", response_model=dict)
async def list_users(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: Optional[str] = None,
    role: Optional[str] = None,
    is_active: Optional[bool] = None,
    admin_user: User = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    """List all users with pagination and filters"""
    query = db.query(User)

    # Apply filters
    if search:
        search_filter = f"%{search}%"
        query = query.filter(
            (User.username.ilike(search_filter)) |
            (User.email.ilike(search_filter))
        )

    if role:
        query = query.filter(User.role == role)

    if is_active is not None:
        query = query.filter(User.is_active == is_active)

    # Get total count
    total = query.count()

    # Apply pagination
    users = query.order_by(desc(User.created_at)).offset(
        (page - 1) * page_size
    ).limit(page_size).all()

    return {
        "users": [UserResponse.model_validate(u) for u in users],
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": (total + page_size - 1) // page_size
    }


@router.get("/users/{user_id}", response_model=dict)
async def get_user_detail(
    user_id: int,
    admin_user: User = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    """Get detailed user information including stats"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    stats = db.query(PlayerStats).filter(PlayerStats.user_id == user_id).first()
    recent_games = db.query(GameSession).filter(
        GameSession.user_id == user_id
    ).order_by(desc(GameSession.started_at)).limit(10).all()

    return {
        "user": UserResponse.model_validate(user),
        "stats": PlayerStatsResponse.model_validate(stats) if stats else None,
        "recent_games": [GameSessionResponse.model_validate(g) for g in recent_games]
    }


@router.put("/users/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: int,
    user_update: UserAdminUpdate,
    request: Request,
    admin_user: User = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    """Update user (role, is_active) - Admin only"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Prevent non-super-admin from modifying super_admin users
    if user.role == UserRole.SUPER_ADMIN.value and admin_user.role != UserRole.SUPER_ADMIN.value:
        raise HTTPException(
            status_code=403,
            detail="Cannot modify super admin user"
        )

    # Prevent non-super-admin from granting super_admin role
    if user_update.role == UserRole.SUPER_ADMIN.value and admin_user.role != UserRole.SUPER_ADMIN.value:
        raise HTTPException(
            status_code=403,
            detail="Only super admin can grant super admin role"
        )

    update_data = user_update.model_dump(exclude_unset=True)

    for field, value in update_data.items():
        setattr(user, field, value)

    user.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(user)

    # Log action
    log_admin_action(
        db, admin_user.id, "update_user", "user",
        str(user_id), update_data, request
    )

    return UserResponse.model_validate(user)


# ============== Statistics ==============

@router.get("/stats/overview", response_model=OverviewStats)
async def get_overview_stats(
    admin_user: User = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    """Get overview statistics for dashboard"""
    today = datetime.utcnow().date()
    today_start = datetime.combine(today, datetime.min.time())

    total_users = db.query(User).count()
    active_users = db.query(User).filter(User.is_active == True).count()
    total_games = db.query(GameSession).count()
    games_today = db.query(GameSession).filter(
        GameSession.started_at >= today_start
    ).count()
    total_hands = db.query(func.sum(GameSession.total_hands)).scalar() or 0
    active_ai_agents = db.query(AIAgentConfig).filter(
        AIAgentConfig.is_active == True
    ).count()

    return OverviewStats(
        total_users=total_users,
        active_users=active_users,
        total_games=total_games,
        games_today=games_today,
        total_hands_played=total_hands,
        active_ai_agents=active_ai_agents
    )


@router.get("/stats/games", response_model=List[DailyGameStats])
async def get_daily_game_stats(
    days: int = Query(30, ge=1, le=365),
    admin_user: User = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    """Get daily game statistics for the last N days"""
    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=days)

    # Query daily stats
    results = db.query(
        func.date(GameSession.started_at).label('date'),
        func.count(GameSession.id).label('games_count'),
        func.sum(GameSession.total_hands).label('hands_count'),
        func.count(func.distinct(GameSession.user_id)).label('unique_players')
    ).filter(
        GameSession.started_at >= start_date
    ).group_by(
        func.date(GameSession.started_at)
    ).order_by(
        func.date(GameSession.started_at)
    ).all()

    return [
        DailyGameStats(
            date=str(r.date),
            games_count=r.games_count,
            hands_count=r.hands_count or 0,
            unique_players=r.unique_players or 0
        )
        for r in results
    ]


@router.get("/stats/leaderboard", response_model=List[LeaderboardEntry])
async def get_leaderboard(
    limit: int = Query(20, ge=1, le=100),
    admin_user: User = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    """Get player leaderboard by total chips won"""
    results = db.query(
        PlayerStats, User
    ).join(
        User, PlayerStats.user_id == User.id
    ).filter(
        User.is_active == True,
        PlayerStats.total_games > 0
    ).order_by(
        desc(PlayerStats.total_chips_won)
    ).limit(limit).all()

    return [
        LeaderboardEntry(
            rank=idx + 1,
            user_id=stats.user_id,
            username=user.username,
            total_chips_won=stats.total_chips_won,
            win_rate=stats.win_rate,
            total_games=stats.total_games
        )
        for idx, (stats, user) in enumerate(results)
    ]


# ============== Game Sessions ==============

@router.get("/games", response_model=dict)
async def list_game_sessions(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    user_id: Optional[int] = None,
    result: Optional[str] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    admin_user: User = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    """List game sessions with filters"""
    query = db.query(GameSession)

    if user_id:
        query = query.filter(GameSession.user_id == user_id)

    if result:
        query = query.filter(GameSession.result == result)

    if start_date:
        query = query.filter(GameSession.started_at >= start_date)

    if end_date:
        query = query.filter(GameSession.started_at <= end_date)

    total = query.count()

    games = query.order_by(desc(GameSession.started_at)).offset(
        (page - 1) * page_size
    ).limit(page_size).all()

    return {
        "games": [GameSessionResponse.model_validate(g) for g in games],
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": (total + page_size - 1) // page_size
    }


@router.get("/games/{game_id}")
async def get_game_detail(
    game_id: str,
    admin_user: User = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    """Get detailed game session with hand records"""
    game = db.query(GameSession).filter(GameSession.game_id == game_id).first()
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")

    hands = db.query(HandRecord).filter(
        HandRecord.session_id == game.id
    ).order_by(HandRecord.hand_number).all()

    user = None
    if game.user_id:
        user = db.query(User).filter(User.id == game.user_id).first()

    return {
        "game": GameSessionResponse.model_validate(game),
        "hands": [
            {
                "hand_number": h.hand_number,
                "pot_size": h.pot_size,
                "player_result": h.player_result,
                "chips_change": h.chips_change,
                "final_hand_rank": h.final_hand_rank
            }
            for h in hands
        ],
        "user": UserResponse.model_validate(user) if user else None
    }


# ============== AI Agent Configuration ==============

@router.get("/ai-agents", response_model=List[AIAgentConfigResponse])
async def list_ai_agents(
    include_inactive: bool = False,
    admin_user: User = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    """List all AI agent configurations"""
    query = db.query(AIAgentConfig)

    if not include_inactive:
        query = query.filter(AIAgentConfig.is_active == True)

    agents = query.order_by(AIAgentConfig.name).all()
    return [AIAgentConfigResponse.model_validate(a) for a in agents]


@router.get("/ai-agents/{agent_id}", response_model=AIAgentConfigResponse)
async def get_ai_agent(
    agent_id: str,
    admin_user: User = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    """Get AI agent configuration by ID"""
    agent = db.query(AIAgentConfig).filter(AIAgentConfig.agent_id == agent_id).first()
    if not agent:
        raise HTTPException(status_code=404, detail="AI agent not found")

    return AIAgentConfigResponse.model_validate(agent)


@router.post("/ai-agents", response_model=AIAgentConfigResponse, status_code=201)
async def create_ai_agent(
    agent_data: AIAgentConfigCreate,
    request: Request,
    admin_user: User = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    """Create a new AI agent configuration"""
    existing = db.query(AIAgentConfig).filter(
        AIAgentConfig.agent_id == agent_data.agent_id
    ).first()
    if existing:
        raise HTTPException(
            status_code=400,
            detail="Agent ID already exists"
        )

    agent = AIAgentConfig(**agent_data.model_dump())
    db.add(agent)
    db.commit()
    db.refresh(agent)

    log_admin_action(
        db, admin_user.id, "create_ai_agent", "ai_agent",
        agent_data.agent_id, agent_data.model_dump(), request
    )

    return AIAgentConfigResponse.model_validate(agent)


@router.put("/ai-agents/{agent_id}", response_model=AIAgentConfigResponse)
async def update_ai_agent(
    agent_id: str,
    agent_update: AIAgentConfigUpdate,
    request: Request,
    admin_user: User = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    """Update AI agent configuration"""
    agent = db.query(AIAgentConfig).filter(AIAgentConfig.agent_id == agent_id).first()
    if not agent:
        raise HTTPException(status_code=404, detail="AI agent not found")

    update_data = agent_update.model_dump(exclude_unset=True)

    for field, value in update_data.items():
        setattr(agent, field, value)

    agent.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(agent)

    log_admin_action(
        db, admin_user.id, "update_ai_agent", "ai_agent",
        agent_id, update_data, request
    )

    return AIAgentConfigResponse.model_validate(agent)


# ============== System Configuration ==============

@router.get("/system-config", response_model=List[SystemConfigResponse])
async def list_system_configs(
    admin_user: User = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    """List all system configurations"""
    configs = db.query(SystemConfig).order_by(SystemConfig.key).all()
    return [SystemConfigResponse.model_validate(c) for c in configs]


@router.get("/system-config/{key}", response_model=SystemConfigResponse)
async def get_system_config(
    key: str,
    admin_user: User = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    """Get system configuration by key"""
    config = db.query(SystemConfig).filter(SystemConfig.key == key).first()
    if not config:
        raise HTTPException(status_code=404, detail="Configuration not found")

    return SystemConfigResponse.model_validate(config)


@router.post("/system-config", response_model=SystemConfigResponse, status_code=201)
async def create_system_config(
    config_data: SystemConfigCreate,
    request: Request,
    admin_user: User = Depends(get_super_admin_user),
    db: Session = Depends(get_db)
):
    """Create a new system configuration - Super Admin only"""
    existing = db.query(SystemConfig).filter(SystemConfig.key == config_data.key).first()
    if existing:
        raise HTTPException(status_code=400, detail="Configuration key already exists")

    config = SystemConfig(
        **config_data.model_dump(),
        updated_by=admin_user.id
    )
    db.add(config)
    db.commit()
    db.refresh(config)

    log_admin_action(
        db, admin_user.id, "create_system_config", "system_config",
        config_data.key, config_data.model_dump(), request
    )

    return SystemConfigResponse.model_validate(config)


@router.put("/system-config/{key}", response_model=SystemConfigResponse)
async def update_system_config(
    key: str,
    config_update: SystemConfigUpdate,
    request: Request,
    admin_user: User = Depends(get_super_admin_user),
    db: Session = Depends(get_db)
):
    """Update system configuration - Super Admin only"""
    config = db.query(SystemConfig).filter(SystemConfig.key == key).first()
    if not config:
        raise HTTPException(status_code=404, detail="Configuration not found")

    update_data = config_update.model_dump(exclude_unset=True)

    for field, value in update_data.items():
        setattr(config, field, value)

    config.updated_at = datetime.utcnow()
    config.updated_by = admin_user.id
    db.commit()
    db.refresh(config)

    log_admin_action(
        db, admin_user.id, "update_system_config", "system_config",
        key, update_data, request
    )

    return SystemConfigResponse.model_validate(config)


# ============== System Monitoring ==============

@router.get("/monitor/status", response_model=SystemStatus)
async def get_system_status(
    admin_user: User = Depends(get_admin_user)
):
    """Get current system status"""
    try:
        import psutil
        cpu_percent = psutil.cpu_percent(interval=0.1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
    except ImportError:
        # psutil not installed
        cpu_percent = 0.0
        memory = type('obj', (object,), {'percent': 0.0})()
        disk = type('obj', (object,), {'percent': 0.0})()

    # Import from main module to get active counts
    # These would need to be tracked in main.py
    active_games = 0
    active_connections = 0

    try:
        # Try to get from main module if available
        import sys
        if 'main' in sys.modules:
            main_module = sys.modules['main']
            active_games = len(getattr(main_module, 'active_games', {}))
            active_connections = len(getattr(main_module, 'connections', {}))
    except Exception:
        pass

    return SystemStatus(
        cpu_percent=cpu_percent,
        memory_percent=memory.percent,
        disk_percent=disk.percent,
        active_games=active_games,
        active_connections=active_connections,
        uptime_seconds=time.time() - SERVER_START_TIME
    )


@router.get("/monitor/audit-logs", response_model=dict)
async def list_audit_logs(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    user_id: Optional[int] = None,
    action: Optional[str] = None,
    resource_type: Optional[str] = None,
    start_date: Optional[datetime] = None,
    admin_user: User = Depends(get_admin_user),
    db: Session = Depends(get_db)
):
    """List audit logs with filters"""
    query = db.query(AuditLog)

    if user_id:
        query = query.filter(AuditLog.user_id == user_id)

    if action:
        query = query.filter(AuditLog.action == action)

    if resource_type:
        query = query.filter(AuditLog.resource_type == resource_type)

    if start_date:
        query = query.filter(AuditLog.created_at >= start_date)

    total = query.count()

    logs = query.order_by(desc(AuditLog.created_at)).offset(
        (page - 1) * page_size
    ).limit(page_size).all()

    return {
        "logs": [AuditLogResponse.model_validate(log) for log in logs],
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": (total + page_size - 1) // page_size
    }
