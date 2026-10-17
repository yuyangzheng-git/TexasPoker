"""
对手范围推断 + 基于范围的蒙特卡洛胜率

旧实现假设每个对手持有"任意两张牌"，所以对手加注到很大时 AI 仍高估自己。
这里根据对手的公开行动线给每一种可能的底牌组合一个权重：

翻牌前：按行动类型给出范围宽度（开池 / 跟注 / 3bet / 4bet / 平跟 / 大盲过牌），
        并用该对手的实际 VPIP/PFR 统计做缩放（松的对手范围更宽）。
        被动行动（跟注、平跟）会"封顶"——最强的手牌大概率会加注，所以权重降低。
翻牌后：每条街按对手最激进的行动（下注/加注、跟注、过牌）和该手牌在当时牌面上的
        成牌类别重新加权，例如下注后空气牌权重下降，听牌和成牌保持。
        对手的诈唬倾向用其激进度 AF 调节。

只使用公开信息（行动、公共牌、统计），不读取任何对手底牌。
"""
import math
import random
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence, Tuple

from fast_eval import FULL_DECK, codes, evaluate7, made_category
from game_engine import ActionType, GameEngine, GamePhase, Player
from preflop_ranges import percentile_of_codes

# 6~9 人桌各位置的默认开池宽度（占全部起手牌的比例）
DEFAULT_OPEN = {"UTG": 0.14, "EP": 0.15, "MP": 0.18, "LJ": 0.2, "HJ": 0.22, "CO": 0.27,
                "BTN": 0.42, "SB": 0.36, "BB": 0.16, "BTN/SB": 0.6, "": 0.22}

# 翻后：行动 × 成牌类别 → 权重（类别见 fast_eval.MADE_CATEGORY_NAMES）
#            空气  听牌  弱对  中对  顶对  两对  三条+
_BET_W =   [0.22, 0.75, 0.40, 0.70, 1.00, 1.00, 1.00]
_CALL_W =  [0.12, 0.95, 0.65, 1.00, 1.00, 0.85, 0.65]
_CHECK_W = [1.00, 0.85, 1.00, 0.95, 0.70, 0.50, 0.45]

STREETS = [GamePhase.FLOP.value, GamePhase.TURN.value, GamePhase.RIVER.value]
BOARD_LEN = {GamePhase.FLOP.value: 3, GamePhase.TURN.value: 4, GamePhase.RIVER.value: 5}


@dataclass
class RangeSpec:
    """一个对手的推断范围（可解释）。"""
    player_id: str
    top: float = 1.0          # 翻前：强度百分位 <= top 的手牌
    cap: float = 0.0          # 翻前：最强的 cap 部分被降权（被动行动）
    preflop_label: str = "未知"
    postflop: List[Tuple[str, str]] = field(default_factory=list)  # [(街, bet/call/check)]
    bluffiness: float = 1.0   # 对手诈唬倾向（来自 AF）

    def describe(self) -> str:
        parts = [f"{self.preflop_label}(约前{self.top:.0%})"]
        names = {"bet": "下注", "call": "跟注", "check": "过牌"}
        street_cn = {"flop": "翻牌", "turn": "转牌", "river": "河牌"}
        for street, act in self.postflop:
            parts.append(f"{street_cn.get(street, street)}{names[act]}")
        return "→".join(parts)


def _sigmoid(x: float) -> float:
    if x < -30:
        return 0.0
    if x > 30:
        return 1.0
    return 1.0 / (1.0 + math.exp(-x))


