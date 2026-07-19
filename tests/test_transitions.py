from reef_game.engine.actions import PlaceCoralAction
from reef_game.engine.enums import PlayerId, ResourceType
from reef_game.engine.transitions import apply_action


def test_place_coral_updates_resources_board_and_score(soiled_state):
    sun0 = soiled_state.players[PlayerId.P1].resources[ResourceType.SUN]
    plk0 = soiled_state.players[PlayerId.P1].resources[ResourceType.PLANKTON]
    next_state = apply_action(soiled_state, PlaceCoralAction("grooved_brain_coral", (0, 0, 0)))

    placed = next_state.board.cells[(0, 0, 0)].occupant
    assert placed is not None
    assert placed.owner == PlayerId.P1
    assert next_state.players[PlayerId.P1].resources[ResourceType.SUN] == sun0 - 2  # brain = 2 Sun
    assert next_state.players[PlayerId.P1].resources[ResourceType.PLANKTON] == plk0
    # Grooved Brain: 1 base + 0 corals above it.
    assert next_state.players[PlayerId.P1].score == 1
    assert next_state.active_player == PlayerId.P2
