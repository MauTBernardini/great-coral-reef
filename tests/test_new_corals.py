import pytest

from reef_game.engine.actions import PlaceCoralAction
from reef_game.engine.enums import PlayerId, ResourceType
from reef_game.engine.models import PlacedCoral, PlacedSoil
from reef_game.engine.scoring import score_coral
from reef_game.engine.transitions import apply_action
from reef_game.engine.validators import InvalidActionError, validate_action


def _soil(state, position, soil_id, owner=PlayerId.P1):
    state.board.cells[position].soil = PlacedSoil(soil_id, owner, position)


def _coral(state, coral_id, position, owner):
    state.board.cells[position].occupant = PlacedCoral(
        instance_id=f"{coral_id}_{position}", coral_id=coral_id, owner=owner, position=position
    )


# ---------------- Fox Coral ----------------

def test_fox_coral_scores_two_per_empty_same_layer_neighbor(initial_state):
    _coral(initial_state, "fox_coral", (1, 1, 1), PlayerId.P1)
    fox = initial_state.board.cells[(1, 1, 1)].occupant
    # 4 vizinhos de mesma camada, todos vazios -> 8
    assert score_coral(initial_state, fox) == 8
    # Ocupa um vizinho -> 3 vazios -> 6
    _coral(initial_state, "grooved_brain_coral", (2, 1, 1), PlayerId.P1)
    assert score_coral(initial_state, fox) == 6


def test_fox_coral_only_on_layers_2_and_3(initial_state):
    _soil(initial_state, (1, 1, 0), "sandy_bed")
    with pytest.raises(InvalidActionError):
        validate_action(initial_state, PlaceCoralAction("fox_coral", (1, 1, 0)))  # z=0 proibido


def test_fox_coral_blocks_opponent_from_adjacent_cell(initial_state):
    # P1 fox em (1,1,1); P2 tenta construir vizinho (2,1,1).
    _coral(initial_state, "fox_coral", (1, 1, 1), PlayerId.P1)
    _soil(initial_state, (2, 1, 0), "sandy_bed", owner=PlayerId.P2)
    _coral(initial_state, "grooved_brain_coral", (2, 1, 0), PlayerId.P2)  # suporte p/ (2,1,1)
    initial_state.active_player = PlayerId.P2
    with pytest.raises(InvalidActionError):
        validate_action(initial_state, PlaceCoralAction("grooved_brain_coral", (2, 1, 1)))


# ---------------- Sun Coral ----------------

def test_sun_coral_requires_dark_overhang_and_scores_five(initial_state):
    _soil(initial_state, (0, 0, 0), "dark_overhang")
    s = apply_action(initial_state, PlaceCoralAction("sun_coral", (0, 0, 0)))
    p1 = s.players[PlayerId.P1]
    assert s.board.cells[(0, 0, 0)].occupant.coral_id == "sun_coral"
    assert p1.resources[ResourceType.PLANKTON] == 7  # 10 - 3
    assert p1.score == 5


def test_sun_coral_rejected_on_wrong_soil(initial_state):
    _soil(initial_state, (0, 0, 0), "sandy_bed")
    with pytest.raises(InvalidActionError):
        validate_action(initial_state, PlaceCoralAction("sun_coral", (0, 0, 0)))


# ---------------- Gorgonian Sea Fan ----------------

def test_gorgonian_scores_two_per_fan_in_column(initial_state):
    _coral(initial_state, "gorgonian_sea_fan", (0, 0, 0), PlayerId.P1)
    _coral(initial_state, "gorgonian_sea_fan", (0, 0, 1), PlayerId.P1)
    a = initial_state.board.cells[(0, 0, 0)].occupant
    b = initial_state.board.cells[(0, 0, 1)].occupant
    # 2 fans na coluna -> cada um 2*2 = 4
    assert score_coral(initial_state, a) == 4
    assert score_coral(initial_state, b) == 4


# ---------------- Branched Finger Coral ----------------

def test_branched_finger_refunds_sun_on_rocky_reef(initial_state):
    _soil(initial_state, (0, 0, 0), "rocky_reef")
    sun_before = initial_state.players[PlayerId.P1].resources[ResourceType.SUN]
    s = apply_action(initial_state, PlaceCoralAction("branched_finger_coral", (0, 0, 0)))
    p1 = s.players[PlayerId.P1]
    # custo 1 Sol, -1 do rocky reef -> 0, +1 de rebate -> saldo +1
    assert p1.resources[ResourceType.SUN] == sun_before + 1
    assert p1.score == 1


def test_branched_finger_no_refund_on_other_soil(initial_state):
    _soil(initial_state, (0, 0, 0), "sandy_bed")
    sun_before = initial_state.players[PlayerId.P1].resources[ResourceType.SUN]
    s = apply_action(initial_state, PlaceCoralAction("branched_finger_coral", (0, 0, 0)))
    # custo 1 Sol, sem desconto nem rebate -> -1
    assert s.players[PlayerId.P1].resources[ResourceType.SUN] == sun_before - 1


# ---------------- Bubble Coral ----------------

def test_bubble_scores_when_adjacent_to_two_coral_types(initial_state):
    _coral(initial_state, "grooved_brain_coral", (2, 1, 0), PlayerId.P1)
    _coral(initial_state, "elkhorn", (0, 1, 0), PlayerId.P1)
    _coral(initial_state, "bubble_coral", (1, 1, 0), PlayerId.P1)
    bubble = initial_state.board.cells[(1, 1, 0)].occupant
    assert score_coral(initial_state, bubble) == 2


def test_bubble_scores_zero_with_one_adjacent_type(initial_state):
    _coral(initial_state, "grooved_brain_coral", (2, 1, 0), PlayerId.P1)
    _coral(initial_state, "bubble_coral", (1, 1, 0), PlayerId.P1)
    bubble = initial_state.board.cells[(1, 1, 0)].occupant
    assert score_coral(initial_state, bubble) == 0
