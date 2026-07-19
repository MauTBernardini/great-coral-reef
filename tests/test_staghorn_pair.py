import pytest

from reef_game.engine.actions import PlaceCoralAction, PlaceStaghornPairAction
from reef_game.engine.enums import PlayerId, ResourceType
from reef_game.engine.transitions import apply_action
from reef_game.engine.validators import InvalidActionError, validate_action


def _setup_two_supports(soiled_state):
    # P1 builds two ground supports; P2 plays elsewhere. Back to P1 ready to pair.
    s = apply_action(soiled_state, PlaceCoralAction("grooved_brain_coral", (0, 0, 0)))  # P1
    s = apply_action(s, PlaceCoralAction("grooved_brain_coral", (3, 3, 0)))              # P2
    s = apply_action(s, PlaceCoralAction("grooved_brain_coral", (1, 0, 0)))              # P1
    s = apply_action(s, PlaceCoralAction("grooved_brain_coral", (3, 2, 0)))              # P2
    return s


def test_staghorn_pair_places_two_corals_in_one_turn(soiled_state):
    s = _setup_two_supports(soiled_state)
    plankton_before = s.players[PlayerId.P1].resources[ResourceType.PLANKTON]

    s = apply_action(s, PlaceStaghornPairAction((0, 0, 1), (1, 0, 1)))  # P1 pair

    assert s.board.cells[(0, 0, 1)].occupant.coral_id == "staghorn"
    assert s.board.cells[(1, 0, 1)].occupant.coral_id == "staghorn"
    # +1 Plankton surcharge for the second staghorn.
    assert s.players[PlayerId.P1].resources[ResourceType.PLANKTON] == plankton_before - 1
    # Only one action was spent: it is P2's turn now.
    assert s.active_player == PlayerId.P2


def test_staghorn_pair_rejected_without_enough_plankton(soiled_state):
    s = _setup_two_supports(soiled_state)
    s.players[PlayerId.P1].resources[ResourceType.PLANKTON] = 0

    with pytest.raises(InvalidActionError):
        validate_action(s, PlaceStaghornPairAction((0, 0, 1), (1, 0, 1)))


def test_staghorn_pair_rejects_identical_positions(soiled_state):
    s = _setup_two_supports(soiled_state)

    with pytest.raises(InvalidActionError):
        validate_action(s, PlaceStaghornPairAction((0, 0, 1), (0, 0, 1)))
