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
