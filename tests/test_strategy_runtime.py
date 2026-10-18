import random

import pytest

from game_engine import Action, ActionType, GameEngine, GamePhase, Player
from opponent_model import PublicStatsTracker
from range_equity import RangeSpec, infer_range, range_equity
from strategy_agent import StrategyAgent
from hand_evaluator import Card


def table(stack=1000):
    game = GameEngine([Player("a", "A", stack), Player("b", "B", stack)], min_bet=10)
    game.deal_hole_cards()
    game.post_blinds()
    tracker = PublicStatsTracker()
    tracker.start_hand(game)
    return game, tracker


def act(game, tracker, kind, amount=0):
    player = game.get_action_order()[0]
    action = Action(player.id, kind, amount)
    assert game.process_action(action)
    tracker.observe(game, player.id, kind)
    return player, action


@pytest.mark.parametrize("requested", [0, 990, 1000])
def test_allin_history_uses_actual_raise_to_total(requested):
    game, tracker = table()
    raiser, action = act(game, tracker, ActionType.ALLIN, requested)
    assert action.amount == 1000
    assert action.street_bet_before == 20
    assert action.player_bet_before == 10
    other = next(p for p in game.players if p.id != raiser.id)
    agent = StrategyAgent({}, other)
    assert agent._preflop_context(game) == (1, 0, 1000, [raiser.id])
    assert infer_range(game, raiser).preflop_label == "翻前全下"
    act(game, tracker, ActionType.ALLIN)
    assert agent._preflop_aggressor(game) == raiser.id  # All-in call is not a raise.


def test_raise_facing_a_bet_counts_as_faced_bet():
    game, tracker = table()
    act(game, tracker, ActionType.CALL)
    act(game, tracker, ActionType.CHECK)
    game.advance_phase()
    tracker.observe_phase(game)
    bettor, _ = act(game, tracker, ActionType.RAISE, 20)
    raiser, _ = act(game, tracker, ActionType.RAISE, 40)
    assert tracker.get(bettor.id).faced_bets == 0
    assert tracker.get(raiser.id).faced_bets == 1
    assert tracker.get(raiser.id).postflop_aggr == 1


def test_preflop_allin_runout_counts_flop_and_showdown():
    game, tracker = table()
    act(game, tracker, ActionType.ALLIN)
    act(game, tracker, ActionType.ALLIN)
    while game.phase != GamePhase.SHOWDOWN:
        game.advance_phase()
        tracker.observe_phase(game)
    game.determine_winners()
    tracker.end_hand(game)
    tracker.end_hand(game)  # Counters remain idempotent.
    for player in game.players:
        assert tracker.get(player.id).saw_flop == 1
        assert tracker.get(player.id).showdowns == 1


def test_random_equity_baseline_uses_independent_full_live_deck():
    class RecordingRandom(random.Random):
        populations = []

        def sample(self, population, k, **kwargs):
            self.populations.append(set(population))
            return super().sample(population, k, **kwargs)

    rng = RecordingRandom(42)
    result = range_equity([Card(13, 0), Card(13, 1)],
                          [Card(14, 0), Card(12, 2), Card(9, 3), Card(6, 0), Card(2, 2)],
                          [RangeSpec("opponent", top=0.03)], simulations=100, rng=rng)
    assert len(rng.populations) == 100
    assert all(len(deck) == 45 for deck in rng.populations)
    assert all(deck == rng.populations[0] for deck in rng.populations)
    assert 0 <= result["equity"] <= 1
