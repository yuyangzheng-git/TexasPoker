"""
德州扑克游戏引擎
管理游戏流程、发牌、下注轮、底池和胜负判定
"""
import random
import math
from enum import Enum
from typing import List, Optional
from dataclasses import dataclass, field
from hand_evaluator import Card, HandEvaluator


class GamePhase(str, Enum):
    PRE_FLOP = "pre_flop"
    FLOP     = "flop"
    TURN     = "turn"
    RIVER    = "river"
    SHOWDOWN = "showdown"
    ENDED    = "ended"


class PlayerStatus(str, Enum):
    ACTIVE = "active"
    FOLDED = "folded"
    ALLIN  = "allin"


class ActionType(str, Enum):
    FOLD  = "fold"
    CHECK = "check"
    CALL  = "call"
    RAISE = "raise"
    ALLIN = "allin"


@dataclass
class Action:
    player_id: str
    type: ActionType
    amount: float = 0.0
    phase: str    = ""
    speech: str   = ""
    street_bet_before: Optional[float] = None
    player_bet_before: Optional[float] = None


@dataclass
class Player:
    id: str
    name: str
    stack: float
    player_type: str = "human"  # "human" | "llm_agent"
    hole_cards: List[Card] = field(default_factory=list)
    current_bet: float = 0.0
    status: PlayerStatus = PlayerStatus.ACTIVE
    position: str = ""
    agent_config: Optional[dict] = None


@dataclass
class Pot:
    amount: float
    eligible_player_ids: List[str]


