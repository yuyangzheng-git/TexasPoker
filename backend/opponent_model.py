"""
公开信息对手统计（HUD 式）

只使用桌上所有人都能看到的行动，因此一张牌桌共享一个 tracker 不会泄露底牌，
真人玩家与 AI 拿到的信息完全一致。

与旧的 OpponentProfile 相比的修正：
- 按"手"计数而不是按"动作"计数：一手牌里多次跟注只算一次 VPIP。
- VPIP / PFR / 3bet 只统计翻牌前；盲注不算主动入池。
- 补上激进度 AF = 翻后(下注+加注)/翻后跟注，旧代码从未更新该值。
- 翻后面对下注的弃牌率、摊牌率（WTSD）。

使用方式（game_session / benchmark）：
    tracker.start_hand(game)               # 发完盲注后
    tracker.observe(game, player_id, type) # 每次 process_action 成功后
    tracker.end_hand(game)                 # 结算后
"""
from dataclasses import dataclass, field
from typing import Dict, Optional

from game_engine import ActionType, GameEngine, GamePhase


@dataclass
class PlayerStats:
    hands: int = 0
    vpip_hands: int = 0
    pfr_hands: int = 0
    three_bet_opps: int = 0
    three_bets: int = 0
    postflop_aggr: int = 0      # 翻后下注/加注次数
    postflop_calls: int = 0
    faced_bets: int = 0         # 翻后面对下注次数
    folds_to_bet: int = 0
    saw_flop: int = 0
    showdowns: int = 0

    # 小样本先验（伪计数），避免 3 手牌就得出 100% 之类的极端值
    PRIOR_HANDS = 8.0

    def _ratio(self, num: float, den: float, prior: float, weight: float) -> float:
        return (num + prior * weight) / (den + weight)

    @property
    def vpip(self) -> float:
        return self._ratio(self.vpip_hands, self.hands, 0.28, self.PRIOR_HANDS)

    @property
    def pfr(self) -> float:
        return self._ratio(self.pfr_hands, self.hands, 0.18, self.PRIOR_HANDS)

    @property
    def three_bet(self) -> float:
        return self._ratio(self.three_bets, self.three_bet_opps, 0.07, 6.0)

    @property
    def af(self) -> float:
        """激进度：翻后 (下注+加注)/跟注，先验约 1.8。"""
        return (self.postflop_aggr + 1.8 * 2) / (self.postflop_calls + 2)

    @property
    def fold_to_bet(self) -> float:
        return self._ratio(self.folds_to_bet, self.faced_bets, 0.45, 6.0)

    @property
    def wtsd(self) -> float:
        return self._ratio(self.showdowns, self.saw_flop, 0.28, 6.0)

    @property
    def reliable(self) -> bool:
        return self.hands >= 15

    def summary(self) -> dict:
        return {
            "hands": self.hands,
            "vpip": round(self.vpip, 3),
            "pfr": round(self.pfr, 3),
            "three_bet": round(self.three_bet, 3),
            "af": round(self.af, 2),
            "fold_to_bet": round(self.fold_to_bet, 3),
            "wtsd": round(self.wtsd, 3),
        }

    def style_label(self) -> str:
        if self.hands < 8:
            return "样本不足"
        loose = self.vpip >= 0.32
        tight = self.vpip <= 0.2
        aggressive = self.af >= 2.2 or (self.pfr / max(self.vpip, 1e-6)) >= 0.7
        passive = self.af <= 1.2 and (self.pfr / max(self.vpip, 1e-6)) < 0.45
        if loose and passive:
            return "跟注站"
        if loose and aggressive:
            return "松凶"
        if tight and aggressive:
            return "紧凶"
        if tight:
            return "紧弱"
        return "常规"


@dataclass
class _HandFlags:
    vpip: bool = False
    pfr: bool = False
    three_bet_opp: bool = False
    three_bet: bool = False
    saw_flop: bool = False


class PublicStatsTracker:
    """一张牌桌一个实例。"""

    def __init__(self):
        self.stats: Dict[str, PlayerStats] = {}
        self._flags: Dict[str, _HandFlags] = {}
        self._phase: Optional[str] = None
        self._street_bet = 0.0
        self._preflop_raises = 0
        self._active = False

    def get(self, player_id: str) -> PlayerStats:
        if player_id not in self.stats:
            self.stats[player_id] = PlayerStats()
        return self.stats[player_id]

    def start_hand(self, game: GameEngine):
        self._flags = {pid: _HandFlags() for pid in game.hand_player_ids}
        for pid in self._flags:
            self.get(pid).hands += 1
        self._phase = GamePhase.PRE_FLOP.value
        self._street_bet = float(game.street_bet)  # 大盲
        self._preflop_raises = 0
        self._active = True

    def observe(self, game: GameEngine, player_id: str, action_type: ActionType):
        """在 process_action 成功后调用。"""
        if not self._active or player_id not in self._flags:
            return
        phase = game.action_history[-1].phase if game.action_history else game.phase.value
        if phase != self._phase:
            # 进入新的下注轮：街注从 0 开始
            self._phase = phase
            self._street_bet = 0.0
            if phase == GamePhase.FLOP.value:
                for pid, fl in self._flags.items():
                    p = game._get_player(pid)
                    if p is not None and (p.status.value != "folded" or pid == player_id):
                        fl.saw_flop = True
        st = self.get(player_id)
        fl = self._flags[player_id]
        player = game._get_player(player_id)
        prev_street_bet = self._street_bet
        increased = game.street_bet > prev_street_bet + 1e-9
        my_bet_after = player.current_bet if player else 0.0
        if action_type in (ActionType.FOLD, ActionType.CHECK):
            facing = prev_street_bet > my_bet_after + 1e-9
        else:
            facing = action_type == ActionType.CALL or (
                action_type == ActionType.ALLIN and not increased and prev_street_bet > 0
            )

        if phase == GamePhase.PRE_FLOP.value:
            if self._preflop_raises == 1:
                fl.three_bet_opp = True
            if action_type in (ActionType.CALL, ActionType.RAISE, ActionType.ALLIN):
                fl.vpip = True
            if increased and action_type in (ActionType.RAISE, ActionType.ALLIN):
                fl.pfr = True
                if self._preflop_raises == 1:
                    fl.three_bet = True
                self._preflop_raises += 1
        else:
            if increased and action_type in (ActionType.RAISE, ActionType.ALLIN):
                st.postflop_aggr += 1
            elif action_type == ActionType.CALL or (action_type == ActionType.ALLIN and not increased):
                st.postflop_calls += 1
            if facing:
                st.faced_bets += 1
                if action_type == ActionType.FOLD:
                    st.folds_to_bet += 1
        self._street_bet = max(self._street_bet, float(game.street_bet))

    def end_hand(self, game: GameEngine):
        if not self._active:
            return
        reached_showdown = len(game.non_folded_players()) > 1
        for pid, fl in self._flags.items():
            st = self.get(pid)
            st.vpip_hands += fl.vpip
            st.pfr_hands += fl.pfr
            st.three_bet_opps += fl.three_bet_opp
            st.three_bets += fl.three_bet
            if fl.saw_flop:
                st.saw_flop += 1
                p = game._get_player(pid)
                if reached_showdown and p is not None and p.status.value != "folded":
                    st.showdowns += 1
        self._active = False
