import pytest

from reef_game.engine.actions import PlaceCoralAction, PlaceSoilAction
from reef_game.engine.enums import PlayerId, ResourceType
from reef_game.engine.production import resolve_production
from reef_game.engine.transitions import apply_action
from reef_game.engine.validators import InvalidActionError, validate_action


def test_coral_requires_soil_at_column_base(initial_state):
    # No soil placed yet -> any coral placement is rejected (mesmo com a carta na mão).
    initial_state.players[PlayerId.P1].hand.append("grooved_brain_coral")
    with pytest.raises(InvalidActionError):
        validate_action(initial_state, PlaceCoralAction("grooved_brain_coral", (0, 0, 0)))


def test_buying_soil_draws_top_of_pile_and_places_it(initial_state):
    top = initial_state.soil_pile[0]
    top_cost = initial_state.available_soils[top].cost.values[ResourceType.SUN]
    sun_before = initial_state.players[PlayerId.P1].resources[ResourceType.SUN]

    s = apply_action(initial_state, PlaceSoilAction((0, 0, 0)))

    placed = s.board.cells[(0, 0, 0)].soil
    assert placed is not None and placed.soil_id == top
    assert placed.owner == PlayerId.P1
    assert s.players[PlayerId.P1].resources[ResourceType.SUN] == sun_before - top_cost
    assert len(s.soil_pile) == len(initial_state.soil_pile) - 1
    assert s.soil_pile == initial_state.soil_pile[1:]


def test_unaffordable_soil_is_not_a_valid_action(initial_state):
    # Comprar solo só é válido se puder pagar o topo da pilha.
    initial_state.players[PlayerId.P1].resources[ResourceType.SUN] = 0
    with pytest.raises(InvalidActionError):
        validate_action(initial_state, PlaceSoilAction((0, 0, 0)))


def test_soil_only_on_bottom_layer(initial_state):
    with pytest.raises(InvalidActionError):
        validate_action(initial_state, PlaceSoilAction((0, 0, 1)))


def test_cannot_place_soil_where_soil_exists(initial_state):
    s = apply_action(initial_state, PlaceSoilAction((0, 0, 0)))
    with pytest.raises(InvalidActionError):
        validate_action(s, PlaceSoilAction((0, 0, 0)))


def test_empty_soil_pile_makes_soil_purchase_illegal(initial_state):
    initial_state.soil_pile = []
    with pytest.raises(InvalidActionError):
        validate_action(initial_state, PlaceSoilAction((0, 0, 0)))


def test_rocky_reef_discounts_corals_built_on_it(initial_state):
    from reef_game.engine.economy import effective_cost
    from reef_game.engine.models import PlacedSoil

    initial_state.board.cells[(0, 0, 0)].soil = PlacedSoil("rocky_reef", PlayerId.P1, (0, 0, 0))
    coral = initial_state.available_corals["grooved_brain_coral"]  # normally 2 Sun
    cost = effective_cost(initial_state, coral, (0, 0, 0))
    assert cost[ResourceType.SUN] == 1  # 2 - 1 (rocky reef)


def test_soil_produces_for_its_owner(initial_state):
    from reef_game.engine.models import PlacedSoil

    cell = initial_state.board.cells[(0, 0, 0)]
    cell.soil = PlacedSoil("seagrass_meadow", PlayerId.P1, (0, 0, 0))  # +2 Sun, +1 Plankton
    sun0 = initial_state.players[PlayerId.P1].resources[ResourceType.SUN]

    gains = resolve_production(initial_state)

    assert gains[PlayerId.P1][ResourceType.SUN] == 2
    assert gains[PlayerId.P1][ResourceType.PLANKTON] == 1
    assert initial_state.players[PlayerId.P1].resources[ResourceType.SUN] == sun0 + 2
    assert initial_state.players[PlayerId.P1].produced_resources[ResourceType.SUN] == 2
