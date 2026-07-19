from pathlib import Path

import pytest

from reef_game.content.loader import load_corals, load_flora, load_soils
from reef_game.engine.enums import PlayerId
from reef_game.engine.models import PlacedSoil
from reef_game.engine.setup import create_initial_state, load_balance_rules, load_climate_config

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def coral_defs():
    return load_corals(ROOT / "configs" / "corals.yaml")


@pytest.fixture
def soil_defs():
    return load_soils(ROOT / "configs" / "soils.yaml")


@pytest.fixture
def flora_defs():
    return load_flora(ROOT / "configs" / "flora.yaml")


@pytest.fixture
def balance_rules():
    return load_balance_rules(ROOT / "configs" / "balance_rules.yaml")


@pytest.fixture
def climate_config():
    return load_climate_config(ROOT / "configs" / "climate.yaml")


@pytest.fixture
def initial_state(coral_defs, soil_defs, flora_defs, balance_rules, climate_config):
    return create_initial_state(
        seed=42,
        coral_definitions=coral_defs,
        balance_rules=balance_rules,
        climate_config=climate_config,
        soil_definitions=soil_defs,
        flora_definitions=flora_defs,
    )


def seed_all_soil(state, owner=PlayerId.P2, soil_id="sandy_bed"):
    """Test shortcut: fill every bottom cell with soil directly (bypassing the
    buy action) so coral-placement tests can focus on coral mechanics.

    Owned by P2 by default so it never perturbs the P1-focused resource assertions
    (soil production goes to its owner). Sandy Bed has no cost reduction, so it does
    not interfere with cost tests either.
    """
    for position, cell in state.board.cells.items():
        if position[2] == 0:
            cell.soil = PlacedSoil(soil_id=soil_id, owner=owner, position=position)
    return state


@pytest.fixture
def soiled_state(initial_state):
    return seed_all_soil(initial_state)
