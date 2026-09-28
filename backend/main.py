"""
FastAPI 主入口 + WebSocket 游戏服务器
"""
import os
import json
import asyncio
import random
from pathlib import Path
from typing import Dict, List
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

from game_engine import GameEngine, Player, GamePhase
from llm_agent import LLMAgent
from game_logger import GameLogger

# Import auth and admin modules
from database.connection import init_db
from auth import router as auth_router
from admin import router as admin_router

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
    allow_origins=["http://localhost:3000", "http://101.35.6.63:3001", "http://101.35.6.63"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# 活跃游戏会话
active_games: Dict[str, dict] = {}

# WebSocket 连接池
connections: Dict[str, WebSocket] = {}

# 游戏暂停状态
game_paused: Dict[str, asyncio.Event] = {}

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


@app.post("/api/games")
async def create_game(body: dict):
    """创建新牌局"""
    import uuid
    import json

    game_id = str(uuid.uuid4())[:8]
    api_key = os.getenv("DEEPSEEK_API_KEY", "")

    # 加载 Agent 人格配置
    with open(CONFIG_DIR / "agent_personas.json", encoding="utf-8") as f:
        all_personas = json.load(f)["agents"]

    with open(CONFIG_DIR / "game_config.json", encoding="utf-8") as f:
        game_cfg = json.load(f)

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
    all_selected_personas = manually_selected_personas + auto_fill_personas

    # 如果没有任何 AI（包括自动补位关闭且未手动选择），使用旧逻辑 fallback
    if not all_selected_personas:
        if agent_ids and isinstance(agent_ids, list):
            all_selected_personas = [p for p in all_personas if p["id"] in agent_ids]
        else:
            all_selected_personas = all_personas[:num_agents]

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
        agent_map[agent_player.id] = LLMAgent(persona, agent_player)

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

    return {
        "gameId": game_id,
        "wsUrl": f"ws://localhost:8000/ws/{game_id}",
        "players": [{"id": p.id, "name": p.name, "stack": p.stack} for p in players]
    }


# ─── 日志 API ─────────────────────────────────────────────────────────


@app.get("/api/logs")
async def list_logs(limit: int = 20):
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
async def get_log(filename: str):
    """获取特定日志详情"""
    log_file = LOG_DIR / filename
    if not log_file.exists():
        raise HTTPException(status_code=404, detail="Log not found")

    try:
        with open(log_file, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/logs/{filename}/summary")
async def get_log_summary(filename: str):
    """获取日志摘要"""
    log_file = LOG_DIR / filename
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
    connections[game_id] = websocket

    # 初始化暂停状态（默认不暂停）
    game_paused[game_id] = asyncio.Event()
    game_paused[game_id].set()  # set = not paused

    try:
        game_data = active_games.get(game_id)
        if not game_data:
            await websocket.send_json({"type": "ERROR", "data": {"message": "Game not found"}})
            return

        game: GameEngine = game_data["engine"]
        agents: dict = game_data["agents"]
        cfg: dict = game_data["config"]
        logger: GameLogger = game_data["logger"]

        # 发牌开始
        game.deal_hole_cards()
        game.post_blinds()

        # 记录第一手牌开始
        logger.log_hand_start(
            hand_number=1,
            dealer_idx=game.dealer_idx,
            players_state=[
                {
                    "id": p.id,
                    "name": p.name,
                    "stack": p.stack,
                    "position": p.position,
                    "hole_cards": [c.to_string() for c in p.hole_cards],
                }
                for p in game.players
            ]
        )
        logger.log_phase_change(
            phase="pre_flop",
            community_cards=[],
            pot=game.pot
        )

        await broadcast(websocket, "GAME_STARTED", game.get_state_snapshot())

        # 多局游戏循环
        hand_count = 0
        while True:
            hand_count += 1

            # 检查是否还有多于1名玩家有筹码
            players_with_chips = [p for p in game.players if p.stack > 0]
            if len(players_with_chips) <= 1:
                # 游戏结束，只剩一人
                logger.log_tournament_end(
                    winner=players_with_chips[0].name if players_with_chips else "Unknown",
                    final_stacks={p.id: p.stack for p in game.players}
                )
                await broadcast(websocket, "TOURNAMENT_ENDED", {
                    "winner": players_with_chips[0].name if players_with_chips else "Unknown",
                    "finalStacks": {p.id: p.stack for p in game.players}
                })
                break

            # 单局游戏循环
            while game.phase not in (GamePhase.ENDED, GamePhase.SHOWDOWN):

                # 检查是否只剩一人
                remaining = game.non_folded_players()
                if len(remaining) <= 1:
                    allocations = game.determine_winners()
                    logger.log_hand_result(allocations, game.pot)
                    await broadcast(websocket, "GAME_ENDED", {
                        "allocations": allocations,
                        "finalState": game.get_state_snapshot()
                    })
                    game.phase = GamePhase.ENDED
                    break

                active = game.get_action_order()
                round_complete = False
                print(f"[DEBUG] Starting action round: phase={game.phase.value}, active_count={len(active)}, pending={game.pending_actors}")

                for player in active:
                    # 每轮开始前重新检查
                    if game.phase in (GamePhase.ENDED, GamePhase.SHOWDOWN):
                        round_complete = True
                        break

                    if player.player_type == "llm_agent":
                        agent = agents.get(player.id)
                        if not agent:
                            continue

                        # 等待暂停恢复
                        await game_paused[game_id].wait()

                        await broadcast(websocket, "AGENT_THINKING_START", {"agentId": player.id})

                        def on_chunk(agent_id: str, text: str):
                            asyncio.create_task(
                                broadcast(websocket, "AGENT_THINKING_CHUNK",
                                          {"agentId": agent_id, "chunk": text})
                            )

                        timeout = cfg["game"]["agent_timeout_ms"] / 1000
                        response = await agent.decide(game, timeout=timeout, on_chunk=on_chunk)

                        await broadcast(websocket, "AGENT_THINKING_END", {
                            "agentId": player.id,
                            "action": response.action.type.value if response.action else "fold",
                            "speech": response.speech
                        })

                        if response.action:
                            game.process_action(response.action)
                        if response.speech:
                            game.record_speech(player.id, response.speech)
                            logger.log_speech(player.id, player.name, response.speech, game.phase.value)

                        # 记录AI行动
                        logger.log_player_action(
                            player_id=player.id,
                            player_name=player.name,
                            action=response.action.type.value if response.action else "fold",
                            amount=response.action.amount if response.action else 0,
                            phase=game.phase.value,
                            pot_after=game.pot,
                            stack_after=player.stack,
                            thinking=response.thinking
                        )

                        await broadcast(websocket, "PLAYER_ACTION", {
                            "playerId": player.id,
                            "action": response.action.type.value if response.action else "fold",
                            "amount": response.action.amount if response.action else 0,
                            "pot": game.pot,
                            "stateSnapshot": game.get_state_snapshot()
                        })

                    else:
                        # 真人玩家
                        valid_actions = game.get_valid_actions(player)
                        timeout_ms = cfg["game"]["human_timeout_ms"]

                        await broadcast(websocket, "PLAYER_ACTION_REQUEST", {
                            "playerId": player.id,
                            "validActions": [a.value for a in valid_actions],
                            "callAmount": max(0, game.street_bet - player.current_bet),
                            "pot": game.pot,
                            "timeLimit": timeout_ms
                        })

                        try:
                            msg = await asyncio.wait_for(
                                websocket.receive_json(),
                                timeout=timeout_ms / 1000
                            )
                            # 处理暂停/恢复消息
                            if msg.get("type") == "PAUSE":
                                game_paused[game_id].clear()
                                continue
                            if msg.get("type") == "RESUME":
                                game_paused[game_id].set()
                                continue
                            from game_engine import Action, ActionType

                            # 处理人类玩家的发言
                            human_speech = msg.get("speech", "")
                            if human_speech:
                                game.record_speech(player.id, human_speech)
                                logger.log_speech(player.id, player.name, human_speech, game.phase.value)

                            human_action = Action(
                                player_id=player.id,
                                type=ActionType(msg.get("action", "fold")),
                                amount=msg.get("amount", 0)
                            )
                            game.process_action(human_action)
                            print(f"[DEBUG] Human action processed: {human_action.type.value}")

                            # 记录人类玩家行动
                            logger.log_player_action(
                                player_id=player.id,
                                player_name=player.name,
                                action=human_action.type.value,
                                amount=human_action.amount,
                                phase=game.phase.value,
                                pot_after=game.pot,
                                stack_after=player.stack
                            )

                            await broadcast(websocket, "PLAYER_ACTION", {
                                "playerId": player.id,
                                "action": human_action.type.value,
                                "amount": human_action.amount,
                                "speech": human_speech,
                                "pot": game.pot,
                                "stateSnapshot": game.get_state_snapshot()
                            })
                        except asyncio.TimeoutError:
                            from game_engine import Action, ActionType
                            if game.street_bet == player.current_bet:
                                timeout_action = Action(player_id=player.id, type=ActionType.CHECK)
                            else:
                                timeout_action = Action(player_id=player.id, type=ActionType.FOLD)
                            game.process_action(timeout_action)

                            # 记录超时行动
                            logger.log_player_action(
                                player_id=player.id,
                                player_name=player.name,
                                action=timeout_action.type.value,
                                amount=timeout_action.amount,
                                phase=game.phase.value,
                                pot_after=game.pot,
                                stack_after=player.stack,
                                thinking="(超时自动行动)"
                            )

                            await broadcast(websocket, "PLAYER_ACTION", {
                                "playerId": player.id,
                                "action": timeout_action.type.value,
                                "amount": timeout_action.amount,
                                "pot": game.pot,
                                "stateSnapshot": game.get_state_snapshot()
                            })
                        except (RuntimeError, WebSocketDisconnect):
                            # WebSocket 断开连接，将玩家视为弃牌
                            print(f"[DEBUG] WebSocket disconnected during human turn, folding")
                            from game_engine import Action, ActionType
                            fold_action = Action(player_id=player.id, type=ActionType.FOLD)
                            game.process_action(fold_action)
                            raise WebSocketDisconnect()

                    # 每次 action 后检查是否只剩一人
                    if len(game.non_folded_players()) <= 1:
                        allocations = game.determine_winners()
                        logger.log_hand_result(allocations, game.pot)
                        await broadcast(websocket, "GAME_ENDED", {
                            "allocations": allocations,
                            "finalState": game.get_state_snapshot()
                        })
                        game.phase = GamePhase.ENDED
                        break

                    # 每次 action 后检查下注轮是否结束
                    betting_complete = game.is_betting_round_complete()
                    print(f"[DEBUG] phase={game.phase.value}, betting_complete={betting_complete}, pending={game.pending_actors}, street_bet={game.street_bet}")
                    if betting_complete:
                        if game.phase == GamePhase.RIVER:
                            game.phase = GamePhase.SHOWDOWN
                            print(f"[DEBUG] Entering SHOWDOWN")
                            logger.log_phase_change(
                                phase="showdown",
                                community_cards=[c.to_string() for c in game.community_cards],
                                pot=game.pot
                            )
                            # 广播进入摊牌阶段
                            await broadcast(websocket, "PHASE_CHANGED", game.get_state_snapshot())
                        else:
                            game.advance_phase()
                            logger.log_phase_change(
                                phase=game.phase.value,
                                community_cards=[c.to_string() for c in game.community_cards],
                                pot=game.pot
                            )
                            await broadcast(websocket, "PHASE_CHANGED", game.get_state_snapshot())
                        round_complete = True
                        break

                if game.phase in (GamePhase.ENDED, GamePhase.SHOWDOWN):
                    break
                if round_complete:
                    continue

                # 无人行动(所有人 all-in), 自动推进行到 showdown
                if not active:
                    while game.phase != GamePhase.SHOWDOWN:
                        game.advance_phase()
                        logger.log_phase_change(
                            phase=game.phase.value,
                            community_cards=[c.to_string() for c in game.community_cards],
                            pot=game.pot
                        )
                        await broadcast(websocket, "PHASE_CHANGED", game.get_state_snapshot())
                        # 延迟以便前端展示每一轮发牌动画
                        await asyncio.sleep(1.5)
                    break

            # 摊牌
            if game.phase == GamePhase.SHOWDOWN:
                print(f"[DEBUG] Processing SHOWDOWN")

                # 先发送亮牌事件，让前端显示所有人的底牌
                reveal_data = {
                    "players": [
                        {
                            "id": p.id,
                            "name": p.name,
                            "holeCards": [{"rank": c.rank, "suit": c.suit} for c in p.hole_cards],
                            "status": p.status.value,
                        }
                        for p in game.players
                        if p.status.value != "folded"  # 只显示未弃牌玩家的牌
                    ]
                }
                await broadcast(websocket, "REVEAL_ALL_CARDS", reveal_data)

                # 记录摊牌信息
                logger.log_showdown([
                    {
                        "id": p.id,
                        "name": p.name,
                        "hole_cards": [c.to_string() for c in p.hole_cards],
                    }
                    for p in game.players
                    if p.status.value != "folded"
                ])

                # 等待3秒让玩家看清所有人的牌
                await asyncio.sleep(3)

                # 然后计算赢家并发送结算结果
                print(f"[DEBUG] Calling determine_winners()")
                allocations = game.determine_winners()
                print(f"[DEBUG] SHOWDOWN allocations: {allocations}")

                # 记录手牌结果
                logger.log_hand_result(allocations, game.pot)

                await broadcast(websocket, "SHOWDOWN", {
                    "allocations": allocations,
                    "finalState": game.get_state_snapshot()
                })

            # 等待玩家确认进入下一局
            print(f"[DEBUG] Waiting for READY_FOR_NEXT_HAND...")
            try:
                while True:
                    msg = await asyncio.wait_for(websocket.receive_json(), timeout=300)
                    print(f"[DEBUG] Received message while waiting: {msg}")
                    if msg.get("type") == "READY_FOR_NEXT_HAND":
                        print(f"[DEBUG] Got READY_FOR_NEXT_HAND, proceeding to next hand")
                        break
                    if msg.get("type") == "PAUSE":
                        game_paused[game_id].clear()
                    if msg.get("type") == "RESUME":
                        game_paused[game_id].set()
                    # 忽略其他消息，继续等待
            except asyncio.TimeoutError:
                print(f"[DEBUG] Timeout waiting for READY_FOR_NEXT_HAND, auto-continuing")
            except Exception as e:
                print(f"[DEBUG] Exception while waiting for READY_FOR_NEXT_HAND: {e}")
                raise  # 重新抛出异常，让外层处理

            # 重置游戏状态以开始新的一手牌
            game.reset_for_new_hand()
            game.deal_hole_cards()
            game.post_blinds()

            # 记录新一手牌开始
            logger.log_hand_start(
                hand_number=hand_count + 1,
                dealer_idx=game.dealer_idx,
                players_state=[
                    {
                        "id": p.id,
                        "name": p.name,
                        "stack": p.stack,
                        "position": p.position,
                        "hole_cards": [c.to_string() for c in p.hole_cards],
                    }
                    for p in game.players
                ]
            )
            logger.log_phase_change(
                phase="pre_flop",
                community_cards=[],
                pot=game.pot
            )

            await broadcast(websocket, "HAND_STARTED", {
                "handNumber": hand_count,
                "gameState": game.get_state_snapshot()
            })

    except WebSocketDisconnect:
        connections.pop(game_id, None)


async def broadcast(websocket: WebSocket, event_type: str, data: dict):
    """向客户端发送 WebSocket 消息"""
    try:
        await websocket.send_json({"type": event_type, "data": data})
    except Exception:
        pass


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
