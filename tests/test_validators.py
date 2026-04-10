import pytest

from reef_game.engine.actions import PlaceCoralAction
from reef_game.engine.validators import InvalidActionError, validate_action


def test_cannot_place_out_of_bounds(initial_state):
    action = PlaceCoralAction("staghorn", (999, 0, 0))
    with pytest.raises(InvalidActionError):
        validate_action(initial_state, action)


def test_cannot_place_without_support(initial_state):
    action = PlaceCoralAction("staghorn", (1, 1, 1))
    with pytest.raises(InvalidActionError):
        validate_action(initial_state, action)


def test_can_place_on_ground(initial_state):
    action = PlaceCoralAction("staghorn", (1, 1, 0))
    validate_action(initial_state, action)
