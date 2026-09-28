"""
Benchmark agent 测试：
- LLM wrapper 必须绑定引擎中的同一个 Player（状态同步）
- LLM 初始化失败默认终止（除非显式允许降级）
- 座位轮换正确
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import importlib.util  # noqa: E402

_BENCH_PATH = Path(__file__).resolve().parent.parent / "scripts" / "benchmark.py"
_spec = importlib.util.spec_from_file_location("benchmark", _BENCH_PATH)
benchmark = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(benchmark)

from game_engine import GameEngine, Player  # noqa: E402


def make_game():
    players = [
        Player(id="p0", name="p0", stack=10000.0),
        Player(id="p1", name="p1", stack=10000.0),
        Player(id="p2", name="p2", stack=10000.0),
    ]
    return GameEngine(players, min_bet=50.0)


class TestLLMWrapperStateSync:
    def test_init_failure_aborts_by_default(self, monkeypatch):
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        try:
            benchmark.LLMWrapperAgent("p0", allow_fallback=False)
        except RuntimeError as e:
            assert "LLM init failed" in str(e)
        else:
            raise AssertionError("should have raised without API key")

    def test_init_failure_falls_back_when_allowed(self, monkeypatch):
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        agent = benchmark.LLMWrapperAgent("p0", allow_fallback=True)
        assert agent.init_reason
        assert agent.llm_agent is None

    def test_decide_binds_engine_player(self):
        """发牌后，LLM 读取的必须是引擎中的同一个 Player（含手牌）"""
        game = make_game()
        game.deal_hole_cards()
        game.post_blinds()

        agent = benchmark.LLMWrapperAgent("p0", allow_fallback=True)
        seen = {}

        class FakeLLMAgent:
            def __init__(self, config, player):
                self.config = config
                self.player = player

            async def decide(self, game_):
                seen["player"] = self.player
                resp = type("R", (), {})()
                resp.action = benchmark.Action(self.player.id, benchmark.ActionType.CHECK)
                resp.fallback_reason = ""
                resp.usage = None
                return resp

        fake = FakeLLMAgent(agent.persona or {"name": "t"}, game.players[0])
        agent.llm_agent = fake
        agent.init_reason = ""

        player = game.players[0]
        asyncio.run(agent.decide(game, player))
        assert seen["player"] is player
        assert len(seen["player"].hole_cards) == 2

    def test_rotation_shifts_every_hand(self):
        seats = {
            "p0": benchmark.MCBaselineAgent("p0", 100),
            "p1": benchmark.RandomAgent("p1", 100),
            "p2": benchmark.MCBaselineAgent("p2", 100),
        }
        r1 = benchmark.rotated_seats(seats, 1)
        assert r1["p0"] is seats["p2"]
        assert r1["p1"] is seats["p0"]
        assert r1["p2"] is seats["p1"]
        r2 = benchmark.rotated_seats(seats, 2)
        assert r2["p0"] is seats["p1"]
        assert r2["p1"] is seats["p2"]
        assert r2["p2"] is seats["p0"]
        r0 = benchmark.rotated_seats(seats, 0)
        assert r0 == seats
        r3 = benchmark.rotated_seats(seats, 3)
        assert r3 == seats


class TestSummary:
    def test_summary_vpip_pfr_preflop(self):
        rows = [
            {"requested_agent": "mc", "net_chips": 100, "won_pot": 1,
             "vpip_hand": 1, "pfr_hand": 1, "fallback_count": 0,
             "prompt_tokens": 0, "completion_tokens": 0},
            {"requested_agent": "mc", "net_chips": -50, "won_pot": 0,
             "vpip_hand": 0, "pfr_hand": 0, "fallback_count": 0,
             "prompt_tokens": 0, "completion_tokens": 0},
            {"requested_agent": "mc", "net_chips": 25, "won_pot": 0,
             "vpip_hand": 1, "pfr_hand": 0, "fallback_count": 1,
             "prompt_tokens": 10, "completion_tokens": 5},
        ]
        agg = benchmark.summarize(rows)
        a = agg["mc"]
        assert a["net_per_hand"] == 75.0 / 3
        assert abs(a["vpip"] - 2 / 3) < 1e-9
        assert abs(a["pfr"] - 1 / 3) < 1e-9
        assert a["fallbacks"] == 1
