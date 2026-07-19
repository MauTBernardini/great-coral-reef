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


CLOWNFISH_ID = "clownfish"
DAMSELFISH_ID = "damselfish"
MANDARIN_ID = "mandarin_dragonet"
SEAHORSE_ID = "seahorse"
PARROTFISH_ID = "parrotfish"
SHARK_ID = "blacktip_reef_shark"
ANTHIAS_ID = "anthias"
GREEN_CHROMIS_ID = "green_chromis"
SEA_CUCUMBER_ID = "sea_cucumber"
MOON_JELLY_ID = "moon_jelly"
SANDY_BED_ID = "sandy_bed"
SEAGRASS_ID = "seagrass_meadow"


def count_adjacent_fauna(state, position, fauna_id, owner) -> int:
    """Quantos ``fauna_id`` (do mesmo dono) há em tiles vizinhos de mesma camada."""
    count = 0
    for pos in same_layer_neighbors(position):
        cell = state.board.cells.get(pos)
        if cell is not None and cell.occupant is not None and cell.occupant.owner == owner:
            count += cell.fauna.count(fauna_id)
    return count


def count_fauna_on_board(state, fauna_id) -> int:
    return sum(cell.fauna.count(fauna_id) for cell in state.board.cells.values())


def has_patrol_neighbor(state, position) -> bool:
    """Há um predador patrulhando numa célula vizinha (mesma camada)?"""
    for pos in same_layer_neighbors(position):
        cell = state.board.cells.get(pos)
        if cell is None:
            continue
        for fauna_id in cell.fauna:
            fauna = state.available_fauna.get(fauna_id)
            if fauna is not None and fauna.patrol:
                return True
    return False


def player_small_fish(state, owner):
    """Lista de (cell, fauna_id) de peixes pequenos do jogador no board."""
    result = []
    for cell in state.board.cells.values():
        occupant = cell.occupant
        if occupant is not None and occupant.owner == owner:
            for fauna_id in cell.fauna:
                fauna = state.available_fauna.get(fauna_id)
                if fauna is not None and fauna.is_small_fish:
                    result.append((cell, fauna_id))
    return result


def fauna_habitat_cost(state, fauna_id, coral_id) -> int:
    """Capacidade que a fauna ocupa no coral. Seahorse em Gorgonian ocupa 0."""
    if fauna_id == SEAHORSE_ID and coral_id == GORGONIAN_ID:
        return 0
    return state.available_fauna[fauna_id].habitat_cost


def occupied_habitat(state, cell) -> int:
    if cell.occupant is None:
        return 0
    coral_id = cell.occupant.coral_id
    return sum(fauna_habitat_cost(state, fauna_id, coral_id) for fauna_id in cell.fauna)


def _count_owned_soil(state, owner, soil_id) -> int:
    return sum(
        1
        for cell in state.board.cells.values()
        if cell.soil is not None and cell.soil.owner == owner and cell.soil.soil_id == soil_id
    )


def _count_adjacent_seagrass(state, position) -> int:
    x, y, _ = position
    count = 0
    for neighbor in [(x + 1, y, 0), (x - 1, y, 0), (x, y + 1, 0), (x, y - 1, 0)]:
        cell = state.board.cells.get(neighbor)
        if cell is not None and cell.soil is not None and cell.soil.soil_id == SEAGRASS_ID:
            count += 1
    return count


def score_fauna(state, fauna_id, position, owner) -> int:
    if fauna_id == CLOWNFISH_ID:
        return 2
    if fauna_id == DAMSELFISH_ID:
        return 1
    if fauna_id == MANDARIN_ID:
        return 5
    if fauna_id == SEAHORSE_ID:
        return _count_adjacent_seagrass(state, position)
    if fauna_id == PARROTFISH_ID:
        return 1 + _count_owned_soil(state, owner, SANDY_BED_ID)
    if fauna_id == SHARK_ID:
        return 3 * _count_empty_same_layer_neighbors(state, position)
    if fauna_id == ANTHIAS_ID:
        return count_adjacent_fauna(state, position, ANTHIAS_ID, owner)
    if fauna_id == GREEN_CHROMIS_ID:
        cell = state.board.cells.get(position)
        on_tile = cell.fauna.count(GREEN_CHROMIS_ID) if cell is not None else 0
        return 2 if on_tile >= 3 else 1
    if fauna_id == SEA_CUCUMBER_ID:
        return count_fauna_on_board(state, SEA_CUCUMBER_ID) // 2
    return state.available_fauna[fauna_id].base_points


def _owned_coral_cells(state, owner):
    return [
        cell for cell in state.board.cells.values()
        if cell.occupant is not None and cell.occupant.owner == owner
    ]


