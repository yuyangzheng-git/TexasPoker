"""
Headless poker benchmark: run simulated hands with configurable agent types
and export per-hand results to CSV.

Agent types:
  mc     - rule-based baseline: Monte Carlo equity + pot odds (no API keys needed)
  random - control baseline: uniform random over legal actions
  strategy[:persona_id]
         - local styled mixed-strategy agent (backend/strategy_agent.py) with
           range-aware equity; optional persona id from config/agent_personas.json
           (e.g. strategy:laohu). No API keys needed.
  llm    - LLM agent (backend/llm_agent.py); requires ANTHROPIC_API_KEY and the
           `openai` package. If LLM initialization fails the run aborts by
           default; pass --llm-fallback to degrade those seats to the MC
           baseline instead (fallbacks are recorded in the CSV).

Usage (run from the repo root):
  python scripts/benchmark.py --hands 100 --sims 500 \
      --seats mc,mc,mc,random,random,random \
      --seeds 42,43,44 --rotate \
      --csv data/benchmark_results.csv

Notes:
  - VPIP/PFR are computed pre-flop, per hand (voluntary money / raise in
    pre-flop per hand played), not as an all-street action ratio.
  - The dealer button advances every hand (engine-driven), so agents that
    stay at fixed seats already visit every position (BTN/SB/BB/UTG/MP/CO)
    over each orbit. Position is recorded per hand in the CSV.
  - --rotate rotates the *initial* agent->seat alignment per seed (seed k
    uses shift k % n), so different seeds start from different alignments
    while the dealer rotation balances positions within each run. Use
    --require-position-coverage to fail the run if any strategy did not
    cover every position.
  - --seeds runs the full experiment once per seed; the summary reports
    per-seed mean net chips per hand and a 95% t-confidence interval
    across seeds (NIST/SEMATECH e-Handbook 1.3.5.2).
"""
import argparse
import asyncio
import csv
import json
import math
import random
import statistics
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional

BACKEND_DIR = Path(__file__).resolve().parent.parent / "backend"
CONFIG_DIR = Path(__file__).resolve().parent.parent / "config"
sys.path.insert(0, str(BACKEND_DIR))

from game_engine import GameEngine, Player, Action, ActionType, GamePhase, PlayerStatus  # noqa: E402
from monte_carlo_equity import MonteCarloEquityCalculator  # noqa: E402
from opponent_model import PublicStatsTracker  # noqa: E402


@dataclass
class Decision:
    """A single agent decision plus meta-information for the experiment log."""
    action: Action
    fallback_reason: str = ""
    usage: Optional[dict] = None
    actual_agent: str = ""


class BaseAgent:
    agent_type = "base"

    def __init__(self, player_id: str, sims: int = 500):
        self.player_id = player_id
        self.sims = sims

    async def decide(self, game: GameEngine, player: Player) -> Decision:
        raise NotImplementedError

    @staticmethod
    def valid_or_fallback(game: GameEngine, player: Player, action: Action) -> Action:
        valid = game.get_valid_actions(player)
        if action.type not in valid:
            if ActionType.CHECK in valid:
                return Action(player_id=player.id, type=ActionType.CHECK)
            if ActionType.CALL in valid:
                return Action(player_id=player.id, type=ActionType.CALL)
            return Action(player_id=player.id, type=ActionType.FOLD)
        return action


class MCBaselineAgent(BaseAgent):
    """Rule-based agent: fold/call/raise based on Monte Carlo equity vs pot odds."""

    agent_type = "mc"

    async def decide(self, game: GameEngine, player: Player) -> Decision:
        valid = game.get_valid_actions(player)
        to_call = game.street_bet - player.current_bet

        opponents = [
            p for p in game.players
            if p.id != player.id and p.status != PlayerStatus.FOLDED
        ]
        if not opponents:
            return Decision(self.valid_or_fallback(
                game, player, Action(player.id, ActionType.CHECK)), actual_agent=self.agent_type)

        equity = MonteCarloEquityCalculator.calculate_equity(
            player.hole_cards,
            list(game.community_cards),
            len(opponents),
            simulations=self.sims,
        )

        if to_call <= 0:
            if equity >= 0.60 and ActionType.RAISE in valid:
                amount = max(game.street_bet * 2, game.big_blind * 2)
                return Decision(self.valid_or_fallback(
                    game, player, Action(player.id, ActionType.RAISE, amount=amount)),
                    actual_agent=self.agent_type)
            return Decision(self.valid_or_fallback(
                game, player, Action(player.id, ActionType.CHECK)), actual_agent=self.agent_type)

        pot_odds = to_call / (game.pot + to_call) if (game.pot + to_call) > 0 else 0.0
        if equity > pot_odds + 0.10 and ActionType.RAISE in valid:
            amount = game.minimum_raise_to()
            return Decision(self.valid_or_fallback(
                game, player, Action(player.id, ActionType.RAISE, amount=amount)),
                actual_agent=self.agent_type)
        if equity > pot_odds:
            return Decision(self.valid_or_fallback(
                game, player, Action(player.id, ActionType.CALL)), actual_agent=self.agent_type)
        return Decision(self.valid_or_fallback(
            game, player, Action(player.id, ActionType.FOLD)), actual_agent=self.agent_type)


