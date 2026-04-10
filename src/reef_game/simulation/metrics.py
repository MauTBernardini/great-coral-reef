import statistics

from ..engine.state import board_capacity, occupied_cells_count


def summarize_game(state, telemetry):
    players = state.players
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
        "action_history_length": len(state.action_history),
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
