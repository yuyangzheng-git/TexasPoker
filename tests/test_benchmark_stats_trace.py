"""
Benchmark statistics traced through the REAL engine (not hand-written
summaries):

- a pre-flop all-in that raises the bet must count toward PFR
- a pre-flop all-in that merely calls must NOT count toward PFR
- init-failure fallbacks must carry a fallback_reason into the CSV
- every strategy must cover all six positions across hands
- --rotate must vary the initial alignment per seed, not per hand
"""
import argparse
import asyncio
import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "backend"))
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import benchmark  # noqa: E402
from game_engine import GameEngine, Player, Action, ActionType  # noqa: E402


class ScriptedAgent:
    """Agent that returns a fixed decision; runs through the real engine."""

    agent_type = "scripted"

    def __init__(self, player_id: str, decision_fn):
        self.player_id = player_id
        self.decision_fn = decision_fn

    async def decide(self, game: GameEngine, player: Player):
        action = self.decision_fn(game, player)
        return benchmark.Decision(action=action, actual_agent=self.agent_type)


def _engine4():
    players = [
        Player(id="p0", name="p0", stack=1000.0),
        Player(id="p1", name="p1", stack=1000.0),
        Player(id="p2", name="p2", stack=1000.0),
        Player(id="p3", name="p3", stack=1000.0),
    ]
    engine = GameEngine(players, min_bet=10.0)
    # play_hand() calls reset_for_new_hand() itself (dealer 0 -> 1), so with
    # dealer=1: p1 BTN, p2 SB, p3 BB, p0 UTG (pre-flop first to act).
    engine.dealer_idx = 0
    return engine


def _fold(game, player):
    return Action(player.id, ActionType.FOLD)


def test_preflop_allin_raise_counts_as_pfr():
    engine = _engine4()

    def allin_raise(game, player):
        return Action(player.id, ActionType.ALLIN, amount=player.stack)

    seats = {
        "p0": ScriptedAgent("p0", allin_raise),  # UTG acts first
        "p1": ScriptedAgent("p1", _fold),
        "p2": ScriptedAgent("p2", _fold),
        "p3": ScriptedAgent("p3", _fold),
    }
    engine.deal_hole_cards()
    engine.post_blinds()
    result = asyncio.run(benchmark.play_hand(engine, seats))

    utG = result["p0"]
    assert utG["position"] == "UTG"
    assert utG["preflop_voluntary"] is True
    assert utG["preflop_raise"] is True, "all-in raise must count toward PFR"


def test_preflop_allin_call_does_not_count_as_pfr():
    engine = _engine4()

    # p0 (UTG) calls, then when the BB re-raises it goes all-in for exactly
    # the call amount (stack == to_call) -> all-in call, not a raise.
    calls = {"count": 0}

    def utG_call_then_allin_call(game, player):
        if calls["count"] == 0:
            calls["count"] += 1
            return Action(player.id, ActionType.CALL)
        player.stack = game.street_bet - player.current_bet
        return Action(player.id, ActionType.ALLIN, amount=player.stack)

    def open_raise(game, player):
        return Action(player.id, ActionType.RAISE, amount=100.0)

    seats = {
        "p0": ScriptedAgent("p0", utG_call_then_allin_call),
        "p1": ScriptedAgent("p1", _fold),
        "p2": ScriptedAgent("p2", _fold),
        "p3": ScriptedAgent("p3", open_raise),  # BB re-raises
    }
    engine.deal_hole_cards()
    engine.post_blinds()

    result = asyncio.run(benchmark.play_hand(engine, seats))

    rec = result["p0"]
    assert rec["preflop_voluntary"] is True
    assert rec["preflop_raise"] is False, "all-in call must not count toward PFR"


def test_init_fallback_reason_recorded_through_real_engine(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    agent = benchmark.LLMWrapperAgent("p0", sims=50, allow_fallback=True)
    assert agent.init_reason, "LLM init should fail without an API key"

    engine = _engine4()
    seats = {
        "p0": agent,
        "p1": ScriptedAgent("p1", _fold),
        "p2": ScriptedAgent("p2", _fold),
        "p3": ScriptedAgent("p3", _fold),
    }
    engine.deal_hole_cards()
    engine.post_blinds()
    result = asyncio.run(benchmark.play_hand(engine, seats))

    rec = result["p0"]
    assert "mc_fallback" in rec["actual_agents"]
    assert rec["fallback_count"] >= 1
    assert any("LLM init failed" in r for r in rec["fallback_reasons"])


def test_every_strategy_covers_all_positions():
    args = argparse.Namespace(
        sims=50, llm_fallback=False, stack=1000.0,
        rotate=True, rebuy=True, hands=12,
    )
    rows = benchmark.run_seed(42, 0, args, ["mc", "mc", "mc", "random", "random", "random"])
    coverage = benchmark.position_coverage(rows)
    all_positions = {"BTN", "SB", "BB", "UTG", "MP", "CO"}
    assert coverage["mc"] == all_positions
    assert coverage["random"] == all_positions


def test_rotate_changes_initial_alignment_per_seed_not_per_hand():
    args = argparse.Namespace(
        sims=50, llm_fallback=False, stack=1000.0,
        rotate=True, rebuy=True, hands=6,
    )
    rows0 = benchmark.run_seed(42, 0, args, ["mc", "random", "mc", "random", "mc", "random"])
    rows1 = benchmark.run_seed(42, 1, args, ["mc", "random", "mc", "random", "mc", "random"])

    # Within one seed the agent->seat mapping is stable across hands
    hand1_0 = {r["player"]: r["requested_agent"] for r in rows0 if r["hand_id"] == 1}
    hand2_0 = {r["player"]: r["requested_agent"] for r in rows0 if r["hand_id"] == 2}
    assert hand1_0 == hand2_0

    # Different seeds start from different alignments (same cards, same seed
    # RNG: hand 1 is identical except for the alignment shift)
    hand1_1 = {r["player"]: r["requested_agent"] for r in rows1 if r["hand_id"] == 1}
    assert hand1_0 != hand1_1

    # A fixed player's position still changes across hands (dealer rotation)
    p0_positions = {r["position"] for r in rows0 if r["player"] == "p0"}
    assert len(p0_positions) > 3, "old bug kept each agent at one relative position"
