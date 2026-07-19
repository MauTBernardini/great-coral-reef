"""Production phase.

Runs once at the start of every round (right after the climate tick). Each coral
yields its base ``production`` (from config, empty by default) plus any ability
bonuses. Today the only ability contributor is the Elkhorn cluster bonus.
"""

from .enums import ResourceType

ELKHORN_ID = "elkhorn"


def _same_layer_orthogonal_neighbors(position):
    x, y, z = position
    return [(x + 1, y, z), (x - 1, y, z), (x, y + 1, z), (x, y - 1, z)]


def _adjacent_top_elkhorns(state, position, owner) -> int:
    """Same-owner elkhorns orthogonally adjacent on the same (top) layer."""
    count = 0
    for pos in _same_layer_orthogonal_neighbors(position):
        cell = state.board.cells.get(pos)
        if (
            cell is not None
            and cell.occupant is not None
            and cell.occupant.coral_id == ELKHORN_ID
            and cell.occupant.owner == owner
        ):
            count += 1
    return count


def resolve_production(state) -> dict:
    """Grant production to every player. Returns the per-player gains granted."""
    top_layer = state.board.max_layers - 1
    gains = {
        player_id: {ResourceType.SUN: 0, ResourceType.PLANKTON: 0}
        for player_id in state.players
    }

    for cell in state.board.cells.values():
        # Solo produz para o dono do tile.
        if cell.soil is not None:
            soil = state.available_soils.get(cell.soil.soil_id)
            if soil is not None:
                for resource, amount in soil.production.items():
                    gains[cell.soil.owner][resource] += amount

        occupant = cell.occupant
        if occupant is None:
            continue

        coral = state.available_corals[occupant.coral_id]
        for resource, amount in coral.production.items():
            gains[occupant.owner][resource] += amount

        # Elkhorn ability: on the top layer, adjacent to >=2 same-owner top-layer
        # elkhorns -> +1 Sun production.
        if occupant.coral_id == ELKHORN_ID and occupant.position[2] == top_layer:
            if _adjacent_top_elkhorns(state, occupant.position, occupant.owner) >= 2:
                gains[occupant.owner][ResourceType.SUN] += 1

    for player_id, player in state.players.items():
        for resource, amount in gains[player_id].items():
            if amount:
                player.resources[resource] = player.resources.get(resource, 0) + amount
                player.produced_resources[resource] = (
                    player.produced_resources.get(resource, 0) + amount
                )

    return gains
