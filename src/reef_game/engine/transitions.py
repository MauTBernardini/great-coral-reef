from copy import deepcopy

from .actions import (
    BuyFloraAction,
    PlaceCoralAction,
    PlaceSoilAction,
    PlaceStaghornPairAction,
)
from .economy import effective_cost
from .enums import ActionType, PlayerId, ResourceType
from .models import MAX_HAND_SIZE, PlacedCoral, PlacedSoil
from .production import resolve_production
from .scoring import recompute_scores
from .termination import check_game_end
from .validators import validate_action

STAGHORN_ID = "staghorn"
STAGHORN_PAIR_PLANKTON_SURCHARGE = 1


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

    if action.action_type == ActionType.PLACE_STAGHORN_PAIR:
        _apply_place_staghorn_pair(next_state, action)
        _advance_turn(next_state)
        check_game_end(next_state, max_rounds=max_rounds)
        return next_state

    if action.action_type == ActionType.PLACE_SOIL:
        _apply_place_soil(next_state, action)
        _advance_turn(next_state)
        check_game_end(next_state, max_rounds=max_rounds)
        return next_state

    if action.action_type == ActionType.BUY_FLORA:
        _apply_buy_flora(next_state, action)
        _advance_turn(next_state)
        check_game_end(next_state, max_rounds=max_rounds)
        return next_state

    raise ValueError("Unsupported action type.")


def _apply_place_soil(state, action: PlaceSoilAction):
    player = state.players[state.active_player]
    soil_id = state.soil_pile[0]  # topo da pilha (não se escolhe o tipo)
    soil = state.available_soils[soil_id]
    sun_cost = soil.cost.values.get(ResourceType.SUN, 0)

    if player.resources.get(ResourceType.SUN, 0) < sun_cost:
        # Ação perdida: o solo volta ao topo da pilha (nada é pago nem colocado).
        player.dead_turns += 1
        player.passed_last_turn = False
        _append_history(
            state,
            action,
            {
                "soil_id": soil_id,
                "position": action.position,
                "result": "soil_purchase_lost",
                "reason": "insufficient_sun",
            },
        )
        return

    state.soil_pile.pop(0)
    state.board.cells[action.position].soil = PlacedSoil(
        soil_id=soil_id,
        owner=state.active_player,
        position=action.position,
    )
    for resource, amount in soil.cost.values.items():
        player.resources[resource] -= amount
        player.spent_resources[resource] = player.spent_resources.get(resource, 0) + amount

    player.passed_last_turn = False
    _append_history(
        state,
        action,
        {
            "soil_id": soil_id,
            "position": action.position,
            "result": "place_soil",
        },
    )


def _apply_buy_flora(state, action: BuyFloraAction):
    player = state.players[state.active_player]
    space = MAX_HAND_SIZE - len(player.hand)
    drawn = min(action.count, space, len(state.flora_deck))

    bought = []
    for _ in range(drawn):
        bought.append(state.flora_deck.pop(0))
    player.hand.extend(bought)

    player.passed_last_turn = False
    _append_history(
        state,
        action,
        {
            "result": "buy_flora",
            "requested": action.count,
            "bought": bought,
            "hand_size": len(player.hand),
        },
    )


def _place_coral_on_board(state, coral_id, position) -> str:
    """Commit one coral to the board and pay its (effective) cost. Returns its id."""
    player = state.players[state.active_player]
    coral = state.available_corals[coral_id]
    cell = state.board.cells[position]

    px, py, pz = position
    instance_id = f"{coral_id}_{state.turn}_{state.active_player.value}_{px}{py}{pz}"
    cell.occupant = PlacedCoral(
        instance_id=instance_id,
        coral_id=coral_id,
        owner=state.active_player,
        position=position,
    )

    for resource, amount in effective_cost(state, coral, position).items():
        player.resources[resource] -= amount
        player.spent_resources[resource] = player.spent_resources.get(resource, 0) + amount

    player.placed_corals += 1
    return instance_id


def _apply_place_coral(state, action: PlaceCoralAction):
    player = state.players[state.active_player]
    score_before = player.score

    instance_id = _place_coral_on_board(state, action.coral_id, action.position)

    recompute_scores(state)
    gained = player.score - score_before
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


def _apply_place_staghorn_pair(state, action: PlaceStaghornPairAction):
    player = state.players[state.active_player]
    score_before = player.score

    # First goes down before second, so the second may be stacked on it.
    first_id = _place_coral_on_board(state, STAGHORN_ID, action.first_position)
    second_id = _place_coral_on_board(state, STAGHORN_ID, action.second_position)

    player.resources[ResourceType.PLANKTON] -= STAGHORN_PAIR_PLANKTON_SURCHARGE
    player.spent_resources[ResourceType.PLANKTON] = (
        player.spent_resources.get(ResourceType.PLANKTON, 0) + STAGHORN_PAIR_PLANKTON_SURCHARGE
    )

    recompute_scores(state)
    gained = player.score - score_before
    player.passed_last_turn = False

    _append_history(
        state,
        action,
        {
            "placed_instance_id": [first_id, second_id],
            "points_gained": gained,
            "positions": [action.first_position, action.second_position],
            "coral_id": STAGHORN_ID,
            "bonus_plankton_paid": STAGHORN_PAIR_PLANKTON_SURCHARGE,
        },
    )


def _advance_turn(state):
    state.turn += 1
    state.active_player = PlayerId.P1 if state.active_player == PlayerId.P2 else PlayerId.P2
    if state.active_player == PlayerId.P1:
        state.round += 1
        _resolve_climate_round(state)
        _resolve_production_round(state)


def _resolve_production_round(state):
    gains = resolve_production(state)
    _append_history(
        state,
        None,
        {
            "result": "production",
            "round": state.round,
            "production": {
                player_id.value: {resource.value: amount for resource, amount in resources.items()}
                for player_id, resources in gains.items()
            },
        },
        action_type="production_tick",
    )


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


def _append_history(state, action, payload, action_type=None):
    if action_type is None:
        action_type = (
            action.action_type.value
            if hasattr(action, "action_type")
            else "climate_tick"
        )
    state.action_history.append(
        {
            "turn": state.turn,
            "player": state.active_player.value,
            "action_type": action_type,
            **payload,
        }
    )
