import asyncio
import threading
import time
from unittest.mock import AsyncMock

from agent_engine import AgentMemory
from game_engine import GameEngine, Player, Action, ActionType
from llm_agent import LLMAgent, PromptBuilder, ResponseParser


def test_prompt_work_runs_off_event_loop_and_is_included_in_timeout(monkeypatch):
    game = GameEngine([Player('a', 'A', 1000), Player('b', 'B', 1000)])
    agent = object.__new__(LLMAgent)
    agent.player = game.players[0]
    agent.config = {'name': 'test'}
    agent.memory = AgentMemory()
    threads = []
    main_thread = threading.get_ident()

    def slow_prompt(*args):
        threads.append(threading.get_ident())
        time.sleep(0.08)
        return 'unused prompt'

    monkeypatch.setattr(PromptBuilder, 'build', slow_prompt)
    monkeypatch.setattr(ResponseParser, '_fallback_action', lambda p, g: Action(p.id, ActionType.CHECK))
    agent._call_api = AsyncMock()
    response = asyncio.run(agent.decide(game, timeout=0.02))
    assert response.fallback_reason == 'timeout'
    assert response.action.type == ActionType.CHECK
    assert threads and threads[0] != main_thread
    agent._call_api.assert_not_awaited()
