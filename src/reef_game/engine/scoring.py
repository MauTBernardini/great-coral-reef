"""Per-coral scoring.

Score is recomputed from the full board after every placement, because several
coral scores depend on the current board configuration (corals stacked above,
neighbouring corals, whether a coral sits on the top layer) and therefore change
as the game progresses.
"""

STAGHORN_ID = "staghorn"
ELKHORN_ID = "elkhorn"
GROOVED_BRAIN_ID = "grooved_brain_coral"
FOX_ID = "fox_coral"
SUN_CORAL_ID = "sun_coral"
GORGONIAN_ID = "gorgonian_sea_fan"
BRANCHED_FINGER_ID = "branched_finger_coral"
BUBBLE_ID = "bubble_coral"


def orthogonal_neighbors_3d(position):
    """The six face-adjacent cells (same layer + directly above/below)."""
    x, y, z = position
    return [
        (x + 1, y, z),
        (x - 1, y, z),
        (x, y + 1, z),
        (x, y - 1, z),
        (x, y, z + 1),
        (x, y, z - 1),
    ]


def same_layer_neighbors(position):
    """The four cells sharing an edge on the same layer."""
    x, y, z = position
    return [(x + 1, y, z), (x - 1, y, z), (x, y + 1, z), (x, y - 1, z)]


def _count_empty_same_layer_neighbors(state, position) -> int:
    count = 0
    for pos in same_layer_neighbors(position):
        cell = state.board.cells.get(pos)
        if cell is not None and cell.occupant is None:
            count += 1
    return count


def _count_gorgonians_in_column(state, position, owner) -> int:
    x, y, _ = position
    count = 0
    for zz in range(state.board.max_layers):
        cell = state.board.cells.get((x, y, zz))
        if (
            cell is not None
            and cell.occupant is not None
            and cell.occupant.coral_id == GORGONIAN_ID
            and cell.occupant.owner == owner
        ):
            count += 1
    return count


def _distinct_same_layer_coral_types(state, position) -> int:
    types = set()
    for pos in same_layer_neighbors(position):
        cell = state.board.cells.get(pos)
        if cell is not None and cell.occupant is not None:
            types.add(cell.occupant.coral_id)
    return len(types)


def _count_corals_above(state, position) -> int:
    x, y, z = position
    count = 0
    for zz in range(z + 1, state.board.max_layers):
        cell = state.board.cells.get((x, y, zz))
        if cell is not None and cell.occupant is not None:
            count += 1
    return count


def _count_connected_staghorns(state, position, owner) -> int:
    count = 0
    for pos in orthogonal_neighbors_3d(position):
        cell = state.board.cells.get(pos)
        if (
            cell is not None
            and cell.occupant is not None
            and cell.occupant.coral_id == STAGHORN_ID
            and cell.occupant.owner == owner
        ):
            count += 1
    return count


def score_coral(state, placed_coral) -> int:
    """Points a single coral is worth given the current board.

    Reads only *other* cells (never its own), so it yields the same value whether
    or not ``placed_coral`` is already committed to the board. That lets agents
    call it as an immediate-value estimate before actually placing.
    """
    coral_id = placed_coral.coral_id
    x, y, z = placed_coral.position
    top_layer = state.board.max_layers - 1

    if coral_id == GROOVED_BRAIN_ID:
        # 1 base + 1 per coral stacked above it.
        return 1 + _count_corals_above(state, placed_coral.position)

    if coral_id == ELKHORN_ID:
        # 2 points only while it sits on the topmost layer.
        return 2 if z == top_layer else 0

    if coral_id == STAGHORN_ID:
        # 1 per directly-connected staghorn of the same owner, counting itself.
        return 1 + _count_connected_staghorns(state, placed_coral.position, placed_coral.owner)

    if coral_id == FOX_ID:
        # 2 pontos por tile vizinho (mesma camada) vazio.
        return 2 * _count_empty_same_layer_neighbors(state, placed_coral.position)

    if coral_id == SUN_CORAL_ID:
        return 5

    if coral_id == GORGONIAN_ID:
        # 2 por Gorgonian (mesmo dono) na coluna vertical (conta a si mesmo quando no board).
        return 2 * _count_gorgonians_in_column(state, placed_coral.position, placed_coral.owner)

    if coral_id == BRANCHED_FINGER_ID:
        return 1

    if coral_id == BUBBLE_ID:
        # 2 se adjacente (mesma camada) a pelo menos 2 tipos diferentes de coral.
        return 2 if _distinct_same_layer_coral_types(state, placed_coral.position) >= 2 else 0

    # Fallback for any future coral without a bespoke rule.
    coral = state.available_corals[coral_id]
    points = coral.base_points
    if z > 0:
        points += 1
    for pos in orthogonal_neighbors_3d(placed_coral.position):
        cell = state.board.cells.get(pos)
        if cell is None or cell.occupant is None:
            continue
        if cell.occupant.owner == placed_coral.owner:
            points += 1
    return points


def compute_player_score(state, player_id) -> int:
    total = 0
    for cell in state.board.cells.values():
        occupant = cell.occupant
        if occupant is not None and occupant.owner == player_id:
            total += score_coral(state, occupant)
    return total


def recompute_scores(state) -> None:
    """Refresh every player's score from the current board."""
    for player_id, player in state.players.items():
        player.score = compute_player_score(state, player_id)
