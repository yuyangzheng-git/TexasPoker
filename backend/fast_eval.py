"""
快速 7 张牌评估器（纯 Python，无第三方依赖）

用于蒙特卡洛胜率模拟。现有 HandEvaluator 每次枚举 C(7,5)=21 个组合，
这里改为一次扫描点数/花色计数，速度约快 10 倍。

返回的分数与 HandEvaluator.evaluate_best_hand 完全一致（测试中逐手核对），
因此两者可以互换比较，不会出现排序分歧。

牌用整数表示：code = rank * 4 + suit，rank 为 2..14（A=14），suit 为 0..3。
"""
from typing import Iterable, List, Sequence

from hand_evaluator import Card, HandRank

# 牌型基础分（与 HandEvaluator 一致）
_ONE_PAIR = int(HandRank.ONE_PAIR)
_TWO_PAIR = int(HandRank.TWO_PAIR)
_TRIPS = int(HandRank.THREE_OF_A_KIND)
_STRAIGHT = int(HandRank.STRAIGHT)
_FLUSH = int(HandRank.FLUSH)
_FULL_HOUSE = int(HandRank.FULL_HOUSE)
_QUADS = int(HandRank.FOUR_OF_A_KIND)
_STRAIGHT_FLUSH = int(HandRank.STRAIGHT_FLUSH)
_ROYAL = int(HandRank.ROYAL_FLUSH)

FULL_DECK: List[int] = [r * 4 + s for r in range(2, 15) for s in range(4)]


def card_code(card: Card) -> int:
    return card.rank * 4 + card.suit


def codes(cards: Iterable[Card]) -> List[int]:
    return [c.rank * 4 + c.suit for c in cards]


def code_to_card(code: int) -> Card:
    return Card(code >> 2, code & 3)


def _tiebreak(digits: Sequence[int]) -> int:
    value = 0
    for d in digits:
        value = value * 15 + (d - 1)
    return value


def _straight_high(mask: int) -> int:
    """mask 的第 r 位表示点数 r 存在；返回最高顺子的顶张，没有则 0。"""
    for high in range(14, 5, -1):
        need = 0b11111 << (high - 4)
        if mask & need == need:
            return high
    # A-2-3-4-5
    if mask & 0b111100 == 0b111100 and mask & (1 << 14):
        return 5
    return 0


def evaluate7(cards: Sequence[int]) -> int:
    """评估 5~7 张牌（整数编码）的最佳 5 张牌型分数。"""
    rank_count = [0] * 15
    suit_count = [0, 0, 0, 0]
    suit_masks = [0, 0, 0, 0]
    mask = 0
    for c in cards:
        r = c >> 2
        s = c & 3
        rank_count[r] += 1
        suit_count[s] += 1
        suit_masks[s] |= 1 << r
        mask |= 1 << r

    # 同花 / 同花顺
    flush_suit = -1
    for s in range(4):
        if suit_count[s] >= 5:
            flush_suit = s
            break
    if flush_suit >= 0:
        fmask = suit_masks[flush_suit]
        sf_high = _straight_high(fmask)
        if sf_high:
            return _ROYAL if sf_high == 14 else _STRAIGHT_FLUSH + sf_high

    quads = trips = 0
    trips2 = 0
    pairs: List[int] = []
    singles: List[int] = []
    for r in range(14, 1, -1):
        n = rank_count[r]
        if n == 4:
            quads = r
        elif n == 3:
            if trips == 0:
                trips = r
            elif trips2 == 0:
                trips2 = r
        elif n == 2:
            pairs.append(r)
        elif n == 1:
            singles.append(r)

    if quads:
        kicker = 0
        for r in range(14, 1, -1):
            if r != quads and rank_count[r]:
                kicker = r
                break
        return _QUADS + quads * 100 + kicker

    if trips and (trips2 or pairs):
        pair = max(trips2, pairs[0] if pairs else 0)
        return _FULL_HOUSE + trips * 100 + pair

    if flush_suit >= 0:
        fmask = suit_masks[flush_suit]
        top = [r for r in range(14, 1, -1) if fmask & (1 << r)][:5]
        return _FLUSH + _tiebreak(top)

    st_high = _straight_high(mask)
    if st_high:
        return _STRAIGHT + st_high

    if trips:
        kick = [r for r in range(14, 1, -1) if rank_count[r] and r != trips][:2]
        return _TRIPS + _tiebreak([trips] + kick)

    if len(pairs) >= 2:
        p1, p2 = pairs[0], pairs[1]
        kicker = 0
        for r in range(14, 1, -1):
            if rank_count[r] and r != p1 and r != p2:
                kicker = r
                break
        return _TWO_PAIR + _tiebreak([p1, p2, kicker])

    if pairs:
        p = pairs[0]
        kick = [r for r in range(14, 1, -1) if rank_count[r] and r != p][:3]
        return _ONE_PAIR + _tiebreak([p] + kick)

    return _tiebreak(singles[:5])


