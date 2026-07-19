from copy import deepcopy

from .actions import (
    BuyCoralsAction,
    PlaceCoralAction,
    PlaceSoilAction,
    PlaceStaghornPairAction,
    PlayFaunaAction,
)
from .economy import effective_cost
from .enums import ActionType, PlayerId, ResourceType
from .models import MAX_HAND_SIZE, PlacedCoral, PlacedSoil
from .production import resolve_production
from .scoring import (
    count_adjacent_fauna,
    player_small_fish,
    recompute_scores,
    score_fauna,
)
from .termination import check_game_end
from .validators import validate_action

STAGHORN_ID = "staghorn"
STAGHORN_PAIR_PLANKTON_SURCHARGE = 1


def _gain_resource(player, resource, amount):
    player.resources[resource] = player.resources.get(resource, 0) + amount
    player.produced_resources[resource] = player.produced_resources.get(resource, 0) + amount


def apply_action(state, action, max_rounds: int | None = None):
    validate_action(state, action)
    next_state = deepcopy(state)

    if action.action_type == ActionType.PASS:
        player = next_state.players[next_state.active_player]
        player.passed_last_turn = True
        player.passed_this_round = True  # sai da rodada
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

    if action.action_type == ActionType.PLAY_FAUNA:
        _apply_play_fauna(next_state, action)
        _advance_turn(next_state)
        check_game_end(next_state, max_rounds=max_rounds)
        return next_state

    if action.action_type == ActionType.BUY_CORALS:
        _apply_buy_corals(next_state, action)
        _advance_turn(next_state)
        check_game_end(next_state, max_rounds=max_rounds)
        return next_state

    raise ValueError("Unsupported action type.")


def _apply_play_fauna(state, action: PlayFaunaAction):
    player = state.players[state.active_player]
    fauna = state.available_fauna[action.fauna_id]
    cell = state.board.cells[action.position]

    # Custo em peixes pequenos sacrificados do board (Blacktip): remove os de menor pontuação.
    if fauna.sacrifice_small_fish > 0:
        smalls = player_small_fish(state, state.active_player)
        smalls.sort(key=lambda cf: score_fauna(state, cf[1], cf[0].position, state.active_player))
        for _ in range(fauna.sacrifice_small_fish):
            if not smalls:
                break
            sac_cell, sac_fauna = smalls.pop(0)
            sac_cell.fauna.remove(sac_fauna)

    # Efeitos ao jogar (antes de adicionar a carta à célula):
    #  - Green Chromis: se o tile já tem um Green Chromis, recupera 1 Sol.
    #  - Anthias: +1 Plâncton se houver outro Anthias (seu) num tile adjacente.
    if action.fauna_id == "green_chromis" and "green_chromis" in cell.fauna:
        _gain_resource(player, ResourceType.SUN, 1)
    if action.fauna_id == "anthias" and count_adjacent_fauna(
        state, action.position, "anthias", state.active_player
    ) >= 1:
        _gain_resource(player, ResourceType.PLANKTON, 1)

    player.hand.remove(action.fauna_id)  # gasta a carta
    cell.fauna.append(action.fauna_id)

    for resource, amount in fauna.cost.values.items():
        player.resources[resource] -= amount
        player.spent_resources[resource] = player.spent_resources.get(resource, 0) + amount

    # Saque imediato ao jogar (Cyclothone).
    if fauna.on_play_draw:
        _draw_cards(state, player, fauna.on_play_draw)

    score_before = player.score
    recompute_scores(state)
    gained = player.score - score_before
    player.passed_last_turn = False
    _append_history(
        state,
        action,
        {
            "result": "play_fauna",
            "fauna_id": action.fauna_id,
            "position": action.position,
            "points_gained": gained,
        },
    )


def _apply_place_soil(state, action: PlaceSoilAction):
    # Afordabilidade é garantida na validação (só é ação válida se puder pagar).
    player = state.players[state.active_player]
    soil_id = state.soil_pile[0]  # topo da pilha (não se escolhe o tipo)
    soil = state.available_soils[soil_id]

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


def _explore_bonus(state, owner) -> int:
    """+cartas por compra vindo de fauna no board (Leafy Seadragon)."""
    bonus = 0
    for cell in state.board.cells.values():
        occupant = cell.occupant
        if occupant is not None and occupant.owner == owner:
            for fauna_id in cell.fauna:
                fauna = state.available_fauna.get(fauna_id)
                if fauna is not None:
                    bonus += fauna.explore_bonus
    return bonus


def _draw_cards(state, player, count) -> list:
    space = MAX_HAND_SIZE - len(player.hand)
    drawn = min(count, space, len(state.coral_deck))
    bought = [state.coral_deck.pop(0) for _ in range(drawn)]
    player.hand.extend(bought)
    return bought


def _apply_buy_corals(state, action: BuyCoralsAction):
    player = state.players[state.active_player]
    total = action.count + _explore_bonus(state, state.active_player)  # Leafy Seadragon
    bought = _draw_cards(state, player, total)

    player.bought_corals_this_round = True  # só 1 compra por rodada
    player.passed_last_turn = False
    _append_history(
        state,
        action,
        {
            "result": "buy_corals",
            "requested": total,
            "bought": bought,
            "hand_size": len(player.hand),
        },
    )


def _place_coral_on_board(state, coral_id, position) -> str:
    """Commit one coral to the board, gasta a carta da mão e paga o custo. Returns its id."""
    player = state.players[state.active_player]
    coral = state.available_corals[coral_id]
    cell = state.board.cells[position]

    # Gasta a carta de coral da mão.
    if coral_id in player.hand:
        player.hand.remove(coral_id)

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

    # Rebate (Branched Finger): devolve Sol se a base da coluna for o solo indicado.
    if coral.refund_soil is not None and coral.refund_sun:
        base = state.board.cells.get((px, py, 0))
        if base is not None and base.soil is not None and base.soil.soil_id == coral.refund_soil:
            player.resources[ResourceType.SUN] = (
                player.resources.get(ResourceType.SUN, 0) + coral.refund_sun
            )
            player.produced_resources[ResourceType.SUN] = (
                player.produced_resources.get(ResourceType.SUN, 0) + coral.refund_sun
            )

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
    """Rodada com N turnos: alterna, mas pula quem já passou. Quando ambos passaram,
    inicia a próxima rodada (produção + clima)."""
    state.turn += 1
    current = state.active_player
    other = PlayerId.P1 if current == PlayerId.P2 else PlayerId.P2

    if not state.players[other].passed_this_round:
        state.active_player = other
    elif not state.players[current].passed_this_round:
        state.active_player = current  # oponente saiu; segue jogando sozinho
    else:
        _start_new_round(state)


def _start_new_round(state):
    state.round += 1
    for player in state.players.values():
        player.passed_this_round = False
        player.bought_corals_this_round = False
    state.active_player = PlayerId.P1
    # Cada rodada inicia com a produção e um evento climático.
    _resolve_production_round(state)
    # A produção pode sacrificar fauna (falta de O2) -> reflete no score.
    recompute_scores(state)
    _resolve_climate_round(state)


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
