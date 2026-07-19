from pathlib import Path

import pytest

from reef_game.content.loader import load_upgrades
from reef_game.engine.actions import MoveSmallFishAction, PlayFaunaAction
from reef_game.engine.enums import PlayerId, ResourceType
from reef_game.engine.models import PlacedCoral
from reef_game.engine.production import resolve_production
from reef_game.engine.scoring import (
    effective_habitat_capacity,
    grant_small_fish_death_bonus,
    has_patrol_neighbor,
)
from reef_game.engine.transitions import apply_action
from reef_game.engine.validators import InvalidActionError, validate_action

ROOT = Path(__file__).resolve().parents[1]
UPGRADES = load_upgrades(ROOT / "configs" / "upgrades.yaml")


def _coral(state, coral_id, pos, owner=PlayerId.P1):
    state.board.cells[pos].occupant = PlacedCoral(f"{coral_id}_{pos}", coral_id, owner, pos)


def test_load_upgrades():
    assert set(UPGRADES) == {
        "safe_nursery", "saber_teeth", "slow_metabolist", "attraction_pheromones",
    }


# ---------------- Slow Metabolist ----------------

def test_slow_metabolist_doubles_capacity(initial_state):
    _coral(initial_state, "grooved_brain_coral", (0, 0, 0))  # habitat 1
    cell = initial_state.board.cells[(0, 0, 0)]
    base = effective_habitat_capacity(initial_state, cell)
    initial_state.players[PlayerId.P1].upgrade_cards = ["slow_metabolist"]
    assert effective_habitat_capacity(initial_state, cell) == 2 * base


def test_slow_metabolist_allows_extra_fauna(initial_state):
    _coral(initial_state, "grooved_brain_coral", (0, 0, 0))  # habitat 1
    initial_state.board.cells[(0, 0, 0)].add_fauna("damselfish", PlayerId.P1)  # lota (1/1)
    initial_state.players[PlayerId.P1].hand.append("clownfish")
    initial_state.players[PlayerId.P1].resources = {
        ResourceType.SUN: 5, ResourceType.PLANKTON: 5, ResourceType.O2: 0,
    }
    # Sem o upgrade: habitat cheio -> inválido.
    with pytest.raises(InvalidActionError):
        validate_action(initial_state, PlayFaunaAction("clownfish", (0, 0, 0)))
    # Com Slow Metabolist: capacidade 2 -> cabe mais 1.
    initial_state.players[PlayerId.P1].upgrade_cards = ["slow_metabolist"]
    validate_action(initial_state, PlayFaunaAction("clownfish", (0, 0, 0)))


# ---------------- Saber Teeth ----------------

def test_saber_teeth_enables_diagonal_patrol(initial_state):
    _coral(initial_state, "staghorn", (0, 0, 0), owner=PlayerId.P2)
    initial_state.board.cells[(0, 0, 0)].add_fauna("blacktip_reef_shark", PlayerId.P2)
    _coral(initial_state, "staghorn", (1, 1, 0), owner=PlayerId.P1)  # diagonal ao predador

    # Sem o upgrade: diagonal não é patrulhada.
    assert has_patrol_neighbor(initial_state, (1, 1, 0)) is False
    # Com Saber Teeth no dono do predador: a diagonal passa a bloquear.
    initial_state.players[PlayerId.P2].upgrade_cards = ["saber_teeth"]
    assert has_patrol_neighbor(initial_state, (1, 1, 0)) is True


# ---------------- Safe Nursery ----------------

def test_safe_nursery_bonus_helper(initial_state):
    initial_state.players[PlayerId.P1].upgrade_cards = ["safe_nursery"]
    p0 = initial_state.players[PlayerId.P1].resources.get(ResourceType.PLANKTON, 0)
    grant_small_fish_death_bonus(initial_state, "damselfish", PlayerId.P1)  # small fish
    assert initial_state.players[PlayerId.P1].resources[ResourceType.PLANKTON] == p0 + 1
    # Fauna grande não gera bônus.
    grant_small_fish_death_bonus(initial_state, "blacktip_reef_shark", PlayerId.P1)
    assert initial_state.players[PlayerId.P1].resources[ResourceType.PLANKTON] == p0 + 1


