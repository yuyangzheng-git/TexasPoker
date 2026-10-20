"""One game task per table; sockets only authenticate, display and submit commands."""
import asyncio
import secrets
import time
from starlette.websockets import WebSocketDisconnect

from game_engine import Action, ActionType, GamePhase
from opponent_model import PublicStatsTracker


class GameSession:
    def __init__(self, game, agents, config, logger):
        self.game = game
        self.agents = agents
        self.tracker = PublicStatsTracker()
        for agent in agents.values():
            if hasattr(agent, "attach_tracker"):
                agent.attach_tracker(self.tracker)
        self.config = config
        self.logger = logger
        self.token = secrets.token_urlsafe(32)
        self.socket = None
        self.task = None
        self.ready = asyncio.Event()
        self.ready.set()
        self.commands = asyncio.Queue(maxsize=1)
        self.pending = None
        self.result = None
        self.thoughts = []
        self.last_seen = time.monotonic()
        self.finished = False
        self.human_id = next(p.id for p in game.players if p.player_type == "human")

    def snapshot(self):
        return self.game.get_state_snapshot(self.human_id)

    def human_busted(self):
        return self.game._get_player(self.human_id).stack <= 0

    def session_over(self):
        # A single-human practice table ends once the human is out, even if AIs remain.
        return self.human_busted() or len([p for p in self.game.players if p.stack > 0]) <= 1

    async def send(self, event, data):
        if self.socket is not None:
            try:
                await self.socket.send_json({"type": event, "data": data})
            except (RuntimeError, OSError, WebSocketDisconnect):
                # The endpoint detaches the failed transport; keep ownership until then.
                pass

    async def replay(self):
        pending = dict(self.pending) if self.pending else None
        if pending and pending["kind"] == "action":
            pending["timeLimit"] = max(0, int((pending["deadline"] - time.monotonic()) * 1000))
        await self.send("SESSION_STATE", {
            "state": self.snapshot(), "paused": not self.ready.is_set(),
            "pendingAction": pending, "result": self.result, "finished": self.finished,
        })

    async def command(self, message):
        if not isinstance(message, dict):
            await self.send("ERROR", {"message": "Invalid command"})
            return
        self.last_seen = time.monotonic()
        kind = message.get("type")
        if kind in ("PAUSE", "RESUME"):
            self.ready.clear() if kind == "PAUSE" else self.ready.set()
            await self.send("PAUSE_STATE", {"paused": not self.ready.is_set()})
            return
        pending = self.pending
        if not pending or message.get("requestId") != pending["requestId"]:
            await self.send("ERROR", {"message": "Expired or unexpected action"})
            return
        if pending["kind"] == "ready" and kind != "READY_FOR_NEXT_HAND":
            return
        if pending["kind"] == "action" and kind != "ACTION":
            return
        if self.commands.empty():
            self.commands.put_nowait(message)

    def new_request(self, kind, timeout):
        while not self.commands.empty():
            self.commands.get_nowait()
        self.pending = {
            "kind": kind, "requestId": secrets.token_urlsafe(16),
            "deadline": time.monotonic() + timeout,
        }
        return self.pending

    async def human_action(self, player):
        timeout = self.config["game"]["human_timeout_ms"] / 1000
        request = self.new_request("action", timeout)
        request.update({
            "playerId": player.id,
            "validActions": [a.value for a in self.game.get_valid_actions(player)],
            "callAmount": min(player.stack, max(0, self.game.street_bet - player.current_bet)),
            "minRaise": self.game.minimum_raise_to(),
            "maxRaise": player.current_bet + player.stack,
            "pot": self.game.pot, "timeLimit": timeout * 1000,
        })
        await self.send("PLAYER_ACTION_REQUEST", request)
        try:
            while True:
                remaining = request["deadline"] - time.monotonic()
                if remaining <= 0:
                    raise asyncio.TimeoutError
                message = await asyncio.wait_for(self.commands.get(), remaining)
                try:
                    action = Action(player.id, ActionType(message.get("action")), message.get("amount", 0))
                    speech = message.get("speech", "")
                    if not isinstance(speech, str) or len(speech) > 200:
                        raise ValueError("Invalid speech")
                    if not self.game.process_action(action):
                        raise ValueError("Illegal action or raise amount")
                    return action, speech
                except (ValueError, TypeError):
                    await self.send("ERROR", {"message": "Illegal action; please choose again"})
        except asyncio.TimeoutError:
            kind = ActionType.CHECK if player.current_bet >= self.game.street_bet else ActionType.FOLD
            action = Action(player.id, kind)
            if not self.game.process_action(action):
                raise RuntimeError("Timeout action rejected")
            return action, ""
        finally:
            self.pending = None

    async def wait_for_next_hand(self):
        request = self.new_request("ready", 300)
        self.result["requestId"] = request["requestId"]
        await self.send(self.result["event"], self.result)
        try:
            await asyncio.wait_for(self.commands.get(), 300)
        except asyncio.TimeoutError:
            pass
        finally:
            self.pending = None

    async def run(self):
        hand_number = 0
        try:
            while not self.session_over():
                # Do not spend API calls on an abandoned table.
                while self.socket is None:
                    await asyncio.sleep(0.2)
                await self.ready.wait()
                if hand_number:
                    self.game.reset_for_new_hand()
                hand_number += 1
                self.result = None
                self.thoughts = []
                self.game.deal_hole_cards()
                self.game.post_blinds()
                self.tracker.start_hand(self.game)
                self.logger.log_hand_start(hand_number, self.game.dealer_idx, [
                    {"id": p.id, "name": p.name, "stack": p.stack, "position": p.position,
                     "hole_cards": [c.to_string() for c in p.hole_cards]} for p in self.game.players
                ])
                self.logger.log_phase_change("pre_flop", [], self.game.pot)
                event = "GAME_STARTED" if hand_number == 1 else "HAND_STARTED"
                await self.send(event, self.snapshot() if hand_number == 1 else {
                    "handNumber": hand_number, "gameState": self.snapshot(),
                })
                while self.game.phase != GamePhase.SHOWDOWN and len(self.game.non_folded_players()) > 1:
                    await self.ready.wait()
                    actors = self.game.get_action_order()
                    if not actors:
                        self.game.advance_phase()
                        self.tracker.observe_phase(self.game)
                        self.logger.log_phase_change(self.game.phase.value,
                            [c.to_string() for c in self.game.community_cards], self.game.pot)
                        await self.send("PHASE_CHANGED", self.snapshot())
                        continue
                    player = actors[0]
                    thinking = ""
                    if player.player_type == "human":
                        action, speech = await self.human_action(player)
                    else:
                        await self.send("AGENT_THINKING_START", {"agentId": player.id})
                        response = await self.agents[player.id].decide(
                            self.game, timeout=self.config["game"]["agent_timeout_ms"] / 1000,
                        )
                        # Reasoning may name private cards. Reveal it only after this hand ends.
                        thinking = response.thinking
                        self.thoughts.append((player.id, thinking, response.speech))
                        action = response.action
                        if action is None or not self.game.process_action(action):
                            kind = ActionType.CHECK if player.current_bet >= self.game.street_bet else ActionType.FOLD
                            action = Action(player.id, kind)
                            if not self.game.process_action(action):
                                raise RuntimeError("Agent fallback rejected")
                        speech = response.speech
                        await self.send("AGENT_THINKING_END", {
                            "agentId": player.id, "action": action.type.value, "speech": speech,
                        })
                    self.tracker.observe(self.game, player.id, action.type)
                    if speech:
                        self.game.record_speech(player.id, speech)
                        self.logger.log_speech(player.id, player.name, speech, self.game.phase.value)
                    self.logger.log_player_action(player.id, player.name, action.type.value,
                        action.amount, self.game.phase.value, self.game.pot, player.stack, thinking=thinking)
                    await self.send("PLAYER_ACTION", {
                        "playerId": player.id, "action": action.type.value, "amount": action.amount,
                        "speech": speech, "pot": self.game.pot, "stateSnapshot": self.snapshot(),
                    })
                showdown = self.game.phase == GamePhase.SHOWDOWN
                if showdown:
                    self.logger.log_showdown([
                        {"id": p.id, "name": p.name, "hole_cards": [c.to_string() for c in p.hole_cards]}
                        for p in self.game.non_folded_players()
                    ])
                allocations = self.game.determine_winners()
                self.tracker.end_hand(self.game)
                self.logger.log_hand_result(allocations, self.game.pot)
                for agent_id, thinking, speech in self.thoughts:
                    await self.send("AGENT_THINKING_CHUNK", {"agentId": agent_id, "chunk": thinking})
                    await self.send("AGENT_THINKING_END", {"agentId": agent_id, "speech": speech})
                self.game.phase = GamePhase.SHOWDOWN if showdown else GamePhase.ENDED
                self.result = {
                    "event": "SHOWDOWN" if showdown else "GAME_ENDED",
                    "allocations": allocations, "finalState": self.snapshot(),
                }
                if self.session_over():
                    await self.send(self.result["event"], self.result)
                    break
                await self.wait_for_next_hand()
            self.finished = True
            winner = max(self.game.players, key=lambda p: p.stack)
            self.logger.log_tournament_end(winner.name, {p.id: p.stack for p in self.game.players})
            await self.send("TOURNAMENT_ENDED", {
                "winner": winner.name, "finalStacks": {p.id: p.stack for p in self.game.players},
                "humanBusted": self.human_busted(),
            })
        except asyncio.CancelledError:
            raise
        except Exception:
            self.finished = True
            await self.send("ERROR", {"message": "Game stopped; reconnect to view its last state"})
            import logging
            logging.exception("Game task failed")
        finally:
            self.pending = None
