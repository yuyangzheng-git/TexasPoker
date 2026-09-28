"""
Monte Carlo 剩余牌堆测试：
已知牌（手牌 + 公共牌）不可再次被抽到
"""
import sys
sys.path.insert(0, "../backend")
from hand_evaluator import Card
from monte_carlo_equity import MonteCarloEquityCalculator


class TestRemainingDeck:
    def test_card_equality_by_rank_and_suit(self):
        assert Card(14, 0) == Card(14, 0)
        assert Card(14, 0) != Card(14, 1)
        assert Card(14, 0) != Card(13, 0)
        assert hash(Card(14, 0)) == hash(Card(14, 0))
        # 相同 (rank, suit) 的牌在 set 中只保留一张
        cards = [Card(14, 0), Card(14, 0), Card(13, 1)]
        assert len(set(cards)) == 2

    def test_five_known_cards_leave_47(self):
        known = [Card(14, 0), Card(13, 0), Card(12, 0), Card(11, 0), Card(10, 0)]
        deck = MonteCarloEquityCalculator.build_remaining_deck(known)
        assert len(deck) == 47

    def test_seven_known_cards_leave_45(self):
        known = [
            Card(14, 0), Card(13, 0),  # 手牌
            Card(12, 0), Card(11, 0), Card(10, 0), Card(9, 0), Card(8, 0),  # 公共牌
        ]
        deck = MonteCarloEquityCalculator.build_remaining_deck(known)
        assert len(deck) == 45

    def test_known_cards_never_reappear(self):
        known = [Card(14, 0), Card(13, 0), Card(12, 0), Card(11, 0), Card(10, 0)]
        deck = MonteCarloEquityCalculator.build_remaining_deck(known)
        deck_set = set(deck)
        for card in known:
            assert card not in deck_set, f"已知牌 {card} 再次出现在剩余牌堆"

    def test_full_deck_without_known(self):
        deck = MonteCarloEquityCalculator.build_remaining_deck([])
        assert len(deck) == 52
        assert len(set(deck)) == 52  # 无重复

    def test_equity_simulation_uses_no_duplicate_cards(self):
        """已知 5 张牌时模拟应基于 47 张牌；大量模拟不报错且结果在 0-1"""
        hole = [Card(14, 0), Card(13, 0)]
        community = [Card(12, 0), Card(11, 0), Card(10, 0)]
        equity = MonteCarloEquityCalculator.calculate_equity(
            hole, community, 2, simulations=300
        )
        assert 0.0 <= equity <= 1.0
