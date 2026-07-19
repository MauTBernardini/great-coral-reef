import pytest

from reef_game.engine.actions import PlayFaunaAction
from reef_game.engine.enums import PlayerId, ResourceType
from reef_game.engine.models import PlacedCoral, PlacedSoil
from reef_game.engine.scoring import occupied_habitat
from reef_game.engine.transitions import apply_action
from reef_game.engine.validators import InvalidActionError, validate_action


def _coral(state, coral_id, pos, owner=PlayerId.P1):
    state.board.cells[pos].occupant = PlacedCoral(f"{coral_id}_{pos}", coral_id, owner, pos)


def _soil(state, pos, soil_id, owner=PlayerId.P1):
    state.board.cells[pos].soil = PlacedSoil(soil_id, owner, pos)


def _give(state, fauna_id, owner=PlayerId.P1):
    state.players[owner].hand.append(fauna_id)


def test_play_fauna_on_coral_scores_and_pays(initial_state):
    _coral(initial_state, "staghorn", (0, 0, 0))  # habitat 2
    _give(initial_state, "damselfish")  # custo 1 Sol, score 1
    sun0 = initial_state.players[PlayerId.P1].resources[ResourceType.SUN]

    s = apply_action(initial_state, PlayFaunaAction("damselfish", (0, 0, 0)))

    assert "damselfish" in s.board.cells[(0, 0, 0)].fauna
    assert s.players[PlayerId.P1].resources[ResourceType.SUN] == sun0 - 1
    assert "damselfish" not in s.players[PlayerId.P1].hand  # carta gasta
    # staghorn(1) + damselfish(1) = 2
    assert s.players[PlayerId.P1].score == 2


def test_fauna_needs_card_in_hand(initial_state):
    _coral(initial_state, "staghorn", (0, 0, 0))
    with pytest.raises(InvalidActionError):
        validate_action(initial_state, PlayFaunaAction("damselfish", (0, 0, 0)))


def test_fauna_respects_habitat_capacity(initial_state):
    _coral(initial_state, "grooved_brain_coral", (0, 0, 0))  # habitat 1
    initial_state.board.cells[(0, 0, 0)].fauna = ["damselfish"]  # já ocupa 1
    _give(initial_state, "clownfish")
    with pytest.raises(InvalidActionError):
        validate_action(initial_state, PlayFaunaAction("clownfish", (0, 0, 0)))


def test_mandarin_only_on_rocky_reef(initial_state):
    _coral(initial_state, "grooved_brain_coral", (0, 0, 0))
    _soil(initial_state, (0, 0, 0), "sandy_bed")
    _give(initial_state, "mandarin_dragonet")
    initial_state.players[PlayerId.P1].resources[ResourceType.PLANKTON] = 5

    with pytest.raises(InvalidActionError):
        validate_action(initial_state, PlayFaunaAction("mandarin_dragonet", (0, 0, 0)))

    initial_state.board.cells[(0, 0, 0)].soil = PlacedSoil("rocky_reef", PlayerId.P1, (0, 0, 0))
    validate_action(initial_state, PlayFaunaAction("mandarin_dragonet", (0, 0, 0)))  # não levanta


def test_seahorse_free_on_gorgonian_and_scores_adjacent_seagrass(initial_state):
    _coral(initial_state, "gorgonian_sea_fan", (1, 1, 0))  # habitat 2
    _soil(initial_state, (2, 1, 0), "seagrass_meadow")  # adjacente a (1,1,0)
    _give(initial_state, "seahorse")

    s = apply_action(initial_state, PlayFaunaAction("seahorse", (1, 1, 0)))

    assert occupied_habitat(s, s.board.cells[(1, 1, 0)]) == 0  # não ocupa em Gorgonian
    # gorgonian(2) + seahorse(1 seagrass adjacente) = 3
    assert s.players[PlayerId.P1].score == 3


def test_parrotfish_scores_one_plus_sandy_beds(initial_state):
    _coral(initial_state, "staghorn", (0, 0, 0))
    _soil(initial_state, (1, 0, 0), "sandy_bed")
    _soil(initial_state, (2, 0, 0), "sandy_bed")
    _give(initial_state, "parrotfish")
    initial_state.players[PlayerId.P1].resources[ResourceType.SUN] = 5

    s = apply_action(initial_state, PlayFaunaAction("parrotfish", (0, 0, 0)))

    # staghorn(1) + parrotfish(1 + 2 sandy) = 4
    assert s.players[PlayerId.P1].score == 4


def test_fauna_deck_counts_respect_rarity(fauna_defs):
    # Mais caro (Sol+Plâncton) = mais raro; Parrotfish o mais raro.
    counts = {fid: f.deck_count for fid, f in fauna_defs.items()}
    assert counts["parrotfish"] == min(counts.values())
    assert counts["clownfish"] > counts["mandarin_dragonet"] > counts["parrotfish"]
