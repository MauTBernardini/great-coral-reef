from .engine_types import NeighborPositions


def orthogonal_neighbors(position):
    x, y, z = position
    return NeighborPositions(
        same_layer=[
            (x + 1, y, z),
            (x - 1, y, z),
            (x, y + 1, z),
            (x, y - 1, z),
        ]
    )


def score_incremental_after_placement(state, placed_coral) -> int:
    coral = state.available_corals[placed_coral.coral_id]
    points = coral.base_points

    x, y, z = placed_coral.position

    if z > 0:
        points += 1

    for pos in orthogonal_neighbors((x, y, z)).same_layer:
        cell = state.board.cells.get(pos)
        if cell and cell.occupant is not None and cell.occupant.owner == placed_coral.owner:
            points += 1

    return points
