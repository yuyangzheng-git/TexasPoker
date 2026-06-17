"""
手牌评估算法单元测试
"""
import sys
sys.path.insert(0, "../backend")
from hand_evaluator import Card, HandEvaluator, HandRank
import pytest


def make_cards(*specs):
    """辅助函数：快速创建牌组，spec格式如 (14,0) = A♠"""
    return [Card(rank, suit) for rank, suit in specs]


class TestHandEvaluator:

    def test_royal_flush(self):
        hand = make_cards((14,0),(13,0),(12,0),(11,0),(10,0))  # A-K-Q-J-T 同花
        score, _ = HandEvaluator.evaluate_5_cards(hand)
        assert score == HandRank.ROYAL_FLUSH

    def test_straight_flush(self):
        hand = make_cards((9,1),(8,1),(7,1),(6,1),(5,1))
        score, _ = HandEvaluator.evaluate_5_cards(hand)
        assert HandRank.STRAIGHT_FLUSH <= score < HandRank.ROYAL_FLUSH

    def test_four_of_a_kind(self):
        hand = make_cards((14,0),(14,1),(14,2),(14,3),(5,0))
        score, _ = HandEvaluator.evaluate_5_cards(hand)
        assert HandRank.FOUR_OF_A_KIND <= score < HandRank.STRAIGHT_FLUSH

    def test_full_house(self):
        hand = make_cards((8,0),(8,1),(8,2),(5,0),(5,1))
        score, _ = HandEvaluator.evaluate_5_cards(hand)
        assert HandRank.FULL_HOUSE <= score < HandRank.FOUR_OF_A_KIND

    def test_flush(self):
        hand = make_cards((14,2),(10,2),(7,2),(4,2),(2,2))
        score, _ = HandEvaluator.evaluate_5_cards(hand)
        assert HandRank.FLUSH <= score < HandRank.FULL_HOUSE

    def test_straight(self):
        hand = make_cards((9,0),(8,1),(7,2),(6,3),(5,0))
        score, _ = HandEvaluator.evaluate_5_cards(hand)
        assert HandRank.STRAIGHT <= score < HandRank.FLUSH

    def test_wheel_straight(self):
        """A-2-3-4-5 是最低顺子"""
        hand = make_cards((14,0),(2,1),(3,2),(4,3),(5,0))
        score, _ = HandEvaluator.evaluate_5_cards(hand)
        assert HandRank.STRAIGHT <= score < HandRank.FLUSH

    def test_three_of_a_kind(self):
        hand = make_cards((7,0),(7,1),(7,2),(4,3),(2,0))
        score, _ = HandEvaluator.evaluate_5_cards(hand)
        assert HandRank.THREE_OF_A_KIND <= score < HandRank.STRAIGHT

    def test_two_pair(self):
        hand = make_cards((9,0),(9,1),(5,2),(5,3),(2,0))
        score, _ = HandEvaluator.evaluate_5_cards(hand)
        assert HandRank.TWO_PAIR <= score < HandRank.THREE_OF_A_KIND

    def test_one_pair(self):
        hand = make_cards((10,0),(10,1),(8,2),(5,3),(2,0))
        score, _ = HandEvaluator.evaluate_5_cards(hand)
        assert HandRank.ONE_PAIR <= score < HandRank.TWO_PAIR

    def test_high_card(self):
        hand = make_cards((14,0),(10,1),(7,2),(4,3),(2,0))
        score, _ = HandEvaluator.evaluate_5_cards(hand)
        assert HandRank.HIGH_CARD <= score < HandRank.ONE_PAIR

    def test_best_hand_from_7(self):
        """从7张里找最强5张：应该找到同花顺"""
        hole = make_cards((14,0),(13,0))    # A♠ K♠
        community = make_cards((12,0),(11,0),(10,0),(9,1),(8,2))  # Q♠ J♠ T♠ 9♥ 8♦
        score, best = HandEvaluator.evaluate_best_hand(hole, community)
        assert score >= HandRank.ROYAL_FLUSH
        assert len(best) == 5

    def test_kicker_matters(self):
        """两个一对，kicker更高的应该赢"""
        hand_ak = make_cards((14,0),(14,1),(13,2),(12,3),(10,0))  # 一对A + KQ
        hand_a9 = make_cards((14,0),(14,1),(9,2),(8,3),(7,0))     # 一对A + 987
        s1, _ = HandEvaluator.evaluate_5_cards(hand_ak)
        s2, _ = HandEvaluator.evaluate_5_cards(hand_a9)
        assert s1 > s2


class TestMonteCarlo:
    def test_equity_range(self):
        """胜率应在 0-1 之间"""
        from monte_carlo_equity import MonteCarloEquityCalculator
        hole = [Card(14, 0), Card(13, 0)]  # AK suited
        equity = MonteCarloEquityCalculator.calculate_equity(
            hole, [], 2, simulations=200
        )
        assert 0.0 <= equity <= 1.0

    def test_strong_hand_higher_equity(self):
        """AA 胜率应高于 72o"""
        from monte_carlo_equity import MonteCarloEquityCalculator
        aa = [Card(14, 0), Card(14, 1)]
        o72 = [Card(7, 0), Card(2, 1)]
        eq_aa = MonteCarloEquityCalculator.calculate_equity(aa, [], 1, simulations=500)
        eq_72 = MonteCarloEquityCalculator.calculate_equity(o72, [], 1, simulations=500)
        assert eq_aa > eq_72


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