class RandomAgent(BaseAgent):
    """Control baseline: uniform random choice over legal actions."""

    agent_type = "random"

    async def decide(self, game: GameEngine, player: Player) -> Decision:
        valid = game.get_valid_actions(player)
        action_type = random.choice(valid)
        if action_type == ActionType.RAISE:
            amount = game.minimum_raise_to()
            return Decision(Action(player.id, ActionType.RAISE, amount=amount),
                            actual_agent=self.agent_type)
        if action_type == ActionType.ALLIN:
            return Decision(Action(player.id, ActionType.ALLIN), actual_agent=self.agent_type)
        return Decision(Action(player.id, action_type), actual_agent=self.agent_type)


class StrategyWrapperAgent(BaseAgent):
    """Wraps backend StrategyAgent (styled mixed strategy, range-aware equity)."""

    agent_type = "strategy"

    def __init__(self, player_id: str, sims: int = 500, persona_id: str = "", label: str = "strategy"):
        super().__init__(player_id, sims)
        from strategy_agent import StrategyAgent

        with open(CONFIG_DIR / "agent_personas.json", encoding="utf-8") as f:
            personas = {p["id"]: p for p in json.load(f)["agents"]}
        if persona_id and persona_id not in personas:
            raise ValueError(f"unknown persona id: {persona_id}")
        self.persona = personas.get(persona_id) or {
            "id": "default", "name": "策略AI", "vpip_target": [0.25, 0.29],
            "pfr_target": [0.19, 0.23], "risk_profile": "tight_aggressive",
            "difficulty_level": "hard", "temperature": 0.5,
        }
        self.agent_type = label
        self.StrategyAgentClass = StrategyAgent
        self.agent = None
        self.tracker = None

    async def decide(self, game: GameEngine, player: Player) -> Decision:
        if self.agent is None:
            self.agent = self.StrategyAgentClass(self.persona, player,
                                                 seed=random.randrange(2**31), simulations=self.sims)
            self.agent.attach_tracker(self.tracker)
        self.agent.player = player
        resp = self.agent.decide_sync(game)
        return Decision(action=resp.action, fallback_reason=resp.fallback_reason,
                        actual_agent=self.agent_type)


class LLMWrapperAgent(BaseAgent):
    """Wraps backend LLMAgent.

    - Binds the LLM agent to the *same* Player object used by the engine
      (so hole cards, stack, and position stay in sync).
    - Raises on LLM initialization failure unless allow_fallback=True.
    - Reports runtime fallback reason and token usage per decision.
    """

    agent_type = "llm"

    def __init__(self, player_id: str, sims: int = 500, persona_index: int = 0,
                 allow_fallback: bool = False):
        super().__init__(player_id, sims)
        self.allow_fallback = allow_fallback
        self.init_reason = ""
        self.fallback = MCBaselineAgent(player_id, sims)
        self.llm_agent = None
        self.persona = None
        self._try_load_llm(persona_index)

    def _try_load_llm(self, persona_index: int):
        import os

        try:
            from llm_agent import LLMAgent

            if not os.getenv("ANTHROPIC_API_KEY"):
                raise RuntimeError("ANTHROPIC_API_KEY is not set")

            personas_path = CONFIG_DIR / "agent_personas.json"
            with open(personas_path, encoding="utf-8") as f:
                personas = json.load(f)["agents"]
            self.persona = personas[persona_index % len(personas)]
            # LLMAgent is created lazily in decide() with the engine's Player
            # so the agent always sees the real table state.
            self.LLMAgentClass = LLMAgent
        except Exception as e:  # noqa: BLE001
            reason = f"LLM init failed: {e}"
            self.init_reason = reason
            if not self.allow_fallback:
                raise RuntimeError(
                    f"[llm:{self.player_id}] {reason}. "
                    "Set ANTHROPIC_API_KEY / install `openai`, or pass "
                    "--llm-fallback to degrade this seat to the MC baseline."
                )
            print(f"  [llm:{self.player_id}] {reason}; using MC baseline (--llm-fallback)")

    async def decide(self, game: GameEngine, player: Player) -> Decision:
        if self.llm_agent is None and self.init_reason:
            decision = await self.fallback.decide(game, player)
            decision.actual_agent = "mc_fallback"
            decision.fallback_reason = self.init_reason
            return decision

        if self.llm_agent is None:
            # Lazy init bound to the real table player.
            self.llm_agent = self.LLMAgentClass(self.persona, player)
        else:
            # The engine player object is stable across hands, but re-bind to
            # be safe when seats rotate.
            self.llm_agent.player = player

        resp = await self.llm_agent.decide(game)
        return Decision(
            action=resp.action,
            fallback_reason=getattr(resp, "fallback_reason", ""),
            usage=getattr(resp, "usage", None),
            actual_agent="llm" if not getattr(resp, "fallback_reason", "") else "llm_fallback",
        )


