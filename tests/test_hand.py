import pytest

from reef_game.engine.actions import BuyCoralsAction
from reef_game.engine.enums import PlayerId
from reef_game.engine.models import MAX_HAND_SIZE, STARTING_HAND_SIZE
from reef_game.engine.transitions import apply_action
from reef_game.engine.validators import InvalidActionError, validate_action


def test_players_start_with_a_hand_of_coral_cards(initial_state):
    for pid in (PlayerId.P1, PlayerId.P2):
        assert len(initial_state.players[pid].hand) == STARTING_HAND_SIZE
    # As cartas iniciais são corais válidos.
    assert all(c in initial_state.available_corals for c in initial_state.players[PlayerId.P1].hand)


def test_buy_corals_draws_two_cards_into_hand(initial_state):
    hand_before = len(initial_state.players[PlayerId.P1].hand)
    deck_before = len(initial_state.coral_deck)

    s = apply_action(initial_state, BuyCoralsAction())

    assert len(s.players[PlayerId.P1].hand) == hand_before + 2
    assert len(s.coral_deck) == deck_before - 2
    assert s.active_player == PlayerId.P2


def test_buy_corals_respects_hand_limit_partial_draw(initial_state):
    # Mão com 9 -> comprar 2 saca só 1 (teto 10); a segunda não é comprada.
    initial_state.players[PlayerId.P1].hand = ["staghorn"] * 9
    deck_before = len(initial_state.coral_deck)

    s = apply_action(initial_state, BuyCoralsAction())

    assert len(s.players[PlayerId.P1].hand) == MAX_HAND_SIZE  # 10
    assert len(s.coral_deck) == deck_before - 1


def test_buy_corals_illegal_when_hand_full(initial_state):
    initial_state.players[PlayerId.P1].hand = ["staghorn"] * MAX_HAND_SIZE
    with pytest.raises(InvalidActionError):
        validate_action(initial_state, BuyCoralsAction())


def test_buy_corals_illegal_when_deck_empty(initial_state):
    initial_state.coral_deck = []
    with pytest.raises(InvalidActionError):
        validate_action(initial_state, BuyCoralsAction())