def infer_range(game: GameEngine, opponent: Player, tracker=None) -> RangeSpec:
    """根据本手牌的公开行动历史推断 opponent 的范围。"""
    spec = RangeSpec(player_id=opponent.id)
    stats = tracker.get(opponent.id) if tracker is not None else None

    # 用实际统计缩放默认范围宽度（样本少时先验会把它拉回常规值）
    width_scale = 1.0
    open_scale = 1.0
    if stats is not None and stats.hands >= 6:
        width_scale = min(2.4, max(0.55, stats.vpip / 0.27))
        open_scale = min(2.4, max(0.55, stats.pfr / 0.18))
        spec.bluffiness = min(1.8, max(0.5, stats.af / 1.8))

    big_blind = game.big_blind
    street_bet = big_blind
    raises = 0
    limpers = 0
    acted = False
    street_actions: Dict[str, str] = {}
    current_street = GamePhase.PRE_FLOP.value
    street_level = 0.0

    for act in game.action_history:
        phase = act.phase or GamePhase.PRE_FLOP.value
        if phase != current_street:
            current_street = phase
            street_level = 0.0
        is_me = act.player_id == opponent.id
        if phase == GamePhase.PRE_FLOP.value:
            raising = act.type == ActionType.RAISE or (
                act.type == ActionType.ALLIN and act.amount > street_bet)
            if raising:
                target = act.amount if act.type == ActionType.RAISE else max(act.amount, street_bet * 2)
                if is_me:
                    acted = True
                    if raises == 0:
                        pos = opponent.position or ""
                        base = DEFAULT_OPEN.get(pos, 0.22) * open_scale
                        spec.top, spec.cap, spec.preflop_label = min(0.65, base), 0.0, "开池加注"
                    elif raises == 1:
                        spec.top, spec.cap, spec.preflop_label = min(0.2, 0.065 * open_scale), 0.0, "3bet"
                    else:
                        spec.top, spec.cap, spec.preflop_label = 0.03, 0.0, "4bet+"
                    if act.type == ActionType.ALLIN and raises == 0:
                        spec.top = min(0.3, spec.top * 0.8)
                        spec.preflop_label = "翻前全下"
                raises += 1
                street_bet = max(street_bet, target)
            elif act.type in (ActionType.CALL, ActionType.ALLIN) and is_me:
                acted = True
                if raises == 0:
                    spec.top, spec.cap, spec.preflop_label = min(0.75, 0.45 * width_scale), 0.08, "平跟入池"
                    limpers += 1
                elif raises == 1:
                    wide = 0.20 * width_scale
                    if opponent.position == "BB":
                        wide *= 1.5
                    spec.top, spec.cap, spec.preflop_label = min(0.6, wide), 0.035, "跟注加注"
                elif raises == 2:
                    spec.top, spec.cap, spec.preflop_label = 0.09, 0.012, "跟注3bet"
                else:
                    spec.top, spec.cap, spec.preflop_label = 0.045, 0.0, "跟注4bet"
            elif act.type == ActionType.CHECK and is_me:
                acted = True
                spec.top, spec.cap, spec.preflop_label = 1.0, 0.12, "大盲过牌"
            elif act.type == ActionType.CALL and raises == 0:
                limpers += 1
        else:
            if act.type == ActionType.RAISE or (act.type == ActionType.ALLIN and act.amount > street_level):
                street_level = max(street_level, act.amount)
                if is_me:
                    street_actions[phase] = "bet"
            elif is_me and act.type in (ActionType.CALL, ActionType.ALLIN):
                if street_actions.get(phase) != "bet":
                    street_actions[phase] = "call"
            elif is_me and act.type == ActionType.CHECK:
                street_actions.setdefault(phase, "check")

    if not acted:
        # 例如大盲尚未行动、或盲注位直接进入翻后
        spec.top, spec.cap, spec.preflop_label = 1.0, 0.0, "未主动行动"
    spec.postflop = [(s, street_actions[s]) for s in STREETS if s in street_actions]
    return spec


def _preflop_weight(p: float, spec: RangeSpec) -> float:
    # 边界宽度与范围大小成比例：窄范围边界清晰，宽范围边界平滑
    width = max(0.006, 0.16 * spec.top)
    w = _sigmoid((spec.top - p) / width)
    if spec.cap > 0:
        w *= 1.0 - 0.75 * _sigmoid((spec.cap - p) / 0.012)
    return w


