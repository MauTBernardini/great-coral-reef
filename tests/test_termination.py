from copy import deepcopy

from reef_game.engine.actions import PassAction
from reef_game.engine.models import ClimateCard
from reef_game.engine.transitions import apply_action


def test_game_ends_when_climate_deck_is_exhausted(initial_state):
    state = deepcopy(initial_state)
    state.climate_deck = [ClimateCard(
        card_id="last-card",
        era=1,
        label="Last Card",
        temperature_steps=0,
        ph_steps=0,
    )]

    state = apply_action(state, PassAction())
    assert not state.is_terminal
    state = apply_action(state, PassAction())
    assert state.is_terminal


def test_game_ends_when_temperature_hits_critical_threshold(initial_state):
    state = deepcopy(initial_state)
    state.temperature = state.critical_temperature - state.temperature_step
    state.climate_deck = [ClimateCard(
        card_id="final-heat",
        era=1,
        label="Final Heat",
        temperature_steps=1,
        ph_steps=0,
    )]

    state = apply_action(state, PassAction())
    state = apply_action(state, PassAction())

    assert state.is_terminal
    assert state.temperature >= state.critical_temperature


def test_game_ends_when_ph_hits_critical_threshold(initial_state):
    state = deepcopy(initial_state)
    state.ph = state.critical_ph + state.ph_step
    state.climate_deck = [ClimateCard(
        card_id="final-acidification",
        era=1,
        label="Final Acidification",
        temperature_steps=0,
        ph_steps=1,
    )]

    state = apply_action(state, PassAction())
    state = apply_action(state, PassAction())

    assert state.is_terminal
    assert state.ph <= state.critical_ph