class GameEngine:
    """德州扑克核心游戏引擎"""

    def __init__(self, players: List[Player], min_bet: float = 10.0):
        self.players     = players
        self.min_bet     = min_bet
        self.big_blind   = min_bet * 2
        self.phase       = GamePhase.PRE_FLOP
        self.pot         = 0.0
        self.street_bet  = 0.0
        self.dealer_idx  = 0
        self.community_cards: List[Card] = []
        self.deck: List[Card] = []
        self.action_history: List[Action] = []
        self.pots: List[Pot] = []
        self.last_action_phase: str = ""
        self.pending_actors: set = set()
        self.speech_history: list = []
        self.hand_start_stacks: dict = {p.id: p.stack for p in players}
        # 跟踪整局中每个玩家的总下注额（用于边池计算）
        self.total_bets: dict = {p.id: 0.0 for p in players}
        self.last_full_raise = self.big_blind
        self.acted_bets: dict = {}
        self.last_actor_idx = None
        self.hand_player_ids = {p.id for p in players if p.stack > 0}
        self.betting_started = False
        self._allocations = None

    def get_recent_speech(self, max_lines: int = 5) -> str:
        """返回最近 max_lines 句对话"""
        recent = self.speech_history[-max_lines:]
        if not recent:
            return ""
        return "\n".join(f"  [{name}]: \"{speech}\"" for name, speech in recent)

    def record_speech(self, player_id: str, speech: str):
        """记录一名玩家的发言"""
        if not speech:
            return
        player = self._get_player(player_id)
        name = player.name if player else player_id
        self.speech_history.append((name, speech))

    def clear_speech_history(self):
        """新牌局开始时清空上局对话"""
        self.speech_history = []

    # ──────────────────────────────────────────
    # 1. 洗牌 & 发牌（Fisher-Yates）
    # ──────────────────────────────────────────
    def _build_deck(self) -> List[Card]:
        return [Card(rank, suit) for rank in range(2, 15) for suit in range(4)]

    def _shuffle_deck(self, deck: List[Card]) -> List[Card]:
        """Fisher-Yates 洗牌算法"""
        deck = deck[:]
        for i in range(len(deck) - 1, 0, -1):
            j = random.randint(0, i)
            deck[i], deck[j] = deck[j], deck[i]
        return deck

    def deal_hole_cards(self):
        """给所有 active 玩家发2张手牌"""
        self.deck = self._shuffle_deck(self._build_deck())
        for player in self.active_players():
            player.hole_cards = [self.deck.pop(), self.deck.pop()]

    def deal_community_cards(self):
        """按阶段发公共牌"""
        if self.phase == GamePhase.FLOP:
            self.community_cards += [self.deck.pop() for _ in range(3)]
        elif self.phase in (GamePhase.TURN, GamePhase.RIVER):
            self.community_cards.append(self.deck.pop())

    # ──────────────────────────────────────────
    # 2. 下注轮控制
    # ──────────────────────────────────────────
    def post_blinds(self):
        """强制下注小/大盲注"""
        if self.betting_started:
            raise ValueError("Blinds have already been posted")
        self.hand_player_ids = {p.id for p in self.players if p.stack > 0}
        if self.players[self.dealer_idx].id not in self.hand_player_ids:
            self.dealer_idx = self._next_live_seat(self.dealer_idx)
        self.assign_positions()
        active = self._hand_seats()
        if len(active) < 2:
            return
        button = next(i for i, p in enumerate(active) if p.id == self.players[self.dealer_idx].id)
        sb_idx = button if len(active) == 2 else (button + 1) % len(active)
        bb_idx = (sb_idx + 1) % len(active)

        self._place_blind(active[sb_idx], self.min_bet)       # 小盲注
        self._place_blind(active[bb_idx], self.big_blind)     # 大盲注
        self.street_bet = self.big_blind
        # Pre-flop: 初始化待行动玩家集合（仅 ACTIVE）
        self.pending_actors = {p.id for p in self.players if p.status == PlayerStatus.ACTIVE}
        self.betting_started = True
        self._skip_uncontested_action()

    def _hand_seats(self):
        return [p for p in self.players if p.id in self.hand_player_ids]

    def _next_live_seat(self, start):
        for step in range(1, len(self.players) + 1):
            idx = (start + step) % len(self.players)
            if self.players[idx].stack > 0:
                return idx
        return start

    def assign_positions(self):
        """根据庄家位置为所有玩家分配位置标签"""
        seats = self._hand_seats()
        n = len(seats)
        if not n:
            return
        # 顺时针从庄家开始的位置标签
        position_labels = {
            2: ["BTN/SB", "BB"],
            3: ["BTN", "SB", "BB"],
            4: ["BTN", "SB", "BB", "UTG"],
            5: ["BTN", "SB", "BB", "UTG", "CO"],
            6: ["BTN", "SB", "BB", "UTG", "MP", "CO"],
            7: ["BTN", "SB", "BB", "UTG", "MP", "HJ", "CO"],
            8: ["BTN", "SB", "BB", "UTG", "EP", "MP", "HJ", "CO"],
            9: ["BTN", "SB", "BB", "UTG", "EP", "MP", "LJ", "HJ", "CO"],
        }
        if n in position_labels:
            labels = position_labels[n]
        else:
            # 9人以上自动扩展
            base = ["BTN", "SB", "BB", "UTG", "EP", "MP", "LJ", "HJ", "CO"]
            labels = base + [f"P{i}" for i in range(9, n)]

        button = seats.index(self.players[self.dealer_idx])
        for p in self.players:
            p.position = ""
        for i, player in enumerate(seats):
            offset = (i - button) % n
            player.position = labels[offset]

    def _place_blind(self, player: Player, amount: float):
        actual = min(amount, player.stack)
        player.current_bet = actual
        player.stack -= actual
        self.pot += actual
        self.total_bets[player.id] += actual  # 记录总下注
        if player.stack == 0:
            player.status = PlayerStatus.ALLIN

    def process_action(self, action: Action) -> bool:
        """
        处理玩家行动，返回是否合法
        包含完整的规则校验
        """
        player = self._get_player(action.player_id)
        if player is None or player.status != PlayerStatus.ACTIVE:
            return False
        if self.phase in (GamePhase.SHOWDOWN, GamePhase.ENDED) or self._allocations is not None:
            return False
        if self.betting_started:
            order = self.get_action_order()
            if not order or order[0].id != player.id:
                return False
        if action.type not in self.get_valid_actions(player):
            return False
        if isinstance(action.amount, bool) or not isinstance(action.amount, (int, float)):
            return False
        try:
            if not math.isfinite(action.amount) or action.amount < 0:
                return False
        except OverflowError:
            return False

        old_bet = self.street_bet
        target = player.current_bet
        if action.type == ActionType.CALL:
            target += min(max(0, self.street_bet - player.current_bet), player.stack)
        elif action.type == ActionType.RAISE:
            target = action.amount
            if target < self.minimum_raise_to() or target > player.current_bet + player.stack:
                return False
        elif action.type == ActionType.ALLIN:
            target += player.stack

        # Validate first: rejected actions never mutate stacks, history or turn order.
        action.phase = self.phase.value
        action.street_bet_before = old_bet
        action.player_bet_before = player.current_bet
        if action.type == ActionType.ALLIN:
            # History records the actual raise-to total, independent of client input.
            action.amount = target
        if action.type == ActionType.FOLD:
            player.status = PlayerStatus.FOLDED
        else:
            contribution = target - player.current_bet
            player.stack -= contribution
            player.current_bet = target
            self.total_bets[player.id] += contribution
            self.pot += contribution
            if player.stack == 0:
                player.status = PlayerStatus.ALLIN
            self.street_bet = max(self.street_bet, target)

        increase = self.street_bet - old_bet
        if increase >= self.last_full_raise:
            self.last_full_raise = increase
        self.acted_bets[player.id] = self.street_bet
        self.last_actor_idx = self.players.index(player)
        self.pending_actors.discard(player.id)
        if increase > 0:
            self.pending_actors.update(
                p.id for p in self.active_players() if p.current_bet < self.street_bet
            )
        self.action_history.append(action)
        self.last_action_phase = self.phase.value
        self._skip_uncontested_action()
        return True

    def minimum_raise_to(self) -> float:
        return self.street_bet + self.last_full_raise

    def can_raise(self, player: Player) -> bool:
        # A short all-in requires a call, but only a full cumulative raise reopens betting.
        faced = self.acted_bets.get(player.id)
        return faced is None or self.street_bet - faced >= self.last_full_raise

    def _skip_uncontested_action(self):
        active = self.active_players()
        if len(self.non_folded_players()) <= 1:
            self.pending_actors.clear()
        elif len(active) == 1:
            opposing_bet = max((p.current_bet for p in self.non_folded_players() if p.id != active[0].id), default=0)
            if active[0].current_bet >= min(self.street_bet, opposing_bet):
                self.pending_actors.clear()

    def is_betting_round_complete(self) -> bool:
        return not self.pending_actors

    def advance_phase(self):
        """进入下一阶段"""
        # 重置每轮下注状态
        for p in self.players:
            p.current_bet = 0.0
        self.last_full_raise = self.big_blind
        self.acted_bets = {}
        self.last_actor_idx = None
        self.street_bet = 0.0
        self.last_action_phase = ""  # 重置行动跟踪
        # 新阶段开始时，所有活跃(ACTIVE)玩家都需行动
        self.pending_actors = {p.id for p in self.players if p.status == PlayerStatus.ACTIVE}
        self._skip_uncontested_action()

        phase_order = [
            GamePhase.PRE_FLOP, GamePhase.FLOP,
            GamePhase.TURN, GamePhase.RIVER
        ]
        if self.phase == GamePhase.SHOWDOWN:
            return
        idx = phase_order.index(self.phase)
        self.phase = phase_order[idx + 1] if idx + 1 < len(phase_order) else GamePhase.SHOWDOWN

        if self.phase != GamePhase.SHOWDOWN:
            self.deal_community_cards()

    def get_action_order(self) -> List[Player]:
        """返回当前下注轮正确的玩家行动顺序（基于庄家位置和阶段）"""
        seats = self._hand_seats()
        if not seats or not self.pending_actors:
            return []
        if self.last_actor_idx is not None:
            start = (self.last_actor_idx + 1) % len(self.players)
        elif self.phase == GamePhase.PRE_FLOP:
            button = seats.index(self.players[self.dealer_idx])
            first = seats[button] if len(seats) == 2 else seats[(button + 3) % len(seats)]
            start = self.players.index(first)
        else:
            start = (self.dealer_idx + 1) % len(self.players)
        return [
            self.players[(start + i) % len(self.players)]
            for i in range(len(self.players))
            if self.players[(start + i) % len(self.players)].status == PlayerStatus.ACTIVE
            and self.players[(start + i) % len(self.players)].id in self.pending_actors
        ]

    # ──────────────────────────────────────────
    # 3. 边池计算
    # ──────────────────────────────────────────
    def calculate_side_pots(self) -> List[Pot]:
        """
        计算主池和边池
        当有玩家 All-in 且筹码不等时触发
        使用 total_bets 跟踪整局总下注
        """
        # 所有玩家的下注
        all_bets: dict[str, float] = {
            p.id: self.total_bets.get(p.id, 0.0) for p in self.players
        }

        # 未弃牌玩家（只有他们能赢）
        non_folded_ids = {p.id for p in self.players if p.status != PlayerStatus.FOLDED}

        # 如果没有未弃牌玩家，返回空
        if not non_folded_ids:
            return []

        # 只有一个未弃牌玩家，他赢得全部底池
        if len(non_folded_ids) == 1:
            winner_id = list(non_folded_ids)[0]
            self.pots = [Pot(amount=self.pot, eligible_player_ids=[winner_id])]
            return self.pots

        # 多人未弃牌，按下注额计算边池
        # 使用所有玩家的下注级别（包括弃牌玩家）
        unique_levels = sorted(set(all_bets.values()))
        pots = []
        prev_level = 0.0

        for level in unique_levels:
            if level == 0:
                continue
            contribution = level - prev_level
            # 所有贡献此层级的玩家数量
            contributors = sum(1 for bet in all_bets.values() if bet >= level)
            amount = contribution * contributors
            # 有资格赢此边池的玩家（未弃牌且下注 >= level）
            eligible = [pid for pid in non_folded_ids if all_bets.get(pid, 0) >= level]
            if eligible:  # 只有在有资格玩家时才创建边池
                pots.append(Pot(amount=amount, eligible_player_ids=eligible))
            prev_level = level

        self.pots = pots
        return pots

    # ──────────────────────────────────────────
    # 4. 摊牌赢家判定
    # ──────────────────────────────────────────
    def determine_winners(self) -> List[dict]:
        """
        判定赢家并分配底池
        支持边池和平局均分
        返回包含筹码变化的结果
        """
        if self._allocations is not None:
            return self._allocations
        pots = self.calculate_side_pots()
        allocations = []

        for pot in pots:
            eligible = [
                p for p in self.players
                if p.id in pot.eligible_player_ids
                and p.status != PlayerStatus.FOLDED
            ]

            if len(eligible) == 0:
                continue

            if len(eligible) == 1:
                winner = eligible[0]
                start_stack = self.hand_start_stacks.get(winner.id, winner.stack)
                winner.stack += pot.amount
                allocations.append({
                    "playerId": winner.id,
                    "playerName": winner.name,
                    "amount": pot.amount,
                    "bestHand": [],
                    "handRank": "",
                    "stackChange": winner.stack - start_stack,
                    "reason": "last_standing"
                })
            else:
                # 对比所有 eligible 玩家的手牌
                scored = []
                for player in eligible:
                    score, best_hand = HandEvaluator.evaluate_best_hand(
                        player.hole_cards, self.community_cards
                    )
                    scored.append((score, player, best_hand))

                best_score = max(s for s, _, _ in scored)
                winners = [(p, h) for s, p, h in scored if s == best_score]

                share = pot.amount / len(winners)
                for winner, best_hand in winners:
                    # 将 Card 对象转换为可序列化的字符串列表
                    hand_str = [str(card) for card in best_hand] if best_hand else []
                    # 获取牌型名称
                    hand_rank = HandEvaluator.get_hand_rank_name(best_score) if best_score else ""
                    start_stack = self.hand_start_stacks.get(winner.id, winner.stack)
                    winner.stack += share
                    allocations.append({
                        "playerId": winner.id,
                        "playerName": winner.name,
                        "amount": share,
                        "bestHand": hand_str,
                        "handRank": hand_rank,
                        "stackChange": winner.stack - start_stack,
                        "reason": "showdown"
                    })

        # 为没有赢钱的玩家添加记录
        winner_ids = {a["playerId"] for a in allocations}
        for player in self.players:
            if player.id not in winner_ids:
                start_stack = self.hand_start_stacks.get(player.id, player.stack)
                change = player.stack - start_stack
                allocations.append({
                    "playerId": player.id,
                    "playerName": player.name,
                    "amount": 0,
                    "bestHand": [],
                    "handRank": "",
                    "stackChange": change,
                    "reason": "no_win"
                })

        # One settlement row per player, even when they win several side pots.
        totals = {}
        for allocation in allocations:
            pid = allocation["playerId"]
            if pid not in totals:
                totals[pid] = dict(allocation)
            else:
                totals[pid]["amount"] += allocation["amount"]
                if allocation["bestHand"]:
                    totals[pid].update(bestHand=allocation["bestHand"], handRank=allocation["handRank"], reason=allocation["reason"])
        for pid, allocation in totals.items():
            allocation["stackChange"] = self._get_player(pid).stack - self.hand_start_stacks[pid]
        self._allocations = list(totals.values())
        return self._allocations

    # ──────────────────────────────────────────
    # 5. 工具方法
    # ──────────────────────────────────────────
    def active_players(self) -> List[Player]:
        return [p for p in self.players if p.status == PlayerStatus.ACTIVE]

    def non_folded_players(self) -> List[Player]:
        return [p for p in self.players if p.status != PlayerStatus.FOLDED]

    def _get_player(self, player_id: str) -> Optional[Player]:
        return next((p for p in self.players if p.id == player_id), None)

    def get_valid_actions(self, player: Player) -> List[ActionType]:
        """返回玩家当前可以执行的合法行动"""
        if player.status != PlayerStatus.ACTIVE or self.phase in (GamePhase.SHOWDOWN, GamePhase.ENDED):
            return []
        actions = [ActionType.FOLD]
        to_call = max(0, self.street_bet - player.current_bet)
        actions.append(ActionType.CHECK if to_call == 0 else ActionType.CALL)
        opponents_can_bet = any(p.id != player.id for p in self.active_players())
        if player.stack > 0:
            if self.can_raise(player) and opponents_can_bet and player.stack + player.current_bet >= self.minimum_raise_to():
                actions.append(ActionType.RAISE)
            if player.stack <= to_call or (self.can_raise(player) and opponents_can_bet):
                actions.append(ActionType.ALLIN)
        return actions

    def reset_for_new_hand(self):
        """重置游戏状态以开始新的一手牌"""
        # 记录本手开始前的筹码
        self.hand_start_stacks = {p.id: p.stack for p in self.players}

        # 清空所有玩家的手牌和下注
        for player in self.players:
            player.hole_cards = []
            player.current_bet = 0.0
            # 只有还有筹码的玩家才能继续游戏
            if player.stack > 0:
                player.status = PlayerStatus.ACTIVE
            else:
                player.status = PlayerStatus.FOLDED

        # 重置游戏状态
        self.community_cards = []
        self.pot = 0.0
        self.street_bet = 0.0
        self.phase = GamePhase.PRE_FLOP
        self.action_history = []
        self.pending_actors = set()
        self.last_action_phase = ""
        self.speech_history = []
        # 重置总下注跟踪
        self.total_bets = {p.id: 0.0 for p in self.players}

        # 轮转庄家位置
        self.dealer_idx = self._next_live_seat(self.dealer_idx)
        self.hand_player_ids = {p.id for p in self.players if p.stack > 0}
        self.last_full_raise = self.big_blind
        self.acted_bets = {}
        self.last_actor_idx = None
        self.betting_started = False
        self._allocations = None
        self.pots = []

    def get_state_snapshot(self, viewer_id: Optional[str] = None) -> dict:
        """返回当前游戏状态的快照（用于前端和 Prompt 构建）"""
        return {
            "phase": self.phase.value,
            "pot": self.pot,
            "streetBet": self.street_bet,
            "street_bet": self.street_bet,  # snake_case for agent_engine compatibility
            "communityCards": [{"rank": c.rank, "suit": c.suit} for c in self.community_cards],
            "dealerIndex": self.dealer_idx,
            "players": [
                {
                    "id": p.id,
                    "name": p.name,
                    "stack": p.stack,
                    "currentBet": p.current_bet,
                    "status": p.status.value,
                    "position": p.position,
                    "isHuman": p.player_type == "human",
                    "holeCards": [
                        {"rank": c.rank, "suit": c.suit} for c in p.hole_cards
                    ] if p.id == viewer_id or (
                        self.phase == GamePhase.SHOWDOWN and p.status != PlayerStatus.FOLDED
                    ) else [],
                }
                for p in self.players
            ],
        }
