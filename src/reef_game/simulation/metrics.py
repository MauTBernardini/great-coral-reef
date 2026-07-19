import statistics

from ..engine.scoring import score_instinct
from ..engine.state import board_capacity, occupied_cells_count


def _soils_on_board(state):
    counts = {pid.value: 0 for pid in state.players}
    for cell in state.board.cells.values():
        if cell.soil is not None:
            counts[cell.soil.owner.value] += 1
    return counts


def _soil_purchases_lost(state):
    counts = {pid.value: 0 for pid in state.players}
    for event in state.action_history:
        if event.get("result") == "soil_purchase_lost":
            counts[event["player"]] += 1
    return counts


def _corals_by_type(state):
    counts = {pid.value: {} for pid in state.players}
    for cell in state.board.cells.values():
        occupant = cell.occupant
        if occupant is not None:
            by_player = counts[occupant.owner.value]
            by_player[occupant.coral_id] = by_player.get(occupant.coral_id, 0) + 1
    return counts


def _soils_by_type(state):
    counts = {pid.value: {} for pid in state.players}
    for cell in state.board.cells.values():
        if cell.soil is not None:
            by_player = counts[cell.soil.owner.value]
            by_player[cell.soil.soil_id] = by_player.get(cell.soil.soil_id, 0) + 1
    return counts


def _fauna_by_type(state):
    counts = {pid.value: {} for pid in state.players}
    for cell in state.board.cells.values():
        occupant = cell.occupant
        if occupant is not None:
            by_player = counts[occupant.owner.value]
            for fauna_id in cell.fauna:
                by_player[fauna_id] = by_player.get(fauna_id, 0) + 1
    return counts


def _habitat_by_player(state):
    totals = {pid.value: 0 for pid in state.players}
    for cell in state.board.cells.values():
        occupant = cell.occupant
        if occupant is not None:
            coral = state.available_corals[occupant.coral_id]
            totals[occupant.owner.value] += coral.habitat_capacity
    return totals


def summarize_game(state, telemetry):
    players = state.players
    soils_on_board = _soils_on_board(state)
    soil_lost = _soil_purchases_lost(state)
    summary = {
        "winner": state.winner.value if state.winner else None,
        "turns": state.turn,
        "rounds": state.round,
        "temperature": state.temperature,
        "ph": state.ph,
        "current_era": state.current_era,
        "consumed_climate_cards": len(state.climate_discard),
        "remaining_climate_cards": len(state.climate_deck),
        "era_transition_log": list(state.era_transition_log),
        "board_occupancy": occupied_cells_count(state) / board_capacity(state),
        "scores": {pid.value: p.score for pid, p in players.items()},
        "placed_corals": {pid.value: p.placed_corals for pid, p in players.items()},
        "dead_turns": {pid.value: p.dead_turns for pid, p in players.items()},
        "spent_resources": {
            pid.value: {k.value: v for k, v in p.spent_resources.items()}
            for pid, p in players.items()
        },
        "produced_resources": {
            pid.value: {k.value: v for k, v in p.produced_resources.items()}
            for pid, p in players.items()
        },
        "hand_size": {pid.value: len(p.hand) for pid, p in players.items()},
        "soils_on_board": soils_on_board,
        "soil_purchases_lost": soil_lost,
        "corals_by_type": _corals_by_type(state),
        "soils_by_type": _soils_by_type(state),
        "fauna_by_type": _fauna_by_type(state),
        "habitat_capacity": _habitat_by_player(state),
        "soil_pile_remaining": len(state.soil_pile),
        "coral_deck_remaining": len(state.coral_deck),
        "action_history_length": len(state.action_history),
        "instinct_card": {pid.value: p.instinct_card for pid, p in players.items()},
        "instinct_points": {pid.value: score_instinct(state, pid) for pid in players},
    }

    for pid, p in players.items():
        total_spent = sum(p.spent_resources.values()) or 1
        summary[f"efficiency_player_{pid.value}"] = p.score / total_spent

    if telemetry.states:
        p1_scores = [s["scores"][1] for s in telemetry.states]
        p2_scores = [s["scores"][2] for s in telemetry.states]
        summary["p1_score_volatility"] = statistics.pstdev(p1_scores) if len(p1_scores) > 1 else 0
        summary["p2_score_volatility"] = statistics.pstdev(p2_scores) if len(p2_scores) > 1 else 0
        summary["climate_history"] = [
            {
                "round": s["round"],
                "temperature": s["temperature"],
                "ph": s["ph"],
                "current_era": s["current_era"],
                "consumed_climate_cards": s["consumed_climate_cards"],
                "remaining_climate_cards": s["remaining_climate_cards"],
            }
            for s in telemetry.states
        ]
        summary["climate_resolution_log"] = [
            event
            for event in state.action_history
            if event["action_type"] == "climate_tick"
        ]

    return summary
