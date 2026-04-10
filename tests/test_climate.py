from copy import deepcopy

import pytest

from reef_game.engine.actions import PassAction
from reef_game.engine.models import ClimateCard
from reef_game.engine.transitions import apply_action


def test_climate_step_conversion_uses_configured_steps(initial_state):
    state = deepcopy(initial_state)
    state.climate_deck = [
        ClimateCard(
            card_id="step-check",
            era=1,
            label="Step Check",
            temperature_steps=2,
            ph_steps=1,
        )
    ]

    state = apply_action(state, PassAction())
    state = apply_action(state, PassAction())

    assert state.temperature == pytest.approx(29.0)
    assert state.ph == pytest.approx(8.05)
    climate_event = next(event for event in state.action_history if event["action_type"] == "climate_tick")
    assert climate_event["temperature_steps"] == 2
    assert climate_event["ph_steps"] == 1


def test_climate_resolves_once_per_completed_round(initial_state):
    state = deepcopy(initial_state)
    starting_temperature = state.temperature
    starting_deck_size = len(state.climate_deck)

    state = apply_action(state, PassAction())
    assert state.temperature == starting_temperature
    assert len(state.climate_deck) == starting_deck_size

    state = apply_action(state, PassAction())
    assert len(state.climate_deck) == starting_deck_size - 1
    assert len([event for event in state.action_history if event["action_type"] == "climate_tick"]) == 1


def test_era_transition_triggers_when_threshold_is_crossed(initial_state):
    state = deepcopy(initial_state)
    state.temperature = 28.5
    state.climate_deck = [
        ClimateCard(
            card_id="era-shift",
            era=1,
            label="Era Shift",
            temperature_steps=1,
            ph_steps=0,
        )
    ]

    state = apply_action(state, PassAction())
    state = apply_action(state, PassAction())

    assert state.current_era == 2
    assert state.era_transition_log[0]["era"] == 2


def test_climate_draw_uses_only_current_era_cards(initial_state):
    state = deepcopy(initial_state)
    state.climate_deck = [
        ClimateCard(card_id="future-era", era=2, label="Future Era", temperature_steps=2, ph_steps=0),
        ClimateCard(card_id="current-era", era=1, label="Current Era", temperature_steps=1, ph_steps=0),
    ]

    state = apply_action(state, PassAction())
    state = apply_action(state, PassAction())

    climate_event = next(event for event in state.action_history if event["action_type"] == "climate_tick")
    assert climate_event["card_id"] == "current-era"
    assert state.climate_deck[0].card_id == "future-era"


def test_game_stops_when_current_era_has_no_drawable_cards(initial_state):
    state = deepcopy(initial_state)
    state.climate_deck = [
        ClimateCard(card_id="later-era-only", era=2, label="Later Era", temperature_steps=1, ph_steps=0)
    ]

    state = apply_action(state, PassAction())
    state = apply_action(state, PassAction())

    assert not state.is_terminal
    assert all(event["action_type"] != "climate_tick" for event in state.action_history)
