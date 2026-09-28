"""
手牌评估算法
从7张牌中找出最强的5张组合
"""
from enum import IntEnum
from typing import List, Tuple

class CardRank(IntEnum):
    """牌的点数 (1-13, 1=A, 13=K)"""
    ACE = 14
    KING = 13
    QUEEN = 12
    JACK = 11
    TEN = 10

class CardSuit(IntEnum):
    """牌的花色"""
    SPADE = 0
    HEART = 1
    DIAMOND = 2
    CLUB = 3

class HandRank(IntEnum):
    """手牌牌型排名

    牌型基础分值间隔 1,000,000，保证任何 kicker 编码（< 1,000,000）
    都不会跨越到更高牌型，从而保证分数全序正确。
    """
    HIGH_CARD = 0
    ONE_PAIR = 1_000_000
    TWO_PAIR = 2_000_000
    THREE_OF_A_KIND = 3_000_000
    STRAIGHT = 4_000_000
    FLUSH = 5_000_000
    FULL_HOUSE = 6_000_000
    FOUR_OF_A_KIND = 7_000_000
    STRAIGHT_FLUSH = 8_000_000
    ROYAL_FLUSH = 9_000_000


class Card:
    """扑克牌类"""
    def __init__(self, rank: int, suit: int):
        self.rank = rank  # 1-13, 1=A, 13=K
        self.suit = suit  # 0-3

    def __eq__(self, other):
        if not isinstance(other, Card):
            return NotImplemented
        return self.rank == other.rank and self.suit == other.suit

    def __hash__(self):
        return hash((self.rank, self.suit))

    def __repr__(self):
        rank_names = {1: 'A', 11: 'J', 12: 'Q', 13: 'K'}
        suit_names = {0: '♠', 1: '♥', 2: '♦', 3: '♣'}
        rank_str = rank_names.get(self.rank, str(self.rank))
        return f"{rank_str}{suit_names[self.suit]}"

    def to_string(self) -> str:
        """转换为字符串格式，如 'As', '2h'"""
        rank_names = {14: 'A', 2: '2', 3: '3', 4: '4', 5: '5',
                      6: '6', 7: '7', 8: '8', 9: '9', 10: 'T',
                      11: 'J', 12: 'Q', 13: 'K'}
        suit_names = {0: 's', 1: 'h', 2: 'd', 3: 'c'}
        return f"{rank_names[self.rank]}{suit_names[self.suit]}"


