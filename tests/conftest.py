from pathlib import Path

import pytest

from reef_game.content.loader import load_corals, load_soils
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
def balance_rules():
    return load_balance_rules(ROOT / "configs" / "balance_rules.yaml")


@pytest.fixture
def climate_config():
    return load_climate_config(ROOT / "configs" / "climate.yaml")


@pytest.fixture
def initial_state(coral_defs, soil_defs, balance_rules, climate_config):
    return create_initial_state(
        seed=42,
        coral_definitions=coral_defs,
        balance_rules=balance_rules,
        climate_config=climate_config,
        soil_definitions=soil_defs,
    )


def seed_all_soil(state, owner=PlayerId.P2, soil_id="sandy_bed"):
    """Test shortcut: fill every bottom cell with soil directly (bypassing the
    buy action). Owned by P2 por padrão para não perturbar as asserções de P1."""
    for position, cell in state.board.cells.items():
        if position[2] == 0:
            cell.soil = PlacedSoil(soil_id=soil_id, owner=owner, position=position)
    return state


def stock_all_corals(state, copies=8):
    """Test shortcut: dá a ambos os jogadores muitas cartas de cada coral na mão,
    para que os testes de colocação/pontuação não dependam do sorteio do baralho."""
    for player in state.players.values():
        player.hand = [coral_id for coral_id in state.available_corals for _ in range(copies)]
    return state


@pytest.fixture
def soiled_state(initial_state):
    stock_all_corals(initial_state)
    return seed_all_soil(initial_state)
