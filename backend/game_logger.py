"""
游戏日志记录器
记录每局游戏的详细信息
"""
import os
import json
from datetime import datetime
from typing import Optional, List, Dict, Any
from pathlib import Path


class GameLogger:
    """游戏日志记录器 - 为每个游戏会话创建详细日志"""

    def __init__(self, game_id: str, log_dir: str = "../logs"):
        self.game_id = game_id
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)

        # 创建日志文件名：日期_时间_游戏ID.json
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.log_file = self.log_dir / f"{timestamp}_{game_id}.json"

        # 日志数据结构
        self.log_data = {
            "game_id": game_id,
            "created_at": datetime.now().isoformat(),
            "players": [],
            "config": {},
            "hands": [],  # 每手牌的记录
            "current_hand": None,  # 当前手牌记录
            "final_result": None,
        }

        self._save()

    def _save(self):
        """保存日志到文件"""
        with open(self.log_file, "w", encoding="utf-8") as f:
            json.dump(self.log_data, f, ensure_ascii=False, indent=2)

    def _timestamp(self) -> str:
        """获取当前时间戳"""
        return datetime.now().isoformat()

    def log_game_created(self, players: List[Dict], config: Dict):
        """记录游戏创建"""
        self.log_data["players"] = [
            {
                "id": p.get("id"),
                "name": p.get("name"),
                "type": p.get("player_type", "unknown"),
                "initial_stack": p.get("stack", 0),
            }
            for p in players
        ]
        self.log_data["config"] = config
        self._save()

    def log_hand_start(self, hand_number: int, dealer_idx: int, players_state: List[Dict]):
        """记录新一手牌开始"""
        self.log_data["current_hand"] = {
            "hand_number": hand_number,
            "started_at": self._timestamp(),
            "dealer_index": dealer_idx,
            "players_at_start": [
                {
                    "id": p.get("id"),
                    "name": p.get("name"),
                    "stack": p.get("stack", 0),
                    "position": p.get("position", ""),
                    "hole_cards": p.get("hole_cards", []),
                }
                for p in players_state
            ],
            "community_cards": [],
            "phases": [],
            "actions": [],
            "speeches": [],
            "pot_history": [],
            "result": None,
        }
        self._save()

    def log_hole_cards(self, player_id: str, cards: List[str]):
        """记录玩家底牌"""
        if self.log_data["current_hand"]:
            for p in self.log_data["current_hand"]["players_at_start"]:
                if p["id"] == player_id:
                    p["hole_cards"] = cards
                    break
            self._save()

    def log_phase_change(self, phase: str, community_cards: List[str], pot: float):
        """记录阶段变化"""
        if self.log_data["current_hand"]:
            self.log_data["current_hand"]["phases"].append({
                "phase": phase,
                "timestamp": self._timestamp(),
                "community_cards": community_cards,
                "pot": pot,
            })
            self.log_data["current_hand"]["community_cards"] = community_cards
            self.log_data["current_hand"]["pot_history"].append({
                "phase": phase,
                "pot": pot,
            })
            self._save()

    def log_player_action(
        self,
        player_id: str,
        player_name: str,
        action: str,
        amount: float,
        phase: str,
        pot_after: float,
        stack_after: float,
        thinking: Optional[str] = None,
    ):
        """记录玩家行动"""
        if self.log_data["current_hand"]:
            action_record = {
                "timestamp": self._timestamp(),
                "player_id": player_id,
                "player_name": player_name,
                "action": action,
                "amount": amount,
                "phase": phase,
                "pot_after": pot_after,
                "stack_after": stack_after,
            }
            if thinking:
                action_record["ai_thinking"] = thinking[:500]  # 限制长度
            self.log_data["current_hand"]["actions"].append(action_record)
            self._save()

    def log_speech(self, player_id: str, player_name: str, speech: str, phase: str):
        """记录玩家发言"""
        if self.log_data["current_hand"] and speech:
            self.log_data["current_hand"]["speeches"].append({
                "timestamp": self._timestamp(),
                "player_id": player_id,
                "player_name": player_name,
                "speech": speech,
                "phase": phase,
            })
            self._save()

    def log_showdown(self, players_hands: List[Dict]):
        """记录摊牌信息"""
        if self.log_data["current_hand"]:
            self.log_data["current_hand"]["showdown"] = {
                "timestamp": self._timestamp(),
                "players": [
                    {
                        "id": p.get("id"),
                        "name": p.get("name"),
                        "hole_cards": p.get("hole_cards", []),
                        "best_hand": p.get("best_hand", []),
                        "hand_rank": p.get("hand_rank", ""),
                    }
                    for p in players_hands
                ],
            }
            self._save()

    def log_hand_result(self, allocations: List[Dict], final_pot: float):
        """记录手牌结果"""
        if self.log_data["current_hand"]:
            self.log_data["current_hand"]["result"] = {
                "timestamp": self._timestamp(),
                "final_pot": final_pot,
                "allocations": [
                    {
                        "player_id": a.get("playerId"),
                        "player_name": a.get("playerName"),
                        "amount_won": a.get("amount", 0),
                        "hand_rank": a.get("handRank", ""),
                        "best_hand": a.get("bestHand", []),
                        "reason": a.get("reason", ""),
                    }
                    for a in allocations
                ],
            }
            self.log_data["current_hand"]["ended_at"] = self._timestamp()

            # 将当前手牌移入历史记录
            self.log_data["hands"].append(self.log_data["current_hand"])
            self.log_data["current_hand"] = None
            self._save()

    def log_tournament_end(self, winner: str, final_stacks: Dict[str, float]):
        """记录锦标赛结束"""
        self.log_data["final_result"] = {
            "timestamp": self._timestamp(),
            "winner": winner,
            "final_stacks": final_stacks,
            "total_hands": len(self.log_data["hands"]),
        }
        self._save()

    def log_error(self, error_type: str, error_message: str, context: Optional[Dict] = None):
        """记录错误"""
        if "errors" not in self.log_data:
            self.log_data["errors"] = []
        self.log_data["errors"].append({
            "timestamp": self._timestamp(),
            "type": error_type,
            "message": error_message,
            "context": context,
        })
        self._save()

    def get_log_path(self) -> str:
        """获取日志文件路径"""
        return str(self.log_file)

    def get_summary(self) -> Dict:
        """获取游戏摘要"""
        total_hands = len(self.log_data["hands"])
        player_stats = {}

        for hand in self.log_data["hands"]:
            if hand.get("result") and hand["result"].get("allocations"):
                for alloc in hand["result"]["allocations"]:
                    pid = alloc.get("player_id")
                    if pid not in player_stats:
                        player_stats[pid] = {
                            "name": alloc.get("player_name"),
                            "hands_won": 0,
                            "total_winnings": 0,
                        }
                    if alloc.get("amount_won", 0) > 0:
                        player_stats[pid]["hands_won"] += 1
                        player_stats[pid]["total_winnings"] += alloc.get("amount_won", 0)

        return {
            "game_id": self.game_id,
            "total_hands": total_hands,
            "player_stats": player_stats,
            "final_result": self.log_data.get("final_result"),
        }
