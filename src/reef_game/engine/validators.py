from .actions import PlaceCoralAction
from .enums import ActionType
from .state import get_cell


class InvalidActionError(Exception):
    pass


def validate_action(state, action) -> None:
    if state.is_terminal:
        raise InvalidActionError("Game already ended.")

    if action.action_type == ActionType.PASS:
        return

    if action.action_type == ActionType.PLACE_CORAL:
        _validate_place_coral(state, action)
        return

    raise InvalidActionError(f"Unsupported action type: {action.action_type}")


def _validate_place_coral(state, action: PlaceCoralAction) -> None:
    player = state.players[state.active_player]

    if action.coral_id not in state.available_corals:
        raise InvalidActionError("Unknown coral_id.")

    coral = state.available_corals[action.coral_id]
    x, y, z = action.position

    if not (0 <= x < state.board.width and 0 <= y < state.board.height and 0 <= z < state.board.max_layers):
        raise InvalidActionError("Position out of bounds.")

    cell = get_cell(state.board, action.position)
    if cell.occupant is not None:
        raise InvalidActionError("Cell already occupied.")

    for resource, cost_value in coral.cost.values.items():
        if player.resources.get(resource, 0) < cost_value:
            raise InvalidActionError(f"Insufficient resource: {resource.value}")

    if coral.requires_support and z > 0:
        below = get_cell(state.board, (x, y, z - 1))
        if below.occupant is None:
            raise InvalidActionError("Coral requires support below.")
