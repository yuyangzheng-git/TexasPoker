import asyncio
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import main
from database.connection import get_db
from database.models import Base
from game_engine import Action, ActionType
from game_logger import GameLogger


class CallingAgent:
    def __init__(self, config, player):
        self.player = player

    async def decide(self, game, **kwargs):
        await asyncio.sleep(0)
        kind = ActionType.CHECK if self.player.current_bet >= game.street_bet else ActionType.CALL
        return SimpleNamespace(action=Action(self.player.id, kind), thinking='PRIVATE_REASONING', speech='继续')


@pytest.fixture
def client(monkeypatch, tmp_path):
    monkeypatch.setattr(main.settings, 'POKER_AGENT_MODE', 'llm')
    monkeypatch.setattr(main, 'LLMAgent', CallingAgent)
    monkeypatch.setattr(main.random, 'shuffle', lambda players: None)
    monkeypatch.setattr(main, 'GameLogger', lambda game_id: GameLogger(game_id, str(tmp_path)))
    monkeypatch.setattr(main, 'init_db', lambda: None)
    main.active_games.clear()
    engine = create_engine('sqlite://', connect_args={'check_same_thread': False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine)

    def db():
        with factory() as session:
            yield session

    main.app.dependency_overrides[get_db] = db
    with TestClient(main.app) as result:
        yield result
    main.app.dependency_overrides.clear()
    main.active_games.clear()
    engine.dispose()


def create(client):
    response = client.post('/api/games', json={'table_size': 2})
    assert response.status_code == 200, response.text
    return response.json()


def test_production_strategy_mode_creates_real_agents(client, monkeypatch):
    from strategy_agent import StrategyAgent
    monkeypatch.setattr(main.settings, 'POKER_AGENT_MODE', 'strategy')
    assert client.get('/api/health').json() == {'status': 'ok', 'agent_mode': 'strategy'}
    assert client.get('/api/local-mode').json()['paid_api_calls'] is False
    game = create(client)
    session = main.active_games[game['gameId']]['session']
    assert all(isinstance(agent, StrategyAgent) for agent in session.agents.values())
    assert all(agent.tracker is session.tracker for agent in session.agents.values())


def connect(client, game):
    return client.websocket_connect('/ws/' + game['gameId'])


def auth(ws, game):
    ws.send_json({'type': 'AUTH', 'sessionToken': game['sessionToken']})


def until(ws, event):
    for _ in range(100):
        message = ws.receive_json()
        if message['type'] == event:
            return message['data']
    raise AssertionError(f'Never received {event}')


def test_websocket_requires_correct_table_capability(client):
    game = create(client)
    for message in ({'type': 'AUTH', 'sessionToken': 'wrong'}, ['malformed']):
        with connect(client, game) as ws:
            ws.send_json(message)
            with pytest.raises(WebSocketDisconnect) as exc:
                ws.receive_json()
            assert exc.value.code == 4403
    assert main.active_games[game['gameId']]['session'].task is None


def test_reconnect_preserves_hand_blinds_task_and_action_deadline(client):
    game = create(client)
    with connect(client, game) as ws:
        auth(ws, game)
        request = until(ws, 'PLAYER_ACTION_REQUEST')
        session = main.active_games[game['gameId']]['session']
        original_task = session.task
        state = session.snapshot()
    with connect(client, game) as ws:
        auth(ws, game)
        replay = until(ws, 'SESSION_STATE')
        assert replay['state'] == state
        assert replay['pendingAction']['requestId'] == request['requestId']
        assert replay['pendingAction']['timeLimit'] <= request['timeLimit']
        assert session.task is original_task
        assert session.game.pot == session.game.min_bet + session.game.big_blind


def test_second_socket_cannot_start_another_game_loop(client):
    game = create(client)
    with connect(client, game) as first:
        auth(first, game)
        until(first, 'PLAYER_ACTION_REQUEST')
        with connect(client, game) as second:
            auth(second, game)
            with pytest.raises(WebSocketDisconnect) as exc:
                second.receive_json()
            assert exc.value.code == 4409
        engine = main.active_games[game['gameId']]['session'].game
        assert engine.pot == engine.min_bet + engine.big_blind


def test_bad_stale_and_duplicate_actions_do_not_spend_chips(client):
    game = create(client)
    with connect(client, game) as ws:
        auth(ws, game)
        request = until(ws, 'PLAYER_ACTION_REQUEST')
        session = main.active_games[game['gameId']]['session']
        before = session.snapshot()
        ws.send_json({'type': 'ACTION', 'requestId': 'stale', 'action': 'allin'})
        until(ws, 'ERROR')
        assert session.snapshot() == before
        ws.send_json({'type': 'ACTION', 'requestId': request['requestId'], 'action': 'raise', 'amount': -10})
        until(ws, 'ERROR')
        assert session.snapshot() == before
        command = {'type': 'ACTION', 'requestId': request['requestId'], 'action': 'call'}
        ws.send_json(command)
        until(ws, 'PLAYER_ACTION')
        next_request = until(ws, 'PLAYER_ACTION_REQUEST')
        after = session.snapshot()
        ws.send_json(command)
        until(ws, 'ERROR')
        assert session.snapshot() == after
        assert next_request['requestId'] != request['requestId']


def test_pause_and_resume_are_processed_during_human_turn(client):
    game = create(client)
    with connect(client, game) as ws:
        auth(ws, game)
        request = until(ws, 'PLAYER_ACTION_REQUEST')
        ws.send_json({'type': 'PAUSE'})
        assert until(ws, 'PAUSE_STATE')['paused'] is True
        ws.send_json({'type': 'RESUME'})
        assert until(ws, 'PAUSE_STATE')['paused'] is False
        assert main.active_games[game['gameId']]['session'].pending['requestId'] == request['requestId']


def test_full_hand_hides_private_cards_and_reasoning_until_result(client):
    game = create(client)
    result = None
    with connect(client, game) as ws:
        auth(ws, game)
        for _ in range(100):
            message = ws.receive_json()
            event, data = message['type'], message['data']
            if event == 'PLAYER_ACTION_REQUEST':
                ws.send_json({'type': 'ACTION', 'requestId': data['requestId'],
                    'action': 'call' if data['callAmount'] else 'check'})
            if event in ('GAME_STARTED', 'PHASE_CHANGED'):
                if data['phase'] != 'showdown':
                    assert not data['players'][1]['holeCards']
            if event == 'AGENT_THINKING_CHUNK':
                assert main.active_games[game['gameId']]['session'].game.phase.value == 'showdown'
            if event == 'SHOWDOWN':
                result = data
                break
        assert result is not None
        assert all(len(p['holeCards']) == 2 for p in result['finalState']['players'])
        session = main.active_games[game['gameId']]['session']
        assert sum(p.stack for p in session.game.players) == sum(session.game.hand_start_stacks.values())
        state = session.snapshot()
        assert len(session.game.action_history) == 8
    with connect(client, game) as ws:
        auth(ws, game)
        replay = until(ws, 'SESSION_STATE')
        assert replay['state'] == state
        assert replay['result'] == result
        ws.send_json({'type': 'READY_FOR_NEXT_HAND', 'requestId': result['requestId']})
        next_hand = until(ws, 'HAND_STARTED')
        assert next_hand['handNumber'] == 2


def test_full_logs_are_not_public(client):
    assert client.get('/api/logs').status_code in (401, 403)
    assert client.get('/api/logs/private.json').status_code in (401, 403)
    assert client.get('/api/logs/private.json/summary').status_code in (401, 403)


@pytest.mark.parametrize('body', [{'table_size': 100}, {'table_size': 'bad'},
    {'preferred_ai_personas': ['missing']}, {'preferred_ai_personas': ['laowang', 'laowang']}])
def test_invalid_table_setup_is_rejected(client, body):
    assert client.post('/api/games', json=body).status_code == 422
    assert not main.active_games


def test_register_login_and_private_profile_work_with_unicode_password(client):
    password = '密' * 50
    response = client.post('/api/auth/register', json={
        'username': 'test_player', 'email': 'player@example.com', 'password': password,
    })
    assert response.status_code == 201, response.text
    response = client.post('/api/auth/login', json={'username': 'test_player', 'password': password})
    assert response.status_code == 200, response.text
    token = response.json()['access_token']
    response = client.get('/api/auth/me', headers={'Authorization': 'Bearer ' + token})
    assert response.status_code == 200
    assert response.json()['username'] == 'test_player'


def test_human_timeout_folds_when_facing_a_bet(client):
    game = create(client)
    session = main.active_games[game['gameId']]['session']
    session.config['game']['human_timeout_ms'] = 50
    with connect(client, game) as ws:
        auth(ws, game)
        until(ws, 'PLAYER_ACTION_REQUEST')
        action = until(ws, 'PLAYER_ACTION')
        assert action['playerId'] == 'player_human'
        assert action['action'] == 'fold'
        result = until(ws, 'GAME_ENDED')
        assert sum(p['stack'] for p in result['finalState']['players']) == sum(session.game.hand_start_stacks.values())


def test_human_timeout_checks_when_no_bet_is_due(client):
    game = create(client)
    session = main.active_games[game['gameId']]['session']
    session.config['game']['human_timeout_ms'] = 100
    with connect(client, game) as ws:
        auth(ws, game)
        request = until(ws, 'PLAYER_ACTION_REQUEST')
        ws.send_json({'type': 'ACTION', 'requestId': request['requestId'], 'action': 'call'})
        flop_request = until(ws, 'PLAYER_ACTION_REQUEST')
        assert flop_request['callAmount'] == 0
        action = until(ws, 'PLAYER_ACTION')
        assert action['playerId'] == 'player_human'
        assert action['action'] == 'check'
