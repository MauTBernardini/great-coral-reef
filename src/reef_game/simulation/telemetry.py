from dataclasses import dataclass, field

from ..engine.state import board_capacity, occupied_cells_count


@dataclass
class GameTelemetry:
    states: list = field(default_factory=list)

    def record_state(self, state):
        snapshot = {
            "turn": state.turn,
            "round": state.round,
            "active_player": state.active_player.value,
            "is_terminal": state.is_terminal,
            "temperature": state.temperature,
            "ph": state.ph,
            "current_era": state.current_era,
            "remaining_climate_cards": len(state.climate_deck),
            "consumed_climate_cards": len(state.climate_discard),
            "occupancy_ratio": occupied_cells_count(state) / board_capacity(state),
            "scores": {pid.value: p.score for pid, p in state.players.items()},
            "placed_corals": {pid.value: p.placed_corals for pid, p in state.players.items()},
            "dead_turns": {pid.value: p.dead_turns for pid, p in state.players.items()},
        }
        self.states.append(snapshot)
