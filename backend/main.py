"""
FastAPI 主入口 + WebSocket 游戏服务器
"""
import settings  # Load config before auth/database/LLM imports.
import os
import json
import asyncio
import random
import secrets
import time
from pathlib import Path
from typing import Dict, List, Literal
from pydantic import BaseModel, Field
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

from game_engine import GameEngine, Player
from llm_agent import LLMAgent
from strategy_agent import StrategyAgent
from game_logger import GameLogger
from game_session import GameSession

# Import auth and admin modules
from database.connection import init_db
from auth import router as auth_router
from admin import router as admin_router
from auth.dependencies import get_admin_user

# 配置与日志目录（基于本文件位置，与运行目录无关）
BASE_DIR = Path(__file__).resolve().parent
CONFIG_DIR = BASE_DIR.parent / "config"
LOG_DIR = BASE_DIR.parent / "logs"

load_dotenv(CONFIG_DIR / ".env")

app = FastAPI(title="Poker LLM Agent API")

# Initialize database on startup
@app.on_event("startup")
async def startup_event():
    init_db()
    print("Database initialized successfully")

# Register auth and admin routers
app.include_router(auth_router)
app.include_router(admin_router)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in os.getenv("FRONTEND_URL", "http://localhost:3000").split(",")],
    allow_methods=["*"],
    allow_headers=["*"],
)

# 活跃游戏会话
active_games: Dict[str, dict] = {}

# ─── AI 自动补位：难度/主题常量 ───────────────────────────────────────────

# 难度等级映射（基于 agent_personas.json 中的 difficulty_level）
DIFFICULTY_POOLS = {
    "easy": ["laowang", "xiaoli", "meimei", "luobo", "xiaoming"],
    "medium": ["jiaoshou", "pukelian", "kuangmo", "laoqian", "laohu"],
    "hard": ["dushen", "nvwang", "guanjun", "wangzhe", "lengxue"],
}

# 个性主题映射
THEME_POOLS = {
    "aggressive": ["dushen", "kuangmo", "laohu", "nvwang", "guanjun"],
    "balanced": ["laowang", "pukelian", "meimei", "luobo", "laoqian"],
    "beginner_friendly": ["xiaoming", "xiaoli", "luobo", "meimei", "laowang"],
}


def _auto_fill_ai(
    human_count: int,
    existing_ai_ids: List[str],
    table_size: int,
    difficulty: str,
    theme: str,
    preferred: List[str],
    all_personas: List[dict],
) -> List[dict]:
    """
    根据配置自动选择 AI，返回 persona 列表。

    Args:
        human_count: 已有人类玩家数量
        existing_ai_ids: 已经选择的 AI ID 列表（避免重复）
        table_size: 牌桌总人数
        difficulty: easy/medium/hard/mixed
        theme: aggressive/balanced/beginner_friendly/random
        preferred: 手动指定的 AI ID 列表（覆盖难度/主题）
        all_personas: 所有可用 persona 配置

    Returns:
        选中的 persona 配置列表
    """
    vacancies = table_size - human_count - len(existing_ai_ids)
    if vacancies <= 0:
        return []

    # 1. 构建候选池
    if preferred:
        # 手动指定优先
        selected_ids = [pid for pid in preferred if pid not in existing_ai_ids]
        # 如果手动指定的不够，从全池补齐
        if len(selected_ids) < vacancies:
            # 优先级：preferred > 难度筛选 > 全池
            remaining = vacancies - len(selected_ids)
            difficulty_ids = set()
            if difficulty != "mixed":
                difficulty_ids = set(DIFFICULTY_POOLS.get(difficulty, []))
            all_ids = {p["id"] for p in all_personas}
            # 优先级池 = preferred + difficulty + 主题 + 全池
            extra_pool = []
            # 按难度筛选
            if difficulty != "mixed":
                extra_pool.extend(DIFFICULTY_POOLS.get(difficulty, []))
            # 按主题叠加
            theme_ids = THEME_POOLS.get(theme, [])
            for tid in theme_ids:
                if tid not in extra_pool:
                    extra_pool.append(tid)
            # 最后补全池
            for pid in all_ids:
                if pid not in extra_pool and pid not in selected_ids and pid not in preferred:
                    extra_pool.append(pid)
            # 去重已选和已分配的
            extra_pool = [pid for pid in extra_pool if pid not in existing_ai_ids and pid not in selected_ids]
            # 随机采样
            if len(extra_pool) >= remaining:
                selected_ids.extend(random.sample(extra_pool, remaining))
            else:
                selected_ids.extend(extra_pool)
    else:
        # 无手动指定：按难度和主题构建候选池
        candidate_ids = set()

        # 按难度筛选（mixed 表示全部）
        if difficulty in DIFFICULTY_POOLS:
            candidate_ids.update(DIFFICULTY_POOLS[difficulty])
        elif difficulty == "mixed":
            candidate_ids.update(p["id"] for p in all_personas)

        # 按主题叠加
        if theme in THEME_POOLS:
            candidate_ids.update(THEME_POOLS[theme])
        elif theme == "random":
            # 随机从全部中选择，不限池
            candidate_ids.update(p["id"] for p in all_personas)

        # 去除已选 AI
        candidate_ids.difference_update(existing_ai_ids)

        # 如果候选池不够，从全池补充
        if len(candidate_ids) < vacancies:
            all_ids = {p["id"] for p in all_personas}
            all_ids.difference_update(existing_ai_ids)
            all_ids.difference_update(candidate_ids)
            # 从全池随机补够
            extra_needed = vacancies - len(candidate_ids)
            candidate_ids.update(random.sample(list(all_ids), min(extra_needed, len(all_ids))))

        # 随机采样
        candidate_list = list(candidate_ids)
        if len(candidate_list) >= vacancies:
            selected_ids = random.sample(candidate_list, vacancies)
        else:
            selected_ids = candidate_list

    # 2. 从 all_personas 中获取对应的完整 persona 配置
    persona_map = {p["id"]: p for p in all_personas}
    selected_personas = [persona_map[aid] for aid in selected_ids if aid in persona_map]

    return selected_personas


