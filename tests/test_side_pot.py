"""
边池和下注轮算法测试
"""
import sys
sys.path.insert(0, "../backend")
from game_engine import GameEngine, Player, Action, ActionType, PlayerStatus


def make_game():
    players = [
        Player(id="p1", name="Alice", stack=1000.0),
        Player(id="p2", name="Bob",   stack=500.0),
        Player(id="p3", name="Carol", stack=200.0),
    ]
    return GameEngine(players, min_bet=10.0)


class TestSidePots:
    def test_no_allin_single_pot(self):
        """没有 all-in 时只有一个主池"""
        game = make_game()
        game.deal_hole_cards()
        game.post_blinds()
        # 所有人下注相同
        for p in game.players:
            p.current_bet = 100.0
        pots = game.calculate_side_pots()
        assert len(pots) == 1

    def test_allin_creates_side_pot(self):
        """Carol all-in 200，应该产生主池和边池"""
        game = make_game()
        game.deal_hole_cards()
        # 手动模拟下注
        game.players[0].current_bet = 500.0
        game.players[1].current_bet = 500.0
        game.players[2].current_bet = 200.0
        game.players[2].status = PlayerStatus.ALLIN
        game.pot = 1200.0

        pots = game.calculate_side_pots()
        assert len(pots) == 2
        # 主池：200*3=600
        assert pots[0].amount == 600.0
        assert len(pots[0].eligible_player_ids) == 3
        # 边池：300*2=600
        assert pots[1].amount == 600.0
        assert len(pots[1].eligible_player_ids) == 2


class TestBettingRound:
    def test_fold_removes_player(self):
        game = make_game()
        game.deal_hole_cards()
        game.post_blinds()
        action = Action(player_id="p1", type=ActionType.FOLD, amount=0.0)
        game.process_action(action)
        assert game.players[0].status == PlayerStatus.FOLDED

    def test_call_updates_pot(self):
        game = make_game()
        game.deal_hole_cards()
        game.post_blinds()
        initial_pot = game.pot
        p = next(p for p in game.players if p.status == PlayerStatus.ACTIVE)
        call_amount = game.street_bet - p.current_bet
        if call_amount > 0:
            action = Action(player_id=p.id, type=ActionType.CALL, amount=call_amount)
            game.process_action(action)
            assert game.pot >= initial_pot

    def test_invalid_check_corrected(self):
        """当有 street_bet 时 check 应被自动修正为 call"""
        game = make_game()
        game.deal_hole_cards()
        game.street_bet = 50.0
        p = game.players[0]
        p.current_bet = 0.0
        p.status = PlayerStatus.ACTIVE
        action = Action(player_id=p.id, type=ActionType.CHECK, amount=0.0)
        result = game.process_action(action)
        # 应自动处理（call 50）
        assert game.pot > 0


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])