def range_weights(spec: RangeSpec, board: Sequence[int], dead: Sequence[int]) -> Tuple[List[Tuple[int, int]], List[float]]:
    """返回 (组合列表, 权重列表)，已剔除与 dead 冲突的组合。"""
    dead_set = set(dead)
    live = [c for c in FULL_DECK if c not in dead_set]
    combos: List[Tuple[int, int]] = []
    weights: List[float] = []
    boards_by_street = {s: list(board[:BOARD_LEN[s]]) for s, _ in spec.postflop if len(board) >= BOARD_LEN[s]}
    bluff = spec.bluffiness
    n = len(live)
    for i in range(n):
        a = live[i]
        for j in range(i + 1, n):
            b = live[j]
            w = _preflop_weight(percentile_of_codes(a, b), spec)
            if w < 0.003:
                continue
            for street, act in spec.postflop:
                sboard = boards_by_street.get(street)
                if not sboard:
                    continue
                cat = made_category((a, b), sboard)
                if act == "bet":
                    f = _BET_W[cat]
                    if cat == 0:
                        f = min(1.0, f * bluff)
                elif act == "call":
                    f = _CALL_W[cat]
                else:
                    f = _CHECK_W[cat]
                w *= f
                if w < 0.003:
                    break
            if w >= 0.003:
                combos.append((a, b))
                weights.append(w)
    return combos, weights


def range_equity(
    hero_cards: Sequence,
    board_cards: Sequence,
    specs: List[RangeSpec],
    simulations: int = 600,
    rng: Optional[random.Random] = None,
) -> dict:
    """
    hero 对多个对手范围的胜率（平局按人数平分）。
    返回 {"equity", "equity_random", "range_size"}，equity_random 为旧方法（任意两张）的结果，
    便于在思考过程中对比"考虑范围前后"的差别。
    """
    rng = rng or random
    hero = codes(hero_cards)
    board = codes(board_cards)
    dead = hero + board
    tables = []
    for spec in specs:
        combos, weights = range_weights(spec, board, dead)
        if not combos:
            combos, weights = range_weights(RangeSpec(spec.player_id), board, dead)
        cum = []
        acc = 0.0
        for w in weights:
            acc += w
            cum.append(acc)
        tables.append((combos, cum, acc))

    need = 5 - len(board)
    deck = [c for c in FULL_DECK if c not in set(dead)]
    wins = 0.0
    wins_random = 0.0
    done = 0
    for _ in range(simulations):
        used = set(dead)
        opp_hands = []
        ok = True
        for combos, cum, total in tables:
            for _try in range(30):
                x = rng.random() * total
                lo, hi = 0, len(cum) - 1
                while lo < hi:
                    mid = (lo + hi) // 2
                    if cum[mid] < x:
                        lo = mid + 1
                    else:
                        hi = mid
                h = combos[lo]
                if h[0] not in used and h[1] not in used:
                    used.add(h[0])
                    used.add(h[1])
                    opp_hands.append(h)
                    break
            else:
                ok = False
                break
        if not ok:
            continue
        rest = [c for c in deck if c not in used]
        runout = rng.sample(rest, need) if need else []
        full_board = board + runout
        me = evaluate7(hero + full_board)
        best = -1
        ties = 0
        for h in opp_hands:
            s = evaluate7([h[0], h[1]] + full_board)
            if s > best:
                best, ties = s, (1 if s == me else 0)
            elif s == best and s == me:
                ties += 1
        if me > best:
            wins += 1
        elif me == best:
            wins += 1.0 / (1 + ties)
        # 对照：同一条牌面下，对手换成随机手牌
        rnd = rng.sample(rest, 2 * len(opp_hands) + need)
        rb = board + rnd[:need]
        me2 = evaluate7(hero + rb)
        best2, ties2 = -1, 0
        for k in range(len(opp_hands)):
            s = evaluate7(rnd[need + 2 * k: need + 2 * k + 2] + rb)
            if s > best2:
                best2, ties2 = s, (1 if s == me2 else 0)
            elif s == best2 and s == me2:
                ties2 += 1
        if me2 > best2:
            wins_random += 1
        elif me2 == best2:
            wins_random += 1.0 / (1 + ties2)
        done += 1
    if done == 0:
        return {"equity": 0.5, "equity_random": 0.5, "range_size": 0}
    return {
        "equity": wins / done,
        "equity_random": wins_random / done,
        "range_size": sum(len(t[0]) for t in tables),
    }