def _instinct_towers_reaching_surface(state, owner) -> int:
    """Torres (colunas) do jogador cujo topo alcança a camada mais de superfície."""
    top = state.board.max_layers - 1
    count = 0
    for x in range(state.board.width):
        for y in range(state.board.height):
            cell = state.board.cells.get((x, y, top))
            if cell is not None and cell.occupant is not None and cell.occupant.owner == owner:
                count += 1
    return count


def _instinct_dominant_coral_type(state, owner) -> int:
    """Nº de tiles do tipo de coral mais numeroso do jogador (sua 'espécie dominante')."""
    counts = {}
    for cell in _owned_coral_cells(state, owner):
        cid = cell.occupant.coral_id
        counts[cid] = counts.get(cid, 0) + 1
    return max(counts.values()) if counts else 0


def _instinct_symbiosis_pairs(state, owner) -> int:
    """Pares coral<->fauna ativados: cada fauna morando num coral do jogador."""
    return sum(len(cell.fauna) for cell in _owned_coral_cells(state, owner))


def _instinct_corals_on_edge(state, owner) -> int:
    """Corais do jogador em colunas da borda do tabuleiro (qualquer camada)."""
    w, h = state.board.width, state.board.height
    count = 0
    for cell in _owned_coral_cells(state, owner):
        x, y, _ = cell.position
        if x == 0 or y == 0 or x == w - 1 or y == h - 1:
            count += 1
    return count


def _instinct_bottom_layer_connected_trios(state, owner) -> int:
    """Grupos completos de 3 corais do jogador conectados (ortogonal) na camada z=0."""
    nodes = {
        (x, y)
        for (x, y, z), cell in state.board.cells.items()
        if z == 0 and cell.occupant is not None and cell.occupant.owner == owner
    }
    seen = set()
    trios = 0
    for start in nodes:
        if start in seen:
            continue
        # BFS na componente conexa.
        stack = [start]
        seen.add(start)
        size = 0
        while stack:
            cx, cy = stack.pop()
            size += 1
            for nx, ny in ((cx + 1, cy), (cx - 1, cy), (cx, cy + 1), (cx, cy - 1)):
                if (nx, ny) in nodes and (nx, ny) not in seen:
                    seen.add((nx, ny))
                    stack.append((nx, ny))
        trios += size // 3
    return trios


def _instinct_full_habitat_corals(state, owner) -> int:
    """Corais do jogador com capacidade habitacional 100% ocupada."""
    count = 0
    for cell in _owned_coral_cells(state, owner):
        cap = state.available_corals[cell.occupant.coral_id].habitat_capacity
        if cap > 0 and occupied_habitat(state, cell) >= cap:
            count += 1
    return count


_INSTINCT_RULES = {
    "towers_reaching_surface": _instinct_towers_reaching_surface,
    "dominant_coral_type": _instinct_dominant_coral_type,
    "symbiosis_pairs": _instinct_symbiosis_pairs,
    "corals_on_edge": _instinct_corals_on_edge,
    "bottom_layer_connected_trios": _instinct_bottom_layer_connected_trios,
    "full_habitat_corals": _instinct_full_habitat_corals,
}


def score_instinct(state, player_id) -> int:
    """Pontos da carta de Instinto escolhida pelo jogador (0 se não tiver)."""
    card_id = state.players[player_id].instinct_card
    if card_id is None:
        return 0
    inst = state.available_instincts.get(card_id)
    if inst is None:
        return 0
    rule = _INSTINCT_RULES.get(inst.rule)
    if rule is None:
        return 0
    return inst.points * rule(state, player_id)


def compute_player_score(state, player_id) -> int:
    total = 0
    has_moon_jelly = False
    for cell in state.board.cells.values():
        occupant = cell.occupant
        if occupant is not None and occupant.owner == player_id:
            total += score_coral(state, occupant)
            for fauna_id in cell.fauna:
                if fauna_id == MOON_JELLY_ID:
                    # Moon Jelly pontua por tiles distintos visitados (nível do jogador),
                    # não por ocorrência — evita dupla contagem com várias jellies.
                    has_moon_jelly = True
                    continue
                total += score_fauna(state, fauna_id, cell.position, player_id)
    if has_moon_jelly:
        visited = len(state.players[player_id].moon_jelly_visited)
        cap = state.available_fauna[MOON_JELLY_ID].visited_score_cap
        total += min(visited, cap) if cap > 0 else visited
    # Objetivo de Instinto (pontua conforme o board; realizado no placar final).
    total += score_instinct(state, player_id)
    return total


def recompute_scores(state) -> None:
    """Refresh every player's score from the current board."""
    for player_id, player in state.players.items():
        player.score = compute_player_score(state, player_id)
