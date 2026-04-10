import pytest

from reef_game.engine.setup import build_climate_deck
from reef_game.engine.state import board_capacity


def test_initial_state_has_expected_defaults(initial_state, balance_rules):
    assert initial_state.turn == 1
    assert initial_state.round == 1
    assert board_capacity(initial_state) == 4 * 4 * 3
    assert len(initial_state.available_corals) >= 2
    assert initial_state.temperature == 28.0
    assert initial_state.ph == 8.1
    assert initial_state.temperature_step == 0.5
    assert initial_state.ph_step == 0.05
    assert initial_state.critical_temperature == 32.0
    assert initial_state.critical_ph == 7.4
    assert initial_state.current_era == 1
    assert len(initial_state.climate_deck) == balance_rules["climate"]["deck_size"]
    assert {card.era for card in initial_state.climate_deck} == {1, 2, 3}
    assert all(card.number_of_cards == 3 for card in initial_state.climate_deck)


def test_build_climate_deck_respects_deck_size(climate_config):
    deck = build_climate_deck(
        seed=42,
        climate_cfg={
            "deck_size": 7,
            "deck": climate_config["deck"],
        },
    )

    assert len(deck) == 7


def test_build_climate_deck_rejects_oversized_deck(climate_config):
    total_available_cards = sum(card["number_of_cards"] for card in climate_config["deck"])

    with pytest.raises(ValueError):
        build_climate_deck(
            seed=42,
            climate_cfg={
                "deck_size": total_available_cards + 1,
                "deck": climate_config["deck"],
            },
        )
