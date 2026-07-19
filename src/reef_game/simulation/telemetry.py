from dataclasses import dataclass, field

from ..engine.enums import ResourceType
from ..engine.state import board_capacity, occupied_cells_count

_RESOURCES = (ResourceType.SUN, ResourceType.PLANKTON, ResourceType.O2)


def _resource_map(mapping):
    return {r.value: int(mapping.get(r, 0)) for r in _RESOURCES}


def _player_board(state, player_id):
    """This player's corals + soil tiles on the shared board, per-layer count e capacidade
    habitacional total (soma da habitat_capacity dos seus corais)."""
    corals = []
    soils = []
    fauna = []
    by_layer = {z: 0 for z in range(state.board.max_layers)}
    habitat_capacity = 0
    for position, cell in state.board.cells.items():
        occupant = cell.occupant
        if occupant is not None and occupant.owner == player_id:
            corals.append({"coral_id": occupant.coral_id, "position": list(position)})
            by_layer[position[2]] += 1
            habitat_capacity += state.available_corals[occupant.coral_id].habitat_capacity
            for fauna_id in cell.fauna:
                fauna.append({"fauna_id": fauna_id, "position": list(position)})
        if cell.soil is not None and cell.soil.owner == player_id:
            soils.append({"soil_id": cell.soil.soil_id, "position": list(position)})
    return corals, soils, fauna, by_layer, habitat_capacity


def _player_snapshot(state, player):
    corals, soils, fauna, by_layer, habitat_capacity = _player_board(state, player.player_id)
    ponds_count = sum(1 for pond in state.ponds if pond.owner == player.player_id)
    return {
        "resources": _resource_map(player.resources),          # sol, plancton e o2 atuais
        "produced": _resource_map(player.produced_resources),   # produzido acumulado
        "spent": _resource_map(player.spent_resources),         # usado acumulado
        "score": player.score,
        "placed_corals": player.placed_corals,
        "dead_turns": player.dead_turns,
        "hand": list(player.hand),                              # mao (cartas de coral)
        "hand_size": len(player.hand),
        "board": corals,                                        # estado do board do player
        "corals_by_layer": by_layer,
        "soils": soils,                                         # tiles de solo do player
        "soils_count": len(soils),
        "habitat_capacity": habitat_capacity,                  # capacidade total p/ fauna
        "fauna": fauna,                                        # fauna jogada nos corais
        "fauna_count": len(fauna),
        "ponds_count": ponds_count,                            # ponds que o player possui
        "instincts_count": len(player.instinct_cards),         # cartas de Instinto que possui
    }


@dataclass
class GameTelemetry:
    states: list = field(default_factory=list)

    def record_state(self, state):
        players = {pid.value: _player_snapshot(state, p) for pid, p in state.players.items()}
        snapshot = {
            "seed": state.seed,
            "turn": state.turn,
            "round": state.round,
            "active_player": state.active_player.value,
            "is_terminal": state.is_terminal,
            # --- ecossistema ---
            "temperature": state.temperature,
            "ph": state.ph,
            "current_era": state.current_era,
            "remaining_climate_cards": len(state.climate_deck),
            "consumed_climate_cards": len(state.climate_discard),
            "occupancy_ratio": occupied_cells_count(state) / board_capacity(state),
            "soil_pile_remaining": len(state.soil_pile),
            "coral_deck_remaining": len(state.coral_deck),
            # --- compat com metrics.summarize_game (mantidos no topo) ---
            "scores": {pid.value: p.score for pid, p in state.players.items()},
            "placed_corals": {pid.value: p.placed_corals for pid, p in state.players.items()},
            "dead_turns": {pid.value: p.dead_turns for pid, p in state.players.items()},
            # --- estado rico por jogador ---
            "players": players,
        }
        self.states.append(snapshot)

    def to_rows(self):
        """Long format: one row per (snapshot, player) for progression analysis."""
        rows = []
        for snap in self.states:
            for player_id, p in snap["players"].items():
                rows.append(
                    {
                        "seed": snap["seed"],
                        "turn": snap["turn"],
                        "round": snap["round"],
                        "is_terminal": snap["is_terminal"],
                        "temperature": snap["temperature"],
                        "ph": snap["ph"],
                        "current_era": snap["current_era"],
                        "remaining_climate_cards": snap["remaining_climate_cards"],
                        "consumed_climate_cards": snap["consumed_climate_cards"],
                        "occupancy_ratio": snap["occupancy_ratio"],
                        "soil_pile_remaining": snap["soil_pile_remaining"],
                        "coral_deck_remaining": snap["coral_deck_remaining"],
                        "player": player_id,
                        "sun": p["resources"]["sun"],
                        "plankton": p["resources"]["plankton"],
                        "o2": p["resources"]["o2"],
                        "produced_sun": p["produced"]["sun"],
                        "produced_plankton": p["produced"]["plankton"],
                        "produced_o2": p["produced"]["o2"],
                        "spent_sun": p["spent"]["sun"],
                        "spent_plankton": p["spent"]["plankton"],
                        "habitat_capacity": p["habitat_capacity"],
                        "score": p["score"],
                        "placed_corals": p["placed_corals"],
                        "dead_turns": p["dead_turns"],
                        "hand_size": p["hand_size"],
                        "soils_count": p["soils_count"],
                        "fauna_count": p["fauna_count"],
                        "ponds": p["ponds_count"],
                        "instincts": p["instincts_count"],
                        "corals_z0": p["corals_by_layer"].get(0, 0),
                        "corals_z1": p["corals_by_layer"].get(1, 0),
                        "corals_z2": p["corals_by_layer"].get(2, 0),
                    }
                )
        return rows
