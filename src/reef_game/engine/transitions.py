from copy import deepcopy

from .actions import PlaceCoralAction
from .enums import ActionType, PlayerId
from .models import PlacedCoral
from .scoring import score_incremental_after_placement
from .termination import check_game_end
from .validators import validate_action


def apply_action(state, action, max_rounds: int | None = None):
    validate_action(state, action)
    next_state = deepcopy(state)

    if action.action_type == ActionType.PASS:
        player = next_state.players[next_state.active_player]
        player.passed_last_turn = True
        player.dead_turns += 1
        _append_history(next_state, action, {"result": "pass"})
        _advance_turn(next_state)
        check_game_end(next_state, max_rounds=max_rounds)
        return next_state

    if action.action_type == ActionType.PLACE_CORAL:
        _apply_place_coral(next_state, action)
        _advance_turn(next_state)
        check_game_end(next_state, max_rounds=max_rounds)
        return next_state

    raise ValueError("Unsupported action type.")


def _apply_place_coral(state, action: PlaceCoralAction):
    player = state.players[state.active_player]
    coral = state.available_corals[action.coral_id]
    cell = state.board.cells[action.position]

    instance_id = f"{action.coral_id}_{state.turn}_{state.active_player.value}"
    placed = PlacedCoral(
        instance_id=instance_id,
        coral_id=action.coral_id,
        owner=state.active_player,
        position=action.position,
    )
    cell.occupant = placed

    for resource, amount in coral.cost.values.items():
        player.resources[resource] -= amount
        player.spent_resources[resource] = player.spent_resources.get(resource, 0) + amount

    player.placed_corals += 1
    gained = score_incremental_after_placement(state, placed)
    player.score += gained
    player.passed_last_turn = False

    _append_history(
        state,
        action,
        {
            "placed_instance_id": instance_id,
            "points_gained": gained,
            "position": action.position,
            "coral_id": action.coral_id,
        },
    )


def _advance_turn(state):
    state.turn += 1
    state.active_player = PlayerId.P1 if state.active_player == PlayerId.P2 else PlayerId.P2
    if state.active_player == PlayerId.P1:
        state.round += 1
        _resolve_climate_round(state)


def _resolve_climate_round(state):
    card = _draw_climate_card_for_current_era(state)
    if card is None:
        return

    state.climate_discard.append(card)

    state.temperature += card.temperature_steps * state.temperature_step
    state.ph -= card.ph_steps * state.ph_step

    climate_event = {
        "round": state.round,
        "card_id": card.card_id,
        "era": card.era,
        "label": card.label,
        "event_type": card.event_type,
        "original_climate_change": card.original_climate_change,
        "effect_text": card.effect_text,
        "temperature_steps": card.temperature_steps,
        "ph_steps": card.ph_steps,
        "temperature": state.temperature,
        "ph": state.ph,
    }
    _update_era_transitions(state, climate_event)
    _append_history(state, card, {"result": "climate", **climate_event})


def _draw_climate_card_for_current_era(state):
    for index, card in enumerate(state.climate_deck):
        if card.era == state.current_era:
            return state.climate_deck.pop(index)
    return None


def _update_era_transitions(state, climate_event):
    while True:
        next_era = state.current_era + 1
        thresholds = state.era_thresholds.get(next_era)
        if thresholds is None or not _threshold_reached(state, thresholds):
            return

        state.current_era = next_era
        state.era_transition_log.append(
            {
                "round": state.round,
                "era": next_era,
                "trigger_temperature": state.temperature,
                "trigger_ph": state.ph,
                "card_id": climate_event["card_id"],
            }
        )


def _threshold_reached(state, thresholds: dict) -> bool:
    temperature_target = thresholds.get("temperature")
    ph_target = thresholds.get("ph")

    return (
        (temperature_target is not None and state.temperature >= temperature_target)
        or (ph_target is not None and state.ph <= ph_target)
    )


def _append_history(state, action, payload):
    state.action_history.append(
        {
            "turn": state.turn,
            "player": state.active_player.value,
            "action_type": getattr(action, "action_type", ActionType.PASS).value
            if hasattr(action, "action_type")
            else "climate_tick",
            **payload,
        }
    )
