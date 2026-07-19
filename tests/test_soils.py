import pytest

from reef_game.engine.actions import PlaceCoralAction, PlaceSoilAction
from reef_game.engine.enums import PlayerId, ResourceType
from reef_game.engine.production import resolve_production
from reef_game.engine.transitions import apply_action
from reef_game.engine.validators import InvalidActionError, validate_action


def test_coral_requires_soil_at_column_base(initial_state):
    # No soil anywhere -> any coral placement is rejected.
    with pytest.raises(InvalidActionError):
        validate_action(initial_state, PlaceCoralAction("grooved_brain_coral", (0, 0, 0)))


def test_place_soil_then_coral(initial_state):
    s = apply_action(initial_state, PlaceSoilAction("sandy_bed", (0, 0, 0)))  # P1 buys soil
    p1 = s.players[PlayerId.P1]
    assert s.board.cells[(0, 0, 0)].soil.soil_id == "sandy_bed"
    assert s.board.cells[(0, 0, 0)].soil.owner == PlayerId.P1
    assert p1.resources[ResourceType.SUN] == 9  # 10 - 1
    assert s.soil_supply["sandy_bed"] == 7      # 8 - 1

    # Now a coral can be built on that column (P2 passes to return to P1).
    s = apply_action(s, PlaceSoilAction("sandy_bed", (3, 3, 0)))  # P2
    s = apply_action(s, PlaceCoralAction("grooved_brain_coral", (0, 0, 0)))  # P1
    assert s.board.cells[(0, 0, 0)].occupant.coral_id == "grooved_brain_coral"


def test_soil_only_on_bottom_layer(initial_state):
    with pytest.raises(InvalidActionError):
        validate_action(initial_state, PlaceSoilAction("sandy_bed", (0, 0, 1)))


def test_soil_supply_is_enforced(initial_state):
    initial_state.soil_supply["seagrass_meadow"] = 0
    with pytest.raises(InvalidActionError):
        validate_action(initial_state, PlaceSoilAction("seagrass_meadow", (0, 0, 0)))


def test_cannot_place_soil_twice_on_same_cell(initial_state):
    s = apply_action(initial_state, PlaceSoilAction("sandy_bed", (0, 0, 0)))
    with pytest.raises(InvalidActionError):
        validate_action(s, PlaceSoilAction("rocky_reef", (0, 0, 0)))


def test_rocky_reef_discounts_corals_built_on_it(initial_state):
    from reef_game.engine.economy import effective_cost

    initial_state.board.cells[(0, 0, 0)].soil = None
    s = apply_action(initial_state, PlaceSoilAction("rocky_reef", (0, 0, 0)))  # P1
    coral = s.available_corals["grooved_brain_coral"]  # normally 2 Sun
    cost = effective_cost(s, coral, (0, 0, 0))
    assert cost[ResourceType.SUN] == 1  # 2 - 1 (rocky reef)


def test_soil_produces_for_its_owner(initial_state):
    from reef_game.engine.models import PlacedSoil

    # Seagrass Meadow: +2 Sun, +1 Plankton per round, owned by P1.
    cell = initial_state.board.cells[(0, 0, 0)]
    cell.soil = PlacedSoil("seagrass_meadow", PlayerId.P1, (0, 0, 0))
    sun0 = initial_state.players[PlayerId.P1].resources[ResourceType.SUN]
    plk0 = initial_state.players[PlayerId.P1].resources[ResourceType.PLANKTON]

    gains = resolve_production(initial_state)

    assert gains[PlayerId.P1][ResourceType.SUN] == 2
    assert gains[PlayerId.P1][ResourceType.PLANKTON] == 1
    assert initial_state.players[PlayerId.P1].resources[ResourceType.SUN] == sun0 + 2
    assert initial_state.players[PlayerId.P1].resources[ResourceType.PLANKTON] == plk0 + 1
    assert initial_state.players[PlayerId.P1].produced_resources[ResourceType.SUN] == 2