# ─── 游戏 API ───────────────────────────────────────────────────────────


class CreateGameRequest(BaseModel):
    player_name: str = Field(default="Player", min_length=1, max_length=50)
    table_size: int = Field(default=9, ge=2, le=9)
    num_agents: int = Field(default=3, ge=1, le=8)
    ai_fill_enabled: bool = True
    ai_difficulty_level: Literal["easy", "medium", "hard", "mixed"] = "mixed"
    ai_persona_theme: Literal["aggressive", "balanced", "beginner_friendly", "random"] = "balanced"
    preferred_ai_personas: List[str] = Field(default_factory=list, max_length=8)
    agent_ids: List[str] = Field(default_factory=list, max_length=8)


@app.get("/api/health")
async def health():
    return {"status": "ok", "agent_mode": settings.POKER_AGENT_MODE}


@app.get("/api/local-mode")
async def runtime_mode():
    return {"mode": settings.POKER_AGENT_MODE, "paid_api_calls": settings.POKER_AGENT_MODE == "llm"}


@app.post("/api/games")
async def create_game(body: CreateGameRequest, request: Request):
    """创建新牌局"""
    import uuid
    import json

    body = body.model_dump()
    game_id = str(uuid.uuid4())

    # 加载 Agent 人格配置
    with open(CONFIG_DIR / "agent_personas.json", encoding="utf-8") as f:
        all_personas = json.load(f)["agents"]

    with open(CONFIG_DIR / "game_config.json", encoding="utf-8") as f:
        game_cfg = json.load(f)

    known_ids = {p["id"] for p in all_personas}
    for ids in (body["agent_ids"], body["preferred_ai_personas"]):
        if len(ids) != len(set(ids)) or not set(ids) <= known_ids:
            raise HTTPException(status_code=422, detail="Unknown or duplicate AI persona")
    if len(body["agent_ids"]) >= body["table_size"]:
        raise HTTPException(status_code=422, detail="Selected agents exceed table size")

    # 创建玩家列表
    players = []
    agent_map = {}

    # 真人玩家
    human_player = Player(
        id="player_human",
        name=body.get("player_name", "Player"),
        stack=game_cfg["game"]["default_stack"],
        player_type="human"
    )
    players.append(human_player)

    # ─── AI 自动补位逻辑 ───
    table_size = body.get("table_size", 9)
    ai_fill_enabled = body.get("ai_fill_enabled", True)
    ai_difficulty_level = body.get("ai_difficulty_level", "mixed")
    ai_persona_theme = body.get("ai_persona_theme", "balanced")
    preferred_ai_personas = body.get("preferred_ai_personas", [])

    # 手动选择的 agent_ids（手动分配模式或作为自动补位的已有选择）
    agent_ids = body.get("agent_ids")
    num_agents = body.get("num_agents", 3)

    # 获取手动选择的 AI
    manually_selected_personas = []
    if agent_ids and isinstance(agent_ids, list):
        manually_selected_personas = [p for p in all_personas if p["id"] in agent_ids]

    # 自动补位
    existing_ai_ids = [p["id"] for p in manually_selected_personas]
    human_count = 1  # 当前只有1个真人

    if ai_fill_enabled:
        auto_fill_personas = _auto_fill_ai(
            human_count=human_count,
            existing_ai_ids=existing_ai_ids,
            table_size=table_size,
            difficulty=ai_difficulty_level,
            theme=ai_persona_theme,
            preferred=preferred_ai_personas,
            all_personas=all_personas,
        )
    else:
        # 关闭自动补位，仍使用手动选择
        auto_fill_personas = []

    # 合并手动选择和自动补位
    all_selected_personas = (manually_selected_personas + auto_fill_personas)[:table_size - 1]

    # 如果没有任何 AI（包括自动补位关闭且未手动选择），使用旧逻辑 fallback
    if not all_selected_personas:
        if agent_ids and isinstance(agent_ids, list):
            all_selected_personas = [p for p in all_personas if p["id"] in agent_ids]
        else:
            all_selected_personas = all_personas[:min(num_agents, table_size - 1)]

    # 验证最低人数：至少需要 2 名玩家
    total_players = human_count + len(all_selected_personas)
    if total_players < 2:
        raise HTTPException(
            status_code=400,
            detail=f"至少需要 2 名玩家（当前真人: {human_count}, AI: {len(all_selected_personas)}）"
        )

    for persona in all_selected_personas:
        agent_player = Player(
            id=f"agent_{persona['id']}",
            name=persona["name"],
            stack=game_cfg["game"]["default_stack"],
            player_type="llm_agent",
            agent_config=persona
        )
        players.append(agent_player)
        try:
            agent_class = StrategyAgent if settings.POKER_AGENT_MODE == "strategy" else LLMAgent
            agent_map[agent_player.id] = agent_class(persona, agent_player)
        except Exception as exc:
            raise HTTPException(status_code=503, detail="AI client unavailable; check server API configuration") from exc

    # 随机打乱玩家座位顺序
    random.shuffle(players)

    # 初始化游戏引擎
    game = GameEngine(players, min_bet=game_cfg["game"]["small_blind"])

    # 初始化日志记录器
    logger = GameLogger(game_id)
    logger.log_game_created(
        players=[{"id": p.id, "name": p.name, "stack": p.stack, "player_type": p.player_type} for p in players],
        config=game_cfg
    )

    active_games[game_id] = {
        "engine": game,
        "agents": agent_map,
        "config": game_cfg,
        "logger": logger
    }

    session = GameSession(game, agent_map, game_cfg, logger)
    active_games[game_id]["session"] = session
    active_games[game_id]["expiry_task"] = asyncio.create_task(expire_game(game_id, session))
    return {
        "sessionToken": session.token,
        "gameId": game_id,
        "wsUrl": str(request.base_url).replace("https://", "wss://").replace("http://", "ws://").rstrip("/") + f"/ws/{game_id}",
        "players": [{"id": p.id, "name": p.name, "stack": p.stack} for p in players]
    }


