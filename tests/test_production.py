from reef_game.engine.enums import PlayerId, ResourceType
from reef_game.engine.models import PlacedCoral
from reef_game.engine.production import resolve_production


def _force_place(state, coral_id, position, owner):
    # Bypass validation: we're unit-testing the production rule, not placement legality.
    state.board.cells[position].occupant = PlacedCoral(
        instance_id=f"{coral_id}_{position}",
        coral_id=coral_id,
        owner=owner,
        position=position,
    )


def test_fauna_consumes_o2_and_forces_sacrifice(initial_state):
    # 2 corais com O2 (=2 O2) e 3 fauna -> falta 1 O2 -> sacrifica 1 (menor pontuação).
    _force_place(initial_state, "staghorn", (0, 0, 0), PlayerId.P1)  # o2 1
    _force_place(initial_state, "grooved_brain_coral", (1, 0, 0), PlayerId.P1)  # o2 1
    initial_state.board.cells[(0, 0, 0)].fauna = ["damselfish", "clownfish"]  # scores 1, 2
    initial_state.board.cells[(1, 0, 0)].fauna = ["damselfish"]  # score 1

    gains = resolve_production(initial_state)

    total_fauna = sum(len(c.fauna) for c in initial_state.board.cells.values())
    assert total_fauna == 2  # uma sacrificada
    assert gains[PlayerId.P1][ResourceType.O2] == 0  # net zerado
    # a sacrificada foi uma de menor pontuação (damselfish); a clownfish sobrevive.
    surviving = [f for c in initial_state.board.cells.values() for f in c.fauna]
    assert "clownfish" in surviving


def test_surplus_o2_accumulates_when_fewer_fauna(initial_state):
    _force_place(initial_state, "staghorn", (0, 0, 0), PlayerId.P1)  # o2 1
    _force_place(initial_state, "grooved_brain_coral", (1, 0, 0), PlayerId.P1)  # o2 1
    _force_place(initial_state, "fox_coral", (2, 0, 0), PlayerId.P1)  # o2 1 -> 3 O2 no total
    initial_state.board.cells[(0, 0, 0)].fauna = ["damselfish"]  # 1 fauna

    gains = resolve_production(initial_state)

    assert gains[PlayerId.P1][ResourceType.O2] == 2  # 3 O2 - 1 fauna
    assert sum(len(c.fauna) for c in initial_state.board.cells.values()) == 1  # nada sacrificado


def test_corals_produce_o2(initial_state):
    _force_place(initial_state, "staghorn", (0, 0, 0), PlayerId.P1)  # o2 1
    _force_place(initial_state, "fox_coral", (1, 0, 0), PlayerId.P1)  # o2 1
    _force_place(initial_state, "sun_coral", (2, 0, 0), PlayerId.P1)  # o2 0

    gains = resolve_production(initial_state)

    assert gains[PlayerId.P1][ResourceType.O2] == 2
    assert initial_state.players[PlayerId.P1].resources[ResourceType.O2] == 2
    assert initial_state.players[PlayerId.P1].produced_resources[ResourceType.O2] == 2


def test_coral_o2_and_habitat_loaded(coral_defs):
    assert coral_defs["staghorn"].o2 == 1 and coral_defs["staghorn"].habitat_capacity == 2
    assert coral_defs["sun_coral"].o2 == 0 and coral_defs["sun_coral"].habitat_capacity == 1
    gorgonian = coral_defs["gorgonian_sea_fan"]
    assert gorgonian.o2 == 0 and gorgonian.habitat_capacity == 2


def test_elkhorn_cluster_produces_extra_sun(initial_state):
    top = initial_state.board.max_layers - 1
    # Row of three top-layer elkhorns; only the middle one has 2 elkhorn neighbours.
    _force_place(initial_state, "elkhorn", (0, 0, top), PlayerId.P1)
    _force_place(initial_state, "elkhorn", (1, 0, top), PlayerId.P1)
    _force_place(initial_state, "elkhorn", (2, 0, top), PlayerId.P1)

    sun_before = initial_state.players[PlayerId.P1].resources[ResourceType.SUN]
    gains = resolve_production(initial_state)

    assert gains[PlayerId.P1][ResourceType.SUN] == 1
    assert initial_state.players[PlayerId.P1].resources[ResourceType.SUN] == sun_before + 1


def test_isolated_top_elkhorn_produces_nothing(initial_state):
    top = initial_state.board.max_layers - 1
    _force_place(initial_state, "elkhorn", (0, 0, top), PlayerId.P1)

    sun_before = initial_state.players[PlayerId.P1].resources[ResourceType.SUN]
    resolve_production(initial_state)

    assert initial_state.players[PlayerId.P1].resources[ResourceType.SUN] == sun_before


def test_elkhorn_bonus_requires_top_layer(initial_state):
    # Same cluster shape but on the ground layer -> no production bonus.
    _force_place(initial_state, "elkhorn", (0, 0, 0), PlayerId.P1)
    _force_place(initial_state, "elkhorn", (1, 0, 0), PlayerId.P1)
    _force_place(initial_state, "elkhorn", (2, 0, 0), PlayerId.P1)

    gains = resolve_production(initial_state)
    assert gains[PlayerId.P1][ResourceType.SUN] == 0