def evaluate_cards(hole: Sequence[Card], board: Sequence[Card]) -> int:
    return evaluate7(codes(list(hole) + list(board)))


# ──────────────────────────────────────────
# 牌面结构 / 成牌类别（供范围收窄和决策解释使用）
# ──────────────────────────────────────────

MADE_CATEGORY_NAMES = {
    0: "空气",
    1: "听牌",
    2: "弱对子",
    3: "中等对子",
    4: "顶对/超对",
    5: "两对",
    6: "三条及以上",
}


def made_category(hole: Sequence[int], board: Sequence[int]) -> int:
    """
    粗粒度的成牌强度类别（0~6），只在翻后使用。
    类别只看"手牌对牌力的贡献"，公共牌自带的对子不算成手牌。
    """
    if len(board) < 3:
        return 0
    score = evaluate7(list(hole) + list(board))
    board_score = evaluate7(board) if len(board) >= 5 else -1
    if score >= _TRIPS:
        # 公共牌本身就是三条/顺子等，手牌没有贡献时降级
        if board_score >= 0 and score == board_score:
            return 2
        return 6
    if score >= _TWO_PAIR:
        board_ranks = [c >> 2 for c in board]
        hole_ranks = [c >> 2 for c in hole]
        # 两对中至少一对由手牌组成才算真两对
        if any(r in board_ranks for r in hole_ranks) or hole_ranks[0] == hole_ranks[1]:
            # 公共牌已有一对 + 手牌配上一张 = 实际是"一对"级别
            paired_board = len(set(board_ranks)) < len(board_ranks)
            if paired_board and hole_ranks[0] != hole_ranks[1]:
                return _pair_category(hole_ranks, board_ranks)
            return 5
        return _draw_or_air(hole, board)
    if score >= _ONE_PAIR:
        hole_ranks = [c >> 2 for c in hole]
        board_ranks = [c >> 2 for c in board]
        if hole_ranks[0] != hole_ranks[1] and not any(r in board_ranks for r in hole_ranks):
            # 对子来自公共牌
            return _draw_or_air(hole, board)
        return _pair_category(hole_ranks, board_ranks)
    return _draw_or_air(hole, board)


def _pair_category(hole_ranks: List[int], board_ranks: List[int]) -> int:
    top = max(board_ranks)
    if hole_ranks[0] == hole_ranks[1]:
        if hole_ranks[0] > top:
            return 4  # 超对
        return 3 if hole_ranks[0] > sorted(board_ranks)[len(board_ranks) // 2] else 2
    paired = [r for r in hole_ranks if r in board_ranks]
    r = max(paired)
    if r == top:
        return 4  # 顶对
    second = sorted(set(board_ranks), reverse=True)
    if len(second) > 1 and r == second[1]:
        return 3
    return 2


def _draw_or_air(hole: Sequence[int], board: Sequence[int]) -> int:
    if len(board) >= 5:
        return 0
    cards = list(hole) + list(board)
    suit_count = [0, 0, 0, 0]
    for c in cards:
        suit_count[c & 3] += 1
    hole_suits = [c & 3 for c in hole]
    for s in range(4):
        if suit_count[s] == 4 and s in hole_suits:
            return 1  # 同花听牌
    mask = 0
    for c in cards:
        mask |= 1 << (c >> 2)
    if mask & (1 << 14):
        mask |= 1 << 1
    hole_mask = 0
    for c in hole:
        hole_mask |= 1 << (c >> 2)
    for low in range(1, 11):
        window = 0b11111 << low
        present = mask & window
        if bin(present).count("1") == 4 and present & hole_mask:
            return 1  # 两头/卡顺听牌
    return 0
