import pytest

from reef_game.engine.actions import BuyFloraAction
from reef_game.engine.enums import PlayerId
from reef_game.engine.models import MAX_HAND_SIZE
from reef_game.engine.transitions import apply_action
from reef_game.engine.validators import InvalidActionError, validate_action


def test_buy_flora_draws_two_cards_into_hand(initial_state):
    deck_before = len(initial_state.flora_deck)

    s = apply_action(initial_state, BuyFloraAction())

    assert len(s.players[PlayerId.P1].hand) == 2
    assert len(s.flora_deck) == deck_before - 2
    assert s.active_player == PlayerId.P2


def test_buy_flora_respects_hand_limit_partial_draw(initial_state):
    # Hand has 9 -> buying 2 only draws 1 (cap is 10), second is not bought.
    initial_state.players[PlayerId.P1].hand = ["x"] * 9
    deck_before = len(initial_state.flora_deck)

    s = apply_action(initial_state, BuyFloraAction())

    assert len(s.players[PlayerId.P1].hand) == MAX_HAND_SIZE  # 10
    assert len(s.flora_deck) == deck_before - 1  # only one card left the deck


def test_buy_flora_illegal_when_hand_full(initial_state):
    initial_state.players[PlayerId.P1].hand = ["x"] * MAX_HAND_SIZE
    with pytest.raises(InvalidActionError):
        validate_action(initial_state, BuyFloraAction())


def test_buy_flora_illegal_when_deck_empty(initial_state):
    initial_state.flora_deck = []
    with pytest.raises(InvalidActionError):
        validate_action(initial_state, BuyFloraAction())