class HandEvaluator:
    """德州扑克手牌评估器"""

    @staticmethod
    def _tiebreak(digits: List[int]) -> int:
        """将排序后的点数列表编码为 0-999,999 内的唯一值

        使用 15 进制（点数 2-14 → 数字 1-13），最大 5 位：
        13 * (15^4 + 15^3 + 15^2 + 15 + 1) = 542,581 < 1,000,000
        """
        value = 0
        for d in digits:
            value = value * 15 + (d - 1)
        return value

    @staticmethod
    def evaluate_5_cards(cards: List[Card]) -> Tuple[int, List[int]]:
        """
        评估单一5张手牌组合
        返回 (总分, 拆分列表用于对比)

        总分结构：
        - 高位：牌型基础分值（间隔 1,000,000）
        - 低位：kicker 的 15 进制编码，保证同牌型内全序正确
        """
        if len(cards) != 5:
            raise ValueError("Must evaluate exactly 5 cards")

        # 提取点数和花色
        ranks = sorted([c.rank for c in cards], reverse=True)
        suits = [c.suit for c in cards]

        # 检测牌型
        is_flush = len(set(suits)) == 1
        is_straight, straight_high = HandEvaluator._check_straight(ranks)
        rank_counts = HandEvaluator._count_ranks(ranks)

        # 根据牌型返回分值
        if is_straight and is_flush:
            # 同花顺或皇家同花顺
            if straight_high == 14:  # A-K-Q-J-T
                return (HandRank.ROYAL_FLUSH, [14])
            return (HandRank.STRAIGHT_FLUSH + straight_high, [straight_high])

        if 4 in rank_counts.values():
            # 四条
            quad_rank = [r for r, c in rank_counts.items() if c == 4][0]
            kicker = [r for r in ranks if r != quad_rank]
            return (HandRank.FOUR_OF_A_KIND + quad_rank * 100 + kicker[0],
                    [quad_rank, kicker[0]])

        if 3 in rank_counts.values() and 2 in rank_counts.values():
            # 葫芦
            trip_rank = [r for r, c in rank_counts.items() if c == 3][0]
            pair_rank = [r for r, c in rank_counts.items() if c == 2][0]
            return (HandRank.FULL_HOUSE + trip_rank * 100 + pair_rank,
                    [trip_rank, pair_rank])

        if is_flush:
            # 同花
            return (HandRank.FLUSH + HandEvaluator._tiebreak(ranks), ranks)

        if is_straight:
            # 顺子
            return (HandRank.STRAIGHT + straight_high, [straight_high])

        if 3 in rank_counts.values():
            # 三条
            trip_rank = [r for r, c in rank_counts.items() if c == 3][0]
            kickers = sorted([r for r in ranks if r != trip_rank], reverse=True)
            return (HandRank.THREE_OF_A_KIND + HandEvaluator._tiebreak([trip_rank] + kickers),
                    [trip_rank] + kickers)

        pairs = sorted([r for r, c in rank_counts.items() if c == 2], reverse=True)
        if len(pairs) == 2:
            # 两对
            kicker = [r for r in ranks if r not in pairs][0]
            return (HandRank.TWO_PAIR + HandEvaluator._tiebreak([pairs[0], pairs[1], kicker]),
                    [pairs[0], pairs[1], kicker])

        if len(pairs) == 1:
            # 一对
            pair_rank = pairs[0]
            kickers = sorted([r for r in ranks if r != pair_rank], reverse=True)
            return (HandRank.ONE_PAIR + HandEvaluator._tiebreak([pair_rank] + kickers),
                    [pair_rank] + kickers)

        # 高牌
        return (HandRank.HIGH_CARD + HandEvaluator._tiebreak(ranks), ranks)

    @staticmethod
    def evaluate_best_hand(hole_cards: List[Card], community_cards: List[Card]) -> Tuple[int, List[Card]]:
        """
        从7张牌（2张手牌 + 5张公共牌）中找出最强的5张组合
        使用 C(7,5)=21 组合枚举法

        返回 (总分, 最强5张牌)
        """
        if len(hole_cards) != 2:
            raise ValueError("Must have exactly 2 hole cards")

        all_cards = hole_cards + community_cards
        best_score = -1
        best_hand = None

        # 枚举所有 C(7,5)=21 种组合
        from itertools import combinations
        for combo in combinations(all_cards, 5):
            score, _ = HandEvaluator.evaluate_5_cards(list(combo))
            if score > best_score:
                best_score = score
                best_hand = list(combo)

        return best_score, best_hand

    @staticmethod
    def _check_straight(sorted_ranks: List[int]) -> Tuple[bool, int]:
        """检测是否为顺子，返回 (是否顺子, 最高牌)"""
        # 正常顺子检查
        if sorted_ranks == list(range(sorted_ranks[0], sorted_ranks[0] - 5, -1)):
            return True, sorted_ranks[0]

        # 特殊情况：A-2-3-4-5（轮子，wheel）
        if sorted_ranks == [14, 5, 4, 3, 2]:
            return True, 5  # 在轮子中，5是最高的

        return False, 0

    @staticmethod
    def _count_ranks(ranks: List[int]) -> dict:
        """统计每个点数出现的次数"""
        counts = {}
        for r in ranks:
            counts[r] = counts.get(r, 0) + 1
        return counts

    @staticmethod
    def _flush_score(ranks: List[int]) -> int:
        """计算同花的分值 (用最高牌作为附加值)"""
        return ranks[0] * 10 + ranks[1]

    @staticmethod
    def _high_card_score(ranks: List[int]) -> int:
        """高牌的分值"""
        return ranks[0] * 100 + ranks[1] * 10

    @staticmethod
    def get_hand_rank_name(score: int) -> str:
        """根据分数获取牌型名称"""
        if score >= HandRank.ROYAL_FLUSH:
            return "皇家同花顺"
        elif score >= HandRank.STRAIGHT_FLUSH:
            return "同花顺"
        elif score >= HandRank.FOUR_OF_A_KIND:
            return "四条"
        elif score >= HandRank.FULL_HOUSE:
            return "葫芦"
        elif score >= HandRank.FLUSH:
            return "同花"
        elif score >= HandRank.STRAIGHT:
            return "顺子"
        elif score >= HandRank.THREE_OF_A_KIND:
            return "三条"
        elif score >= HandRank.TWO_PAIR:
            return "两对"
        elif score >= HandRank.ONE_PAIR:
            return "一对"
        else:
            return "高牌"


def compare_hands(hand1_score: int, hand2_score: int) -> int:
    """
    比较两个手牌分值
    返回: 1 表示 hand1 更强，-1 表示 hand2 更强，0 表示平局
    """
    if hand1_score > hand2_score:
        return 1
    elif hand1_score < hand2_score:
        return -1
    else:
        return 0


# 示例使用
if __name__ == "__main__":
    # 创建一副测试牌
    hole = [Card(14, 0), Card(13, 0)]  # A♠ K♠
    community = [
        Card(12, 0), Card(11, 0), Card(10, 0),  # Q♠ J♠ T♠
        Card(9, 1), Card(8, 2)  # 9♥ 8♦
    ]

    score, best_hand = HandEvaluator.evaluate_best_hand(hole, community)
    print(f"Best hand score: {score}")
    print(f"Best hand: {[str(c) for c in best_hand]}")
