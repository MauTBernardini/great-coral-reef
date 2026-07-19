from reef_game.engine.actions import PlaceCoralAction
from reef_game.engine.enums import PlayerId, ResourceType
from reef_game.engine.transitions import apply_action


def test_place_coral_updates_resources_board_and_score(soiled_state):
    action = PlaceCoralAction("grooved_brain_coral", (0, 0, 0))
    next_state = apply_action(soiled_state, action)

    placed = next_state.board.cells[(0, 0, 0)].occupant
    assert placed is not None
    assert placed.owner == PlayerId.P1
    assert next_state.players[PlayerId.P1].resources[ResourceType.SUN] == 8
    assert next_state.players[PlayerId.P1].resources[ResourceType.PLANKTON] == 10
    # Grooved Brain: 1 base + 0 corals above it.
    assert next_state.players[PlayerId.P1].score == 1
    assert next_state.active_player == PlayerId.P2