# ─── 日志 API ─────────────────────────────────────────────────────────


@app.get("/api/logs")
async def list_logs(limit: int = 20, admin=Depends(get_admin_user)):
    """列出所有游戏日志"""
    if not LOG_DIR.exists():
        return {"logs": []}

    log_files = sorted(LOG_DIR.glob("*.json"), key=lambda x: x.stat().st_mtime, reverse=True)
    logs = []

    for log_file in log_files[:limit]:
        try:
            with open(log_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                logs.append({
                    "filename": log_file.name,
                    "game_id": data.get("game_id"),
                    "created_at": data.get("created_at"),
                    "total_hands": len(data.get("hands", [])),
                    "players": [p.get("name") for p in data.get("players", [])],
                    "final_result": data.get("final_result"),
                })
        except Exception:
            continue

    return {"logs": logs}


@app.get("/api/logs/{filename}")
async def get_log(filename: str, admin=Depends(get_admin_user)):
    """获取特定日志详情"""
    log_file = (LOG_DIR / filename).resolve()
    if log_file.parent != LOG_DIR.resolve() or log_file.suffix != ".json":
        raise HTTPException(status_code=404, detail="Log not found")
    if not log_file.exists():
        raise HTTPException(status_code=404, detail="Log not found")

    try:
        with open(log_file, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/logs/{filename}/summary")
async def get_log_summary(filename: str, admin=Depends(get_admin_user)):
    """获取日志摘要"""
    log_file = (LOG_DIR / filename).resolve()
    if log_file.parent != LOG_DIR.resolve() or log_file.suffix != ".json":
        raise HTTPException(status_code=404, detail="Log not found")
    if not log_file.exists():
        raise HTTPException(status_code=404, detail="Log not found")

    try:
        with open(log_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        total_hands = len(data.get("hands", []))
        player_stats = {}

        for hand in data.get("hands", []):
            result = hand.get("result")
            if result and result.get("allocations"):
                for alloc in result["allocations"]:
                    pid = alloc.get("player_id")
                    pname = alloc.get("player_name")
                    if pid not in player_stats:
                        player_stats[pid] = {
                            "name": pname,
                            "hands_won": 0,
                            "total_winnings": 0,
                            "actions_count": 0,
                        }
                    if alloc.get("amount_won", 0) > 0:
                        player_stats[pid]["hands_won"] += 1
                        player_stats[pid]["total_winnings"] += alloc.get("amount_won", 0)

            # 统计行动次数
            for action in hand.get("actions", []):
                pid = action.get("player_id")
                if pid in player_stats:
                    player_stats[pid]["actions_count"] += 1

        return {
            "game_id": data.get("game_id"),
            "created_at": data.get("created_at"),
            "total_hands": total_hands,
            "players": data.get("players"),
            "player_stats": player_stats,
            "final_result": data.get("final_result"),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.websocket("/ws/{game_id}")
async def websocket_endpoint(websocket: WebSocket, game_id: str):
    await websocket.accept()
    session = None
    try:
        # Authenticate in the first frame, keeping bearer credentials out of URLs/logs.
        auth = await asyncio.wait_for(websocket.receive_json(), 10)
        game_data = active_games.get(game_id)
        session = game_data.get("session") if game_data else None
        token = auth.get("sessionToken") if isinstance(auth, dict) else None
        if not session or not isinstance(auth, dict) or auth.get("type") != "AUTH" or not isinstance(token, str) or not secrets.compare_digest(session.token.encode(), token.encode()):
            await websocket.close(code=4403)
            return
        if session.socket is not None:
            await websocket.close(code=4409)
            return
        session.socket = websocket
        session.last_seen = time.monotonic()
        if session.task is None:
            session.task = asyncio.create_task(session.run())
        await session.replay()
        while True:
            await session.command(await websocket.receive_json())
    except (WebSocketDisconnect, asyncio.TimeoutError, ValueError):
        pass
    finally:
        if session and session.socket is websocket:
            session.socket = None
            session.last_seen = time.monotonic()


async def expire_game(game_id, session):
    try:
        while True:
            await asyncio.sleep(30)
            if session.socket is None and time.monotonic() - session.last_seen > 1800:
                if session.task and not session.task.done():
                    session.task.cancel()
                    await asyncio.gather(session.task, return_exceptions=True)
                active_games.pop(game_id, None)
                return
    except asyncio.CancelledError:
        pass


@app.on_event("shutdown")
async def shutdown_sessions():
    tasks = []
    for data in active_games.values():
        session = data["session"]
        tasks.extend(t for t in (session.task, data.get("expiry_task")) if t is not None)
        if session.socket:
            await session.socket.close(code=1001)
    for task in tasks:
        task.cancel()
    await asyncio.gather(*tasks, return_exceptions=True)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