async def play_hand(engine: GameEngine, seats: Dict[str, BaseAgent],
                    tracker: Optional[PublicStatsTracker] = None) -> dict:
    """Play one full hand; returns per-player results."""
    engine.reset_for_new_hand()
    if len(engine.active_players()) < 2:
        return {}

    engine.deal_hole_cards()
    engine.post_blinds()
    if tracker is not None:
        tracker.start_hand(engine)

    per_player = {
        p.id: {
            "player": p.name,
            "requested_agent": seats[p.id].agent_type,
            "start_stack": p.stack,
            "actions": {a.value: 0 for a in ActionType},
            "decisions": 0,
            "latencies": [],
            "preflop_voluntary": False,
            "preflop_raise": False,
            "fallback_count": 0,
            "fallback_reasons": [],
            "actual_agents": set(),
            "prompt_tokens": 0,
            "completion_tokens": 0,
        }
        for p in engine.players
    }

    while engine.phase not in (GamePhase.SHOWDOWN, GamePhase.ENDED):
        if len(engine.non_folded_players()) <= 1:
            break

        round_guard = 0
        while not engine.is_betting_round_complete():
            round_guard += 1
            if round_guard > 500:
                print(f"  [warn] betting round guard hit in hand (phase={engine.phase.value})")
                break

            actors = [
                p for p in engine.get_action_order()
                if p.id in engine.pending_actors and p.status == PlayerStatus.ACTIVE
            ]
            if not actors:
                break

            player = actors[0]
            agent = seats[player.id]
            preflop = engine.phase == GamePhase.PRE_FLOP
            start = time.perf_counter()
            try:
                decision = await asyncio.wait_for(agent.decide(engine, player), timeout=60)
            except Exception as e:  # noqa: BLE001
                decision = Decision(Action(player.id, ActionType.FOLD),
                                    fallback_reason=f"benchmark_timeout_or_error:{e}",
                                    actual_agent="error")
            latency_ms = (time.perf_counter() - start) * 1000

            record = per_player[player.id]
            record["decisions"] += 1
            record["latencies"].append(latency_ms)
            record["actual_agents"].add(decision.actual_agent or agent.agent_type)

            if decision.fallback_reason:
                record["fallback_count"] += 1
                record["fallback_reasons"].append(decision.fallback_reason)
            if decision.usage:
                record["prompt_tokens"] += decision.usage.get("prompt_tokens", 0)
                record["completion_tokens"] += decision.usage.get("completion_tokens", 0)

            action = decision.action
            valid = engine.get_valid_actions(player)
            if action.type not in valid:
                if ActionType.CHECK in valid:
                    action = Action(player.id, ActionType.CHECK)
                elif ActionType.CALL in valid:
                    action = Action(player.id, ActionType.CALL)
                else:
                    action = Action(player.id, ActionType.FOLD)
                record["fallback_count"] += 1
                record["fallback_reasons"].append("invalid_action_corrected")

            # Pre-flop stats: voluntary money = any call/raise/all-in.
            # PFR counts raises that increase the bet, including an all-in
            # whose stack exceeds the amount needed to call.
            to_call = engine.street_bet - player.current_bet
            is_preflop_raise = (
                action.type == ActionType.RAISE
                or (action.type == ActionType.ALLIN and player.stack > max(to_call, 0.0))
            )
            if preflop and action.type in (ActionType.CALL, ActionType.RAISE, ActionType.ALLIN):
                record["preflop_voluntary"] = True
            if preflop and is_preflop_raise:
                record["preflop_raise"] = True

            record["actions"][action.type.value] += 1
            if not engine.process_action(action):
                raise RuntimeError(f"Benchmark produced an illegal action: {action}")
            if tracker is not None:
                tracker.observe(engine, player.id, action.type)

            if len(engine.non_folded_players()) <= 1:
                break

        if len(engine.non_folded_players()) <= 1:
            break

        if engine.phase not in (GamePhase.SHOWDOWN, GamePhase.ENDED):
            engine.advance_phase()
            if tracker is not None:
                tracker.observe_phase(engine)

    # Run out remaining streets when everyone is all-in
    while (
        engine.phase not in (GamePhase.SHOWDOWN, GamePhase.ENDED)
        and not engine.active_players()
        and len(engine.non_folded_players()) > 1
    ):
        engine.advance_phase()
        if tracker is not None:
            tracker.observe_phase(engine)

    allocations = engine.determine_winners()
    if tracker is not None:
        tracker.end_hand(engine)
    for alloc in allocations:
        pid = alloc["playerId"]
        if pid in per_player:
            per_player[pid]["net"] = alloc["stackChange"]
            per_player[pid]["won"] = 1 if alloc["amount"] > 0 else 0

    for pid, rec in per_player.items():
        player = next(p for p in engine.players if p.id == pid)
        rec["end_stack"] = player.stack
        rec.setdefault("net", rec["end_stack"] - rec["start_stack"])
        rec.setdefault("won", 0)
        rec["position"] = player.position
        rec["dealer"] = engine.players[engine.dealer_idx].id
        rec["avg_latency_ms"] = (
            round(statistics.mean(rec["latencies"]), 1) if rec["latencies"] else 0.0
        )
    return per_player


