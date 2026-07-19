"""Production phase.

Runs once at the start of every round (right after the climate tick). Each coral
yields its base ``production`` (from config, empty by default) plus any ability
bonuses. Today the only ability contributor is the Elkhorn cluster bonus.
"""

from .enums import ResourceType
from .scoring import _count_adjacent_seagrass, grant_small_fish_death_bonus, score_fauna

ELKHORN_ID = "elkhorn"
DUGONG_ID = "dugong"


def _sacrifice_lowest_fauna(state, owner, count):
    """Remove ``count`` faunas do jogador, priorizando as de menor pontuação."""
    entries = []
    for cell in state.board.cells.values():
        occupant = cell.occupant
        if occupant is not None and occupant.owner == owner:
            for fauna_id in cell.fauna:
                entries.append((score_fauna(state, fauna_id, cell.position, owner), cell, fauna_id))
    entries.sort(key=lambda e: e[0])  # menor pontuação primeiro
    sacrificed = []
    for _ in range(count):
        if not entries:
            break
        _, cell, fauna_id = entries.pop(0)
        f_owner = next((fo for fid, fo in cell.fauna_with_owners() if fid == fauna_id), owner)
        cell.remove_fauna(fauna_id)
        grant_small_fish_death_bonus(state, fauna_id, f_owner)  # Safe Nursery
        sacrificed.append(fauna_id)
    return sacrificed


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
        player_id: {ResourceType.SUN: 0, ResourceType.PLANKTON: 0, ResourceType.O2: 0}
        for player_id in state.players
    }
    fauna_count = {player_id: 0 for player_id in state.players}

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
        # O2 gerado pelo coral (campo separado).
        if coral.o2:
            gains[occupant.owner][ResourceType.O2] += coral.o2
        # Fauna deste coral (para o consumo de O2 abaixo).
        fauna_count[occupant.owner] += len(cell.fauna)

        # Elkhorn ability: on the top layer, adjacent to >=2 same-owner top-layer
        # elkhorns -> +1 Sun production.
        if occupant.coral_id == ELKHORN_ID and occupant.position[2] == top_layer:
            if _adjacent_top_elkhorns(state, occupant.position, occupant.owner) >= 2:
                gains[occupant.owner][ResourceType.SUN] += 1

    # Consumo de O2: cada fauna consome 1. Se há mais fauna que produção de O2,
    # sacrifica-se fauna (menor pontuação primeiro) até o net de O2 ficar >= 0.
    sacrifices = {}
    for player_id in state.players:
        o2_produced = gains[player_id][ResourceType.O2]
        n_fauna = fauna_count[player_id]
        if n_fauna > o2_produced:
            killed = _sacrifice_lowest_fauna(state, player_id, n_fauna - o2_produced)
            sacrifices[player_id] = killed
            n_fauna = o2_produced
        gains[player_id][ResourceType.O2] = o2_produced - n_fauna  # net (>= 0)

    # Produção da fauna SOBREVIVENTE (ex.: Lanternfish +1 Sol).
    for cell in state.board.cells.values():
        occupant = cell.occupant
        if occupant is None:
            continue
        for fauna_id in cell.fauna:
            fauna = state.available_fauna.get(fauna_id)
            if fauna is not None:
                for resource, amount in fauna.production.items():
                    gains[occupant.owner][resource] += amount
            # Dugong: com >=2 Seagrass adjacentes, cada uma dá +1 Plâncton ao dono.
            if fauna_id == DUGONG_ID:
                seagrass = _count_adjacent_seagrass(state, cell.position)
                if seagrass >= 2:
                    gains[occupant.owner][ResourceType.PLANKTON] += seagrass

    for player_id, player in state.players.items():
        for resource, amount in gains[player_id].items():
            if amount:
                player.resources[resource] = player.resources.get(resource, 0) + amount
                player.produced_resources[resource] = (
                    player.produced_resources.get(resource, 0) + amount
                )

    return gains
