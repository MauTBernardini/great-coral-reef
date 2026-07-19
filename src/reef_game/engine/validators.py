from .actions import (
    BuyCoralsAction,
    PlaceCoralAction,
    PlaceSoilAction,
    PlaceStaghornPairAction,
)
from .economy import effective_cost
from .enums import ActionType, ResourceType
from .models import MAX_HAND_SIZE
from .scoring import same_layer_neighbors
from .state import get_cell

STAGHORN_ID = "staghorn"
STAGHORN_PAIR_PLANKTON_SURCHARGE = 1


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

    if action.action_type == ActionType.PLACE_STAGHORN_PAIR:
        _validate_staghorn_pair(state, action)
        return

    if action.action_type == ActionType.PLACE_SOIL:
        _validate_place_soil(state, action)
        return

    if action.action_type == ActionType.BUY_CORALS:
        _validate_buy_corals(state, action)
        return

    raise InvalidActionError(f"Unsupported action type: {action.action_type}")


def _validate_place_soil(state, action: PlaceSoilAction) -> None:
    # Afordabilidade NÃO é validada aqui de propósito: se o topo da pilha for caro
    # demais, a ação é permitida mas perdida (tratada em transitions).
    if not state.soil_pile:
        raise InvalidActionError("Soil purchase pile is empty.")

    x, y, z = action.position
    if z != 0:
        raise InvalidActionError("Soil can only be placed on the bottom layer (z=0).")

    if not (0 <= x < state.board.width and 0 <= y < state.board.height):
        raise InvalidActionError("Position out of bounds.")

    cell = get_cell(state.board, action.position)
    if cell.soil is not None:
        raise InvalidActionError("Cell already has a soil tile.")


def _validate_buy_corals(state, action: BuyCoralsAction) -> None:
    player = state.players[state.active_player]

    if not state.coral_deck:
        raise InvalidActionError("Coral deck is empty.")

    if len(player.hand) >= MAX_HAND_SIZE:
        raise InvalidActionError("Hand is full (max 10 cards).")


def _validate_place_coral(
    state, action: PlaceCoralAction, pending=None, check_resources=True, check_hand=True
) -> None:
    """Validate a single placement.

    ``pending`` maps positions to coral_ids that should be treated as already
    occupied (used so the second staghorn of a pair can be supported by / must
    not overlap the first). ``check_resources``/``check_hand`` can be disabled when
    affordability / cartas na mão são checadas em conjunto num multi-placement.
    """
    pending = pending or {}
    player = state.players[state.active_player]

    if action.coral_id not in state.available_corals:
        raise InvalidActionError("Unknown coral_id.")

    if check_hand and action.coral_id not in player.hand:
        raise InvalidActionError(f"Coral card {action.coral_id} is not in hand.")

    coral = state.available_corals[action.coral_id]
    x, y, z = action.position

    in_bounds = (
        0 <= x < state.board.width
        and 0 <= y < state.board.height
        and 0 <= z < state.board.max_layers
    )
    if not in_bounds:
        raise InvalidActionError("Position out of bounds.")

    if coral.allowed_layers is not None and z not in coral.allowed_layers:
        raise InvalidActionError(
            f"Coral {coral.coral_id} cannot be placed on layer {z}."
        )

    cell = get_cell(state.board, action.position)
    if cell.occupant is not None or action.position in pending:
        raise InvalidActionError("Cell already occupied.")

    base_cell = get_cell(state.board, (x, y, 0))
    if base_cell.soil is None:
        raise InvalidActionError("Coral requires a soil tile at the column base (z=0).")

    if coral.required_soil is not None and base_cell.soil.soil_id != coral.required_soil:
        raise InvalidActionError(
            f"Coral {coral.coral_id} can only be built on {coral.required_soil} soil."
        )

    # Fox Coral: bloqueia construção de oponentes em células vizinhas (mesma camada).
    for neighbor_pos in same_layer_neighbors(action.position):
        neighbor = state.board.cells.get(neighbor_pos)
        if neighbor is None or neighbor.occupant is None:
            continue
        occupant = neighbor.occupant
        if occupant.owner == state.active_player:
            continue
        occupant_def = state.available_corals.get(occupant.coral_id)
        if occupant_def is not None and occupant_def.blocks_opponent_adjacent:
            raise InvalidActionError("Cell borders an opponent's Fox Coral (blocked).")

    if check_resources:
        cost = effective_cost(state, coral, action.position)
        for resource, cost_value in cost.items():
            if player.resources.get(resource, 0) < cost_value:
                raise InvalidActionError(f"Insufficient resource: {resource.value}")

    if coral.requires_support and z > 0:
        below_position = (x, y, z - 1)
        below = get_cell(state.board, below_position)
        if below.occupant is None and below_position not in pending:
            raise InvalidActionError("Coral requires support below.")


def _validate_staghorn_pair(state, action: PlaceStaghornPairAction) -> None:
    if action.first_position == action.second_position:
        raise InvalidActionError("Staghorn pair positions must differ.")

    player = state.players[state.active_player]

    # Precisa de 2 cartas de staghorn na mão (uma por peça).
    if player.hand.count(STAGHORN_ID) < 2:
        raise InvalidActionError("Need 2 staghorn cards in hand for the pair.")

    first = PlaceCoralAction(STAGHORN_ID, action.first_position)
    second = PlaceCoralAction(STAGHORN_ID, action.second_position)

    # Structural checks (bounds/layer/support/occupancy) with resources/hand deferred
    # to the joint checks. The second staghorn may lean on the first.
    _validate_place_coral(state, first, check_resources=False, check_hand=False)
    _validate_place_coral(
        state,
        second,
        pending={action.first_position: STAGHORN_ID},
        check_resources=False,
        check_hand=False,
    )

    coral = state.available_corals[STAGHORN_ID]
    combined: dict = {}
    for position in (action.first_position, action.second_position):
        for resource, amount in effective_cost(state, coral, position).items():
            combined[resource] = combined.get(resource, 0) + amount
    combined[ResourceType.PLANKTON] = (
        combined.get(ResourceType.PLANKTON, 0) + STAGHORN_PAIR_PLANKTON_SURCHARGE
    )

    for resource, cost_value in combined.items():
        if player.resources.get(resource, 0) < cost_value:
            raise InvalidActionError(
                f"Insufficient resource for staghorn pair: {resource.value}"
            )