def make_seats(seat_spec: list, sims: int, allow_llm_fallback: bool) -> Dict[str, BaseAgent]:
    seats = {}
    for i, spec in enumerate(seat_spec):
        player_id = f"p{i}"
        spec = spec.strip().lower()
        if spec == "mc":
            seats[player_id] = MCBaselineAgent(player_id, sims)
        elif spec == "random":
            seats[player_id] = RandomAgent(player_id, sims)
        elif spec == "strategy" or spec.startswith("strategy:"):
            persona_id = spec.split(":", 1)[1] if ":" in spec else ""
            seats[player_id] = StrategyWrapperAgent(player_id, sims, persona_id=persona_id, label=spec)
        elif spec == "llm":
            seats[player_id] = LLMWrapperAgent(player_id, sims, persona_index=i,
                                               allow_fallback=allow_llm_fallback)
        else:
            raise ValueError(f"unknown agent type: {spec}")
    return seats


def rotated_seats(agents: Dict[str, BaseAgent], shift: int) -> Dict[str, BaseAgent]:
    """Shift the agent->seat assignment by `shift` seats (initial alignment)."""
    seat_ids = list(agents)
    n = len(seat_ids)
    return {seat_ids[i]: agents[seat_ids[(i - shift) % n]] for i in range(n)}


def position_coverage(rows: List[dict]) -> Dict[str, set]:
    """Positions (BTN/SB/BB/UTG/MP/CO) actually played per requested_agent."""
    cov: Dict[str, set] = {}
    for row in rows:
        cov.setdefault(row["requested_agent"], set()).add(row["position"])
    return cov


FIELD_NAMES = ["seed", "hand_id", "player", "requested_agent", "actual_agent",
               "position", "dealer",
               "net_chips", "won_pot", "vpip_hand", "pfr_hand",
               "fold", "check", "call", "raise", "allin", "decisions",
               "avg_latency_ms", "fallback_count", "fallback_reasons",
               "prompt_tokens", "completion_tokens"]


