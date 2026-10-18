import random
import math
import pytest
from game_engine import GameEngine, Player, PlayerStatus, GamePhase, Action, ActionType


def table(stacks=(1000, 1000, 1000)):
    game = GameEngine([Player(str(i), str(i), stack) for i, stack in enumerate(stacks)])
    game.deal_hole_cards()
    game.post_blinds()
    return game


def act(game, kind, amount=0):
    player = game.get_action_order()[0]
    assert game.process_action(Action(player.id, kind, amount))
    return player


def test_heads_up_blinds_and_order():
    game = table((1000, 1000))
    assert [(p.position, p.current_bet) for p in game.players] == [("BTN/SB", 10), ("BB", 20)]
    assert game.get_action_order()[0].id == "0"
    act(game, ActionType.CALL)
    act(game, ActionType.CHECK)
    assert game.is_betting_round_complete()
    game.advance_phase()
    assert game.get_action_order()[0].id == "1"


def test_short_stack_raise_cannot_lower_bet_and_allin_can_call():
    game = table((1000, 30, 1000))
    act(game, ActionType.RAISE, 100)
    short = game.players[1]
    before = (short.stack, game.pot, len(game.action_history))
    assert not game.process_action(Action(short.id, ActionType.RAISE, 100))
    assert (short.stack, game.pot, len(game.action_history)) == before
    act(game, ActionType.ALLIN)
    assert game.street_bet == 100
    assert short.current_bet == 30
    act(game, ActionType.CALL)
    assert game.is_betting_round_complete()


def test_raise_size_uses_last_increment_instead_of_doubling():
    game = table()
    act(game, ActionType.RAISE, 100)  # increase of 80
    assert game.minimum_raise_to() == 180
    act(game, ActionType.RAISE, 180)
    assert game.minimum_raise_to() == 260


def test_short_allin_does_not_reopen_betting_for_previous_actor():
    game = table((1000, 130, 1000))
    act(game, ActionType.RAISE, 100)
    act(game, ActionType.ALLIN)  # 30 increase < previous full raise of 80
    act(game, ActionType.CALL)
    p = game.get_action_order()[0]
    assert p.id == "0"
    assert ActionType.RAISE not in game.get_valid_actions(p)
    assert ActionType.ALLIN not in game.get_valid_actions(p)
    act(game, ActionType.CALL)
    assert game.is_betting_round_complete()


def test_cumulative_short_allins_reopen_betting():
    game = table((1000, 130, 180, 1000))
    act(game, ActionType.RAISE, 100)  # seat 3 UTG
    act(game, ActionType.CALL)        # seat 0 has acted at 100
    act(game, ActionType.ALLIN)       # seat 1 raises to 130
    act(game, ActionType.ALLIN)       # seat 2 raises to 180
    assert game.get_action_order()[0].id == "3"
    assert ActionType.RAISE in game.get_valid_actions(game.players[3])
    act(game, ActionType.CALL)
    assert ActionType.RAISE in game.get_valid_actions(game.players[0])


def test_late_raise_resumes_at_next_pending_seat():
    game = table((1000,) * 4)
    act(game, ActionType.CALL)  # 3
    act(game, ActionType.CALL)  # 0
    act(game, ActionType.RAISE, 100)  # 1 SB
    assert [p.id for p in game.get_action_order()] == ["2", "3", "0"]
    act(game, ActionType.CALL)
    act(game, ActionType.CALL)
    act(game, ActionType.CALL)
    assert game.get_action_order() == []


@pytest.mark.parametrize('amount', [-10, math.nan, math.inf, '100', True, 10 ** 400])
def test_malformed_raise_has_no_side_effects(amount):
    game = table()
    snapshot = game.get_state_snapshot()
    assert not game.process_action(Action('0', ActionType.RAISE, amount))
    assert game.get_state_snapshot() == snapshot
    assert not game.action_history


def test_out_of_turn_rejected():
    game = table()
    assert not game.process_action(Action('2', ActionType.FOLD))
    assert game.players[2].status == PlayerStatus.ACTIVE


def test_eliminated_seats_are_skipped_for_button_blinds_and_positions():
    game = table((1000,) * 4)
    game.players[1].stack = 0
    game.reset_for_new_hand()
    assert game.dealer_idx == 2
    game.deal_hole_cards()
    game.post_blinds()
    assert game.players[1].position == ''
    assert game.players[3].current_bet == 10
    assert game.players[0].current_bet == 20
    assert game.get_action_order()[0].id == '2'


def test_short_big_blind_does_not_force_extra_bet_against_allin():
    game = table((1000, 5))
    assert game.get_action_order() == []
    assert game.is_betting_round_complete()


def test_snapshots_hide_other_cards_and_mucked_cards():
    game = table()
    assert all(not p['holeCards'] for p in game.get_state_snapshot()['players'])
    view = game.get_state_snapshot('0')
    assert len(view['players'][0]['holeCards']) == 2
    assert not view['players'][1]['holeCards']
    game.players[1].status = PlayerStatus.FOLDED
    game.phase = GamePhase.SHOWDOWN
    view = game.get_state_snapshot('0')
    assert not view['players'][1]['holeCards']
    assert len(view['players'][2]['holeCards']) == 2


def test_payout_is_idempotent():
    game = table()
    act(game, ActionType.FOLD)
    act(game, ActionType.FOLD)
    first = game.determine_winners()
    stacks = [p.stack for p in game.players]
    assert game.determine_winners() == first
    assert [p.stack for p in game.players] == stacks
    assert sum(stacks) == 3000


def test_blinds_cannot_be_posted_twice():
    game = table()
    with pytest.raises(ValueError):
        game.post_blinds()
    assert game.pot == 30


def test_random_complete_hands_conserve_chips_and_terminate():
    rng = random.Random(7)
    for _ in range(80):
        game = table(tuple(rng.randint(1, 300) for _ in range(rng.randint(2, 9))))
        total = sum(p.stack for p in game.players) + game.pot
        count = 0
        while game.phase != GamePhase.SHOWDOWN and len(game.non_folded_players()) > 1:
            actors = game.get_action_order()
            if not actors:
                game.advance_phase()
                continue
            player = actors[0]
            kind = rng.choice(game.get_valid_actions(player))
            amount = game.minimum_raise_to() if kind == ActionType.RAISE else 0
            assert game.process_action(Action(player.id, kind, amount))
            assert sum(p.stack for p in game.players) + game.pot == pytest.approx(total)
            assert all(p.stack >= 0 for p in game.players)
            count += 1
            assert count < 300
        game.determine_winners()
        assert sum(p.stack for p in game.players) == pytest.approx(total)


def test_multiple_side_pots_have_one_final_settlement_per_player():
    from hand_evaluator import Card
    game = table((100, 200, 300))
    game.players[0].hole_cards = [Card(2, 0), Card(3, 1)]
    game.players[1].hole_cards = [Card(14, 0), Card(14, 1)]
    game.players[2].hole_cards = [Card(4, 0), Card(5, 1)]
    game.community_cards = [Card(14, 2), Card(13, 3), Card(9, 0), Card(8, 1), Card(7, 2)]
    act(game, ActionType.ALLIN)
    act(game, ActionType.ALLIN)
    act(game, ActionType.CALL)  # No opponent has chips left to match another raise.
    game.phase = GamePhase.SHOWDOWN
    rows = game.determine_winners()
    assert len({r['playerId'] for r in rows}) == len(rows) == 3
    row = next(r for r in rows if r['playerId'] == '1')
    assert row['amount'] == 500
    assert row['stackChange'] == 300
    assert sum(r['amount'] for r in rows) == 500
