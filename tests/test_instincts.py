from pathlib import Path

import pytest

from reef_game.content.loader import load_instincts
from reef_game.engine.actions import PlayParasiteAction
from reef_game.engine.enums import PlayerId, ResourceType
from reef_game.engine.models import PlacedCoral, PlacedSoil
from reef_game.engine.scoring import compute_player_score, score_instinct
from reef_game.engine.setup import deal_instinct_options
from reef_game.engine.transitions import apply_action
from reef_game.engine.validators import InvalidActionError, validate_action

ROOT = Path(__file__).resolve().parents[1]
INSTINCTS = load_instincts(ROOT / "configs" / "instincts.yaml")


def _coral(state, coral_id, pos, owner=PlayerId.P1):
    state.board.cells[pos].occupant = PlacedCoral(f"{coral_id}_{pos}", coral_id, owner, pos)


def _soil(state, pos, soil_id, owner=PlayerId.P1):
    state.board.cells[pos].soil = PlacedSoil(soil_id, owner, pos)


def _with_instinct(state, card_id, owner=PlayerId.P1):
    state.available_instincts = INSTINCTS
    state.players[owner].instinct_card = card_id
    return state


# ---------------- Mecânica de escolha ----------------

def test_deal_offers_two_distinct_cards_per_player():
    opts = deal_instinct_options(1234, INSTINCTS)
    assert len(opts[PlayerId.P1]) == 2
    assert len(opts[PlayerId.P2]) == 2
    # As 4 cartas oferecidas são distintas entre si.
    assert set(opts[PlayerId.P1]).isdisjoint(opts[PlayerId.P2])
    assert len(set(opts[PlayerId.P1])) == 2


def test_no_instinct_definitions_deals_empty():
    opts = deal_instinct_options(1, {})
    assert opts[PlayerId.P1] == [] and opts[PlayerId.P2] == []


def test_score_instinct_zero_without_card(initial_state):
    assert score_instinct(initial_state, PlayerId.P1) == 0


# ---------------- Regras de pontuação ----------------

def test_vertical_architect(initial_state):
    top = initial_state.board.max_layers - 1
    _coral(initial_state, "staghorn", (0, 0, top))
    _coral(initial_state, "staghorn", (2, 2, top))
    _coral(initial_state, "staghorn", (1, 1, 0))  # não está no topo
    _with_instinct(initial_state, "vertical_architect")
    assert score_instinct(initial_state, PlayerId.P1) == 3 * 2


def test_dominance_of_species(initial_state):
    _coral(initial_state, "staghorn", (0, 0, 0))
    _coral(initial_state, "staghorn", (1, 0, 0))
    _coral(initial_state, "staghorn", (2, 0, 0))
    _coral(initial_state, "elkhorn", (3, 0, 0))
    _with_instinct(initial_state, "dominance_of_species")
    # tipo dominante = staghorn (3 tiles) -> 2 pontos cada
    assert score_instinct(initial_state, PlayerId.P1) == 3 * 2


def test_total_symbiosis_is_disabled():
    # Desativada por ora: não deve ser oferecida no baralho.
    assert "total_symbiosis" not in INSTINCTS


def test_outer_wall(initial_state):
    _coral(initial_state, "staghorn", (0, 1, 0))  # borda (x=0)
    _coral(initial_state, "staghorn", (3, 2, 0))  # borda (x=3)
    _coral(initial_state, "staghorn", (2, 3, 0))  # borda (y=3)
    _coral(initial_state, "staghorn", (1, 1, 0))  # interior -> não conta
    _with_instinct(initial_state, "outer_wall")
    assert score_instinct(initial_state, PlayerId.P1) == 2 * 3


def test_tunnel_engineer(initial_state):
    # 3 corais conectados em linha na camada do fundo = 1 grupo -> 3 pontos.
    for x in range(3):
        _coral(initial_state, "staghorn", (x, 0, 0))
    _with_instinct(initial_state, "tunnel_engineer")
    assert score_instinct(initial_state, PlayerId.P1) == 3

    # Só 2 conectados -> nenhum grupo completo de 3.
    initial_state.board.cells[(2, 0, 0)].occupant = None
    assert score_instinct(initial_state, PlayerId.P1) == 0


def test_overcrowded_nursery(initial_state):
    gb_cap = initial_state.available_corals["grooved_brain_coral"].habitat_capacity
    _coral(initial_state, "grooved_brain_coral", (0, 0, 0))
    initial_state.board.cells[(0, 0, 0)].fauna = ["damselfish"] * gb_cap  # 100% cheio
    _coral(initial_state, "staghorn", (1, 0, 0))  # tem capacidade mas vazio -> não conta
    _with_instinct(initial_state, "overcrowded_nursery")
    assert score_instinct(initial_state, PlayerId.P1) == 2


