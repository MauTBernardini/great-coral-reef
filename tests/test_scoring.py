from reef_game.engine.actions import PlaceCoralAction
from reef_game.engine.enums import PlayerId, ResourceType
from reef_game.engine.transitions import apply_action


def test_grooved_brain_scores_one_plus_corals_above(soiled_state):
    # P1 stacks a column on its Grooved Brain; the brain should score 1 + 2 above.
    s = apply_action(soiled_state, PlaceCoralAction("grooved_brain_coral", (0, 0, 0)))
    s = apply_action(s, PlaceCoralAction("grooved_brain_coral", (3, 3, 0)))  # P2
    s = apply_action(s, PlaceCoralAction("staghorn", (0, 0, 1)))  # P1
    s = apply_action(s, PlaceCoralAction("grooved_brain_coral", (3, 3, 1)))  # P2
    s = apply_action(s, PlaceCoralAction("staghorn", (0, 0, 2)))  # P1

    # brain(0,0,0): 1 + 2 above = 3
    # staghorn(0,0,1): 1 + 1 connected (0,0,2) = 2
    # staghorn(0,0,2): 1 + 1 connected (0,0,1) = 2
    assert s.players[PlayerId.P1].score == 7


def test_elkhorn_scores_two_only_on_top_layer(soiled_state):
    top_layer = soiled_state.board.max_layers - 1

    # Not on top -> 0 points.
    s = apply_action(soiled_state, PlaceCoralAction("elkhorn", (0, 0, 0)))  # P1, z=0
    assert s.players[PlayerId.P1].score == 0

    # Build a support column, then an elkhorn on the top layer -> 2 points.
    s = apply_action(s, PlaceCoralAction("grooved_brain_coral", (3, 3, 0)))  # P2
    s = apply_action(s, PlaceCoralAction("grooved_brain_coral", (2, 0, 0)))  # P1 base
    s = apply_action(s, PlaceCoralAction("grooved_brain_coral", (3, 3, 1)))  # P2
    s = apply_action(s, PlaceCoralAction("grooved_brain_coral", (2, 0, 1)))  # P1 z=1
    s = apply_action(s, PlaceCoralAction("grooved_brain_coral", (3, 2, 0)))  # P2
    s = apply_action(s, PlaceCoralAction("elkhorn", (2, 0, top_layer)))  # P1 top elkhorn

    placed = s.board.cells[(2, 0, top_layer)].occupant
    assert placed is not None and placed.coral_id == "elkhorn"
    # elkhorn on top = 2; the earlier ground elkhorn(0,0,0) still scores 0.
    # brain(2,0,0): 1 + 2 above = 3 ; brain(2,0,1): 1 + 1 above = 2 ; elkhorn top = 2 -> 7
    assert s.players[PlayerId.P1].score == 7


def test_staghorn_counts_connected_staghorns(soiled_state):
    # Two orthogonally-adjacent staghorns: each scores 1 (self) + 1 (neighbour) = 2.
    s = apply_action(soiled_state, PlaceCoralAction("grooved_brain_coral", (0, 0, 0)))
    s = apply_action(s, PlaceCoralAction("grooved_brain_coral", (3, 3, 0)))  # P2
    s = apply_action(s, PlaceCoralAction("grooved_brain_coral", (1, 0, 0)))  # P1 support
    s = apply_action(s, PlaceCoralAction("grooved_brain_coral", (3, 2, 0)))  # P2
    s = apply_action(s, PlaceCoralAction("staghorn", (0, 0, 1)))  # P1
    s = apply_action(s, PlaceCoralAction("grooved_brain_coral", (2, 2, 0)))  # P2
    s = apply_action(s, PlaceCoralAction("staghorn", (1, 0, 1)))  # P1 adjacent

    # staghorns each 2 -> 4 ; brains each 1 + 1 above -> 4 ; total 8
    assert s.players[PlayerId.P1].score == 8


def test_grooved_brain_discounts_coral_directly_above(soiled_state):
    # P1 brain on the ground costs 2 Sun -> 8 left.
    s = apply_action(soiled_state, PlaceCoralAction("grooved_brain_coral", (0, 0, 0)))
    s = apply_action(s, PlaceCoralAction("grooved_brain_coral", (3, 3, 0)))  # P2
    s = apply_action(s, PlaceCoralAction("elkhorn", (0, 0, 1)))  # P1 above brain

    p1 = s.players[PlayerId.P1]
    # Elkhorn normally costs 3 Sun; -1 for sitting on the brain -> 2. 8 - 2 = 6.
    assert p1.resources[ResourceType.SUN] == 6
    assert p1.resources[ResourceType.PLANKTON] == 9