def run_seed(seed: int, seed_index: int, args, seat_spec: list) -> List[dict]:
    """Run `--hands` hands for one random seed; returns per-hand rows."""
    random.seed(seed)
    agents = make_seats(seat_spec, args.sims, args.llm_fallback)
    if args.rotate:
        # Vary the initial alignment per seed; the dealer rotation inside
        # the run then balances positions within each seed.
        agents = rotated_seats(agents, seed_index % len(agents))
    players = [
        Player(id=pid, name=f"p{i}", stack=args.stack)
        for i, pid in enumerate(agents)
    ]
    engine = GameEngine(players, min_bet=args.stack / 200)  # SB = 0.5% of stack
    tracker = PublicStatsTracker()
    for agent in agents.values():
        if hasattr(agent, "tracker"):
            agent.tracker = tracker

    print(f"seed={seed}: {args.hands} hands, seats={seat_spec}, sims={args.sims}, "
          f"rotate={args.rotate}, rebuy={args.rebuy}")

    rows = []
    for hand in range(args.hands):
        if args.rebuy:
            for p in engine.players:
                p.stack = args.stack
        if len([p for p in engine.players if p.stack > 0]) < 2:
            print(f"  hand {hand + 1}: skipped (game over)")
            break
        seats = agents
        result = asyncio.run(play_hand(engine, seats, tracker))
        for pid, rec in result.items():
            rows.append({
                "seed": seed,
                "hand_id": hand + 1,
                "player": pid,
                "requested_agent": rec["requested_agent"],
                "actual_agent": ",".join(sorted(rec["actual_agents"])) or "none",
                "position": rec["position"],
                "dealer": rec["dealer"],
                "net_chips": rec["net"],
                "won_pot": rec["won"],
                "vpip_hand": 1 if rec["preflop_voluntary"] else 0,
                "pfr_hand": 1 if rec["preflop_raise"] else 0,
                "fold": rec["actions"]["fold"],
                "check": rec["actions"]["check"],
                "call": rec["actions"]["call"],
                "raise": rec["actions"]["raise"],
                "allin": rec["actions"]["allin"],
                "decisions": rec["decisions"],
                "avg_latency_ms": rec["avg_latency_ms"],
                "fallback_count": rec["fallback_count"],
                "fallback_reasons": ";".join(rec["fallback_reasons"])[:200],
                "prompt_tokens": rec["prompt_tokens"],
                "completion_tokens": rec["completion_tokens"],
            })
        if (hand + 1) % 25 == 0:
            print(f"  ... {hand + 1} hands done")
    return rows


def summarize(rows: List[dict], label: str = "") -> Dict[str, dict]:
    """Aggregate per requested_agent: net/hand, VPIP, PFR, fallbacks, tokens."""
    agg: Dict[str, dict] = {}
    for row in rows:
        key = row["requested_agent"]
        a = agg.setdefault(key, {
            "hands": 0, "net": 0.0, "wins": 0, "vpip_hands": 0, "pfr_hands": 0,
            "fallbacks": 0, "prompt_tokens": 0, "completion_tokens": 0,
        })
        a["hands"] += 1
        a["net"] += row["net_chips"]
        a["wins"] += row["won_pot"]
        a["vpip_hands"] += row["vpip_hand"]
        a["pfr_hands"] += row["pfr_hand"]
        a["fallbacks"] += row["fallback_count"]
        a["prompt_tokens"] += row["prompt_tokens"]
        a["completion_tokens"] += row["completion_tokens"]
    for a in agg.values():
        h = max(1, a["hands"])
        a["net_per_hand"] = a["net"] / h
        a["win_pct"] = 100 * a["wins"] / h
        a["vpip"] = a["vpip_hands"] / h
        a["pfr"] = a["pfr_hands"] / h
    return agg


# 95% t-critical values for df = 1..10 (two-sided); normal approx beyond.
# See NIST/SEMATECH e-Handbook 1.3.5.2 (confidence limits for the mean).
T_CRITICAL_95 = {
    1: 12.706, 2: 4.303, 3: 3.182, 4: 2.776, 5: 2.571,
    6: 2.447, 7: 2.365, 8: 2.306, 9: 2.262, 10: 2.228,
}


def t_critical(df: int) -> float:
    return T_CRITICAL_95.get(df, 1.960)


