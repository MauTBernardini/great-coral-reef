from pathlib import Path

from reef_game.agents.greedy_agent import GreedyAgent
from reef_game.content.loader import load_corals, load_fauna, load_instincts, load_soils
from reef_game.engine.enums import PlayerId
from reef_game.engine.models import PlacedCoral
from reef_game.engine.ponds import MAX_CARDS, detect_new_pond, maybe_form_pond
from reef_game.engine.setup import create_initial_state, load_balance_rules, load_climate_config
from reef_game.simulation.metrics import _distribution_stats
from reef_game.simulation.runner import run_game

ROOT = Path(__file__).resolve().parents[1]
INSTINCTS = load_instincts(ROOT / "configs" / "instincts.yaml")


def _coral(state, pos, owner=PlayerId.P1):
    state.board.cells[pos].occupant = PlacedCoral(f"c_{pos}", "staghorn", owner, pos)


def _square_2x2(state, z=0, owner=PlayerId.P1):
    """Coloca 3 dos 4 corais do quadrado 2x2 (falta o de fecho em (1,1,z))."""
    for pos in [(0, 0, z), (1, 0, z), (0, 1, z)]:
        _coral(state, pos, owner)


def _make_two_tall(state):
    """Empilha corais em 2 colunas do quadrado -> 2 colunas 'de altura'."""
    _coral(state, (0, 0, 1))
    _coral(state, (1, 0, 1))


def test_2x2_with_two_tall_columns_forms_pond(initial_state):
    _square_2x2(initial_state)
    _coral(initial_state, (1, 1, 0))  # fecha o ciclo
    _make_two_tall(initial_state)     # (0,0) e (1,0) ficam com altura 2

    cells = detect_new_pond(initial_state, (1, 1, 0))
    assert cells == frozenset({(0, 0, 0), (1, 0, 0), (0, 1, 0), (1, 1, 0)})


def test_2x2_without_tall_columns_is_not_pond(initial_state):
    _square_2x2(initial_state)
    _coral(initial_state, (1, 1, 0))  # ciclo fechado, mas tudo com altura 1
    assert detect_new_pond(initial_state, (1, 1, 0)) is None


def test_open_shape_is_not_pond(initial_state):
    _coral(initial_state, (0, 0, 0))
    _coral(initial_state, (1, 0, 0))
    _coral(initial_state, (0, 1, 0))  # forma um "L", sem ciclo
    _make_two_tall(initial_state)
    assert detect_new_pond(initial_state, (0, 1, 0)) is None


def test_maybe_form_pond_sets_owner_and_grants_offer(initial_state):
    initial_state.available_instincts = INSTINCTS
    initial_state.instinct_deck = list(INSTINCTS.keys())
    _square_2x2(initial_state)
    _coral(initial_state, (1, 1, 0))
    _make_two_tall(initial_state)

    cells = maybe_form_pond(initial_state, (1, 1, 0), PlayerId.P1)

    assert cells is not None
    assert len(initial_state.ponds) == 1
    assert initial_state.ponds[0].owner == PlayerId.P1
    # ganhou uma oferta de carta (2 Instintos; sem baralho de upgrade neste teste)
    offers = initial_state.players[PlayerId.P1].pending_card_offers
    assert len(offers) == 1
    assert len(offers[0]["instincts"]) == 2


def test_closer_owns_pond_even_with_enemy_corals(initial_state):
    initial_state.available_instincts = INSTINCTS
    initial_state.instinct_deck = list(INSTINCTS.keys())
    _square_2x2(initial_state, owner=PlayerId.P1)  # 3 corais do P1
    _coral(initial_state, (1, 1, 0), owner=PlayerId.P2)  # P2 coloca o de fecho
    _make_two_tall(initial_state)

    maybe_form_pond(initial_state, (1, 1, 0), PlayerId.P2)

    assert initial_state.ponds[0].owner == PlayerId.P2  # roubo: quem fecha é dono


def test_intersection_rule_blocks_second_pond(initial_state):
    initial_state.available_instincts = INSTINCTS
    initial_state.instinct_deck = list(INSTINCTS.keys())
    # Primeira pond: quadrado em x=0..1.
    _square_2x2(initial_state)
    _coral(initial_state, (1, 1, 0))
    _make_two_tall(initial_state)
    maybe_form_pond(initial_state, (1, 1, 0), PlayerId.P1)

    # Segunda pond adjacente compartilhando a aresta x=1 (2 células) -> bloqueada.
    _coral(initial_state, (2, 0, 0))
    _coral(initial_state, (2, 1, 0))
    _coral(initial_state, (2, 0, 1))  # deixa (2,0) alto
    _coral(initial_state, (2, 1, 1))  # deixa (2,1) alto
    # ciclo (1,0),(2,0),(2,1),(1,1) compartilha (1,0) e (1,1) com a pond 1.
    assert detect_new_pond(initial_state, (2, 1, 0)) is None


def test_pond_offer_capped_at_max_instincts(initial_state):
    initial_state.available_instincts = INSTINCTS
    initial_state.instinct_deck = list(INSTINCTS.keys())
    initial_state.players[PlayerId.P1].instinct_cards = ["outer_wall"] * MAX_CARDS
    _square_2x2(initial_state)
    _coral(initial_state, (1, 1, 0))
    _make_two_tall(initial_state)

    maybe_form_pond(initial_state, (1, 1, 0), PlayerId.P1)

    # Pond forma, mas nenhuma oferta é dada (teto atingido).
    assert len(initial_state.ponds) == 1
    assert initial_state.players[PlayerId.P1].pending_card_offers == []


# ---------------- Métricas ao longo do jogo ----------------

def test_distribution_stats():
    s = _distribution_stats([0, 0, 1, 1, 2, 3])
    assert round(s["mean"], 3) == 1.167
    assert s["median"] == 1.0
    assert s["p25"] <= s["median"] <= s["p75"]
    # Casos-limite.
    assert _distribution_stats([]) == {"mean": 0.0, "median": 0.0, "p25": 0.0, "p75": 0.0}
    assert _distribution_stats([5])["p25"] == 5.0


def test_summary_and_telemetry_track_ponds_and_instincts():
    corals = load_corals(ROOT / "configs" / "corals.yaml")
    soils = load_soils(ROOT / "configs" / "soils.yaml")
    fauna = load_fauna(ROOT / "configs" / "fauna.yaml")
    br = load_balance_rules(ROOT / "configs" / "balance_rules.yaml")
    cc = load_climate_config(ROOT / "configs" / "climate.yaml")
    state = create_initial_state(
        seed=123, coral_definitions=corals, balance_rules=br, climate_config=cc,
        soil_definitions=soils, fauna_definitions=fauna, instinct_definitions=INSTINCTS,
    )
    _, summary, tel = run_game(
        state, agents={PlayerId.P1: GreedyAgent(), PlayerId.P2: GreedyAgent()}, max_rounds=30
    )

    for pid in (1, 2):
        assert set(summary[f"ponds_stats_{pid}"]) == {"mean", "median", "p25", "p75"}
        # Todo jogador tem >=1 instinto (o inicial) durante todo o jogo.
        assert summary[f"instincts_stats_{pid}"]["mean"] >= 1.0

    rows = tel.to_rows()
    assert "ponds" in rows[0] and "instincts" in rows[0]
