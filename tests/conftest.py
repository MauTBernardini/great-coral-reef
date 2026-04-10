from pathlib import Path

import pytest

from reef_game.content.loader import load_corals
from reef_game.engine.setup import create_initial_state, load_balance_rules, load_climate_config

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def coral_defs():
    return load_corals(ROOT / "configs" / "corals.yaml")


@pytest.fixture
def balance_rules():
    return load_balance_rules(ROOT / "configs" / "balance_rules.yaml")


@pytest.fixture
def climate_config():
    return load_climate_config(ROOT / "configs" / "climate.yaml")


@pytest.fixture
def initial_state(coral_defs, balance_rules, climate_config):
    return create_initial_state(
        seed=42,
        coral_definitions=coral_defs,
        balance_rules=balance_rules,
        climate_config=climate_config,
    )