def print_multi_seed_summary(per_seed: Dict[int, Dict[str, dict]]):
    """Per-seed values + mean net/hand with a 95% t-confidence interval."""
    print("\nCross-seed summary (net chips per hand, mean ± 95% t-CI):")
    print("-" * 90)
    agent_types = sorted({a for agg in per_seed.values() for a in agg})
    seed_keys = sorted(per_seed)
    header = f"{'agent':<10}" + "".join(f"{'seed' + str(s):>12}" for s in seed_keys) + f"{'mean':>12} {'±95%CI':>12} {'seeds':>6}"
    print(header)
    for at in agent_types:
        values = [per_seed[s][at]["net_per_hand"] for s in seed_keys if at in per_seed[s]]
        n = len(values)
        mean = statistics.mean(values)
        if n > 1:
            sd = statistics.stdev(values)  # sample std, n-1
            ci = t_critical(n - 1) * sd / math.sqrt(n)
        else:
            ci = float("nan")
        cells = "".join(f"{v:>12.1f}" for v in values)
        print(f"{at:<10}{cells} {mean:>12.1f} {ci:>12.1f} {n:>6}")


def print_aggregate(agg: Dict[str, dict]):
    print(f"{'agent':<12} {'hands':>6} {'net_chips':>12} {'net/hand':>10} "
          f"{'win%':>6} {'VPIP':>6} {'PFR':>6} {'fallbacks':>9} {'tok_in':>9} {'tok_out':>9}")
    for agent, a in sorted(agg.items()):
        print(f"{agent:<12} {a['hands']:>6} {a['net']:>12.0f} {a['net_per_hand']:>10.1f} "
              f"{a['win_pct']:>5.1f}% {a['vpip']:>6.2f} {a['pfr']:>6.2f} "
              f"{a['fallbacks']:>9} {a['prompt_tokens']:>9} {a['completion_tokens']:>9}")


def main():
    parser = argparse.ArgumentParser(description="Headless poker agent benchmark")
    parser.add_argument("--hands", type=int, default=100, help="number of hands per seed")
    parser.add_argument("--sims", type=int, default=500, help="Monte Carlo simulations per decision")
    parser.add_argument("--seats", type=str, default="mc,mc,mc,random,random,random",
                        help="comma-separated agent types per seat")
    parser.add_argument("--seeds", type=str, default="42",
                        help="comma-separated random seeds (one full run each)")
    parser.add_argument("--stack", type=float, default=10000.0, help="starting stack per player")
    parser.add_argument("--rebuy", action="store_true", help="reset stack each hand")
    parser.add_argument("--rotate", action="store_true",
                        help="rotate the initial agent->seat alignment per seed "
                             "(dealer rotation balances positions within each run)")
    parser.add_argument("--require-position-coverage", action="store_true",
                        help="fail (exit 1) if any strategy did not cover every position")
    parser.add_argument("--llm-fallback", action="store_true",
                        help="degrade llm seats to MC baseline on init failure instead of aborting")
    parser.add_argument("--csv", type=str, default="data/benchmark_results.csv",
                        help="output CSV path for per-hand results")
    args = parser.parse_args()

    seat_spec = [s for s in args.seats.split(",") if s.strip()]
    if len(seat_spec) < 2:
        print("error: need at least 2 seats")
        sys.exit(1)

    seeds = [int(s.strip()) for s in args.seeds.split(",") if s.strip()]

    all_rows = []
    per_seed = {}
    for seed_index, seed in enumerate(seeds):
        rows = run_seed(seed, seed_index, args, seat_spec)
        all_rows.extend(rows)
        per_seed[seed] = summarize(rows)
        print("")

    # Position coverage report (positions are recorded per hand in the CSV)
    coverage = position_coverage(all_rows)
    print("Position coverage per strategy (each must cover all 6 positions):")
    n_players = len(seat_spec)
    all_positions = {"BTN", "SB", "BB", "UTG", "MP", "CO"}
    coverage_ok = True
    for agent_type, positions in sorted(coverage.items()):
        missing = sorted(all_positions - positions)
        status = "OK" if not missing else f"MISSING {missing}"
        if missing:
            coverage_ok = False
        print(f"  {agent_type:<10} {sorted(positions)}  {status}")
    if args.require_position_coverage and not coverage_ok:
        print("error: position coverage requirement not met")
        sys.exit(1)
    if n_players > 6:
        print("  (note: table has more than 6 seats; extra seats keep P# labels)")

    out = Path(args.csv)
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FIELD_NAMES)
        writer.writeheader()
        writer.writerows(all_rows)
    print(f"Per-hand results written to {out}")

    print("\nAggregate results by requested agent (all seeds combined):")
    print("-" * 100)
    print_aggregate(summarize(all_rows))
    if len(seeds) > 1:
        print_multi_seed_summary(per_seed)


if __name__ == "__main__":
    main()