def test_safe_nursery_triggers_on_o2_sacrifice(initial_state):
    _coral(initial_state, "staghorn", (0, 0, 0))  # habitat 2, o2 = 1
    initial_state.board.cells[(0, 0, 0)].add_fauna("damselfish", PlayerId.P1)
    initial_state.board.cells[(0, 0, 0)].add_fauna("damselfish", PlayerId.P1)  # 2 fauna, o2=1
    initial_state.players[PlayerId.P1].upgrade_cards = ["safe_nursery"]
    p0 = initial_state.players[PlayerId.P1].resources.get(ResourceType.PLANKTON, 0)

    resolve_production(initial_state)

    # 1 damselfish sacrificada (2 fauna > 1 O2) -> +1 Plâncton via Safe Nursery.
    assert initial_state.players[PlayerId.P1].resources[ResourceType.PLANKTON] == p0 + 1
    assert initial_state.board.cells[(0, 0, 0)].fauna.count("damselfish") == 1


# ---------------- Attraction Pheromones ----------------

def test_pheromones_repositions_enemy_fish_without_taking_it(initial_state):
    _coral(initial_state, "staghorn", (0, 0, 0), owner=PlayerId.P2)
    initial_state.board.cells[(0, 0, 0)].add_fauna("damselfish", PlayerId.P2)
    _coral(initial_state, "staghorn", (1, 0, 0), owner=PlayerId.P1)  # destino adjacente
    initial_state.players[PlayerId.P1].upgrade_cards = ["attraction_pheromones"]

    s = apply_action(initial_state, MoveSmallFishAction("damselfish", (0, 0, 0), (1, 0, 0)))

    assert "damselfish" not in s.board.cells[(0, 0, 0)].fauna
    dest = s.board.cells[(1, 0, 0)]
    assert list(dest.fauna_with_owners()) == [("damselfish", PlayerId.P2)]  # posse mantida
    # bônus grátis: não avança o turno (ainda é a vez de P1) e marca o uso.
    assert s.active_player == PlayerId.P1
    assert s.players[PlayerId.P1].moved_small_fish_this_turn is True


def test_pheromones_requires_upgrade_and_once_per_turn(initial_state):
    _coral(initial_state, "staghorn", (0, 0, 0), owner=PlayerId.P2)
    initial_state.board.cells[(0, 0, 0)].add_fauna("damselfish", PlayerId.P2)
    _coral(initial_state, "staghorn", (1, 0, 0), owner=PlayerId.P1)
    move = MoveSmallFishAction("damselfish", (0, 0, 0), (1, 0, 0))

    with pytest.raises(InvalidActionError):  # sem o upgrade
        validate_action(initial_state, move)

    initial_state.players[PlayerId.P1].upgrade_cards = ["attraction_pheromones"]
    validate_action(initial_state, move)  # ok

    initial_state.players[PlayerId.P1].moved_small_fish_this_turn = True
    with pytest.raises(InvalidActionError):  # já moveu neste turno
        validate_action(initial_state, move)


def test_pheromones_only_moves_small_fish(initial_state):
    _coral(initial_state, "staghorn", (0, 0, 0), owner=PlayerId.P1)
    initial_state.board.cells[(0, 0, 0)].add_fauna("blacktip_reef_shark", PlayerId.P1)  # não é small
    _coral(initial_state, "staghorn", (1, 0, 0), owner=PlayerId.P1)
    initial_state.players[PlayerId.P1].upgrade_cards = ["attraction_pheromones"]

    with pytest.raises(InvalidActionError):
        validate_action(
            initial_state, MoveSmallFishAction("blacktip_reef_shark", (0, 0, 0), (1, 0, 0))
        )