def test_energy_reserve(initial_state):
    initial_state.players[PlayerId.P1].resources = {
        ResourceType.SUN: 5, ResourceType.PLANKTON: 3, ResourceType.O2: 9,
    }
    _with_instinct(initial_state, "energy_reserve")
    # (5 + 3) // 3 = 2 ; O2 não conta
    assert score_instinct(initial_state, PlayerId.P1) == 2


def test_empire_of_the_frontier(initial_state):
    _coral(initial_state, "staghorn", (1, 1, 0))            # seu
    _coral(initial_state, "staghorn", (2, 1, 0), owner=PlayerId.P2)  # oponente ao lado
    _coral(initial_state, "staghorn", (0, 3, 0))            # seu, sem oponente vizinho
    _with_instinct(initial_state, "empire_of_the_frontier")
    # só o coral em (1,1,0) faz fronteira com o oponente -> 2 pontos
    assert score_instinct(initial_state, PlayerId.P1) == 2


def test_buffer_zone(initial_state):
    _soil(initial_state, (1, 0, 0), "sandy_bed")            # sandy bed vazio no meio
    _coral(initial_state, "staghorn", (0, 0, 0))            # seu, à esquerda
    _coral(initial_state, "staghorn", (2, 0, 0), owner=PlayerId.P2)  # oponente à direita
    _with_instinct(initial_state, "buffer_zone")
    # (1,0,0) é sandy bed vazio entre você e o oponente -> 1 ponto
    assert score_instinct(initial_state, PlayerId.P1) == 1

    # Se o sandy bed for ocupado por um coral, deixa de contar.
    _coral(initial_state, "staghorn", (1, 0, 0))
    assert score_instinct(initial_state, PlayerId.P1) == 0


def test_columns_of_hercules(initial_state):
    top = initial_state.board.max_layers
    for z in range(top):
        _coral(initial_state, "staghorn", (0, 0, z))  # torre completa
    _coral(initial_state, "staghorn", (1, 0, 0))       # coluna incompleta
    _with_instinct(initial_state, "columns_of_hercules")
    assert score_instinct(initial_state, PlayerId.P1) == 4  # 1 torre completa


def test_opportunistic_parasite_scores_for_owner(initial_state):
    _coral(initial_state, "staghorn", (0, 0, 0), owner=PlayerId.P2)  # coral inimigo
    initial_state.board.cells[(0, 0, 0)].add_fauna("clownfish", PlayerId.P1)  # parasita de P1
    _with_instinct(initial_state, "opportunistic_parasite")
    assert score_instinct(initial_state, PlayerId.P1) == 3  # 1 parasita


def test_parasite_action_requires_card_and_enemy_coral(initial_state):
    initial_state.available_instincts = INSTINCTS
    _coral(initial_state, "staghorn", (0, 0, 0), owner=PlayerId.P2)  # inimigo
    initial_state.players[PlayerId.P1].hand.append("clownfish")
    initial_state.players[PlayerId.P1].resources = {
        ResourceType.SUN: 5, ResourceType.PLANKTON: 5, ResourceType.O2: 0,
    }

    # Sem a carta -> inválido.
    with pytest.raises(InvalidActionError):
        validate_action(initial_state, PlayParasiteAction("clownfish", (0, 0, 0)))

    # Com a carta, mas em coral PRÓPRIO -> inválido.
    initial_state.players[PlayerId.P1].instinct_card = "opportunistic_parasite"
    _coral(initial_state, "staghorn", (1, 0, 0), owner=PlayerId.P1)
    with pytest.raises(InvalidActionError):
        validate_action(initial_state, PlayParasiteAction("clownfish", (1, 0, 0)))

    # Com a carta e em coral inimigo -> válido.
    validate_action(initial_state, PlayParasiteAction("clownfish", (0, 0, 0)))


def test_parasite_play_end_to_end(initial_state):
    initial_state.available_instincts = INSTINCTS
    initial_state.players[PlayerId.P1].instinct_card = "opportunistic_parasite"
    _coral(initial_state, "staghorn", (0, 0, 0), owner=PlayerId.P2)  # habitat 2
    initial_state.players[PlayerId.P1].hand.append("clownfish")
    initial_state.players[PlayerId.P1].resources = {
        ResourceType.SUN: 5, ResourceType.PLANKTON: 5, ResourceType.O2: 0,
    }

    s = apply_action(initial_state, PlayParasiteAction("clownfish", (0, 0, 0)))

    cell = s.board.cells[(0, 0, 0)]
    assert list(cell.fauna_with_owners()) == [("clownfish", PlayerId.P1)]
    # P1: clownfish(2) + instinct parasita(3) = 5 ; P2: só staghorn(1)
    assert s.players[PlayerId.P1].score == 5
    assert s.players[PlayerId.P2].score == 1


def test_instinct_adds_to_player_score(initial_state):
    _coral(initial_state, "staghorn", (0, 1, 0))  # borda
    base = compute_player_score(initial_state, PlayerId.P1)
    _with_instinct(initial_state, "outer_wall")
    # score total = base (coral) + 2 (outer wall)
    assert compute_player_score(initial_state, PlayerId.P1) == base + 2
