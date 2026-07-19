from pathlib import Path

from reef_game.content.loader import load_instincts
from reef_game.engine.enums import PlayerId
from reef_game.engine.models import PlacedCoral
from reef_game.engine.scoring import compute_player_score, score_instinct
from reef_game.engine.setup import deal_instinct_options

ROOT = Path(__file__).resolve().parents[1]
INSTINCTS = load_instincts(ROOT / "configs" / "instincts.yaml")


def _coral(state, coral_id, pos, owner=PlayerId.P1):
    state.board.cells[pos].occupant = PlacedCoral(f"{coral_id}_{pos}", coral_id, owner, pos)


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
    # tipo dominante = staghorn (3 tiles) -> 1 ponto cada
    assert score_instinct(initial_state, PlayerId.P1) == 3


def test_total_symbiosis(initial_state):
    _coral(initial_state, "staghorn", (0, 0, 0))
    initial_state.board.cells[(0, 0, 0)].fauna = ["damselfish", "clownfish"]
    _coral(initial_state, "grooved_brain_coral", (1, 0, 0))
    initial_state.board.cells[(1, 0, 0)].fauna = ["seahorse"]
    _with_instinct(initial_state, "total_symbiosis")
    # 3 pares coral<->fauna ativados -> 3 pontos cada
    assert score_instinct(initial_state, PlayerId.P1) == 3 * 3


def test_outer_wall(initial_state):
    _coral(initial_state, "staghorn", (0, 1, 0))  # borda (x=0)
    _coral(initial_state, "staghorn", (3, 2, 0))  # borda (x=3)
    _coral(initial_state, "staghorn", (2, 3, 0))  # borda (y=3)
    _coral(initial_state, "staghorn", (1, 1, 0))  # interior -> não conta
    _with_instinct(initial_state, "outer_wall")
    assert score_instinct(initial_state, PlayerId.P1) == 2 * 3


def test_tunnel_engineer(initial_state):
    # 4 corais conectados em linha na camada do fundo = 1 grupo -> 3 pontos.
    for x in range(4):
        _coral(initial_state, "staghorn", (x, 0, 0))
    _with_instinct(initial_state, "tunnel_engineer")
    assert score_instinct(initial_state, PlayerId.P1) == 3

    # Só 3 conectados -> nenhum grupo completo.
    s2 = initial_state
    s2.board.cells[(3, 0, 0)].occupant = None
    assert score_instinct(s2, PlayerId.P1) == 0


def test_overcrowded_nursery(initial_state):
    gb_cap = initial_state.available_corals["grooved_brain_coral"].habitat_capacity
    _coral(initial_state, "grooved_brain_coral", (0, 0, 0))
    initial_state.board.cells[(0, 0, 0)].fauna = ["damselfish"] * gb_cap  # 100% cheio
    _coral(initial_state, "staghorn", (1, 0, 0))  # tem capacidade mas vazio -> não conta
    _with_instinct(initial_state, "overcrowded_nursery")
    assert score_instinct(initial_state, PlayerId.P1) == 3


def test_instinct_adds_to_player_score(initial_state):
    _coral(initial_state, "staghorn", (0, 1, 0))  # borda
    base = compute_player_score(initial_state, PlayerId.P1)
    _with_instinct(initial_state, "outer_wall")
    # score total = base (coral) + 2 (outer wall)
    assert compute_player_score(initial_state, PlayerId.P1) == base + 2
