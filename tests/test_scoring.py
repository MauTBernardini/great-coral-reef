from reef_game.engine.actions import PlaceCoralAction
from reef_game.engine.transitions import apply_action


def test_vertical_placement_scores_bonus(initial_state):
    state = apply_action(initial_state, PlaceCoralAction("staghorn", (0, 0, 0)))
    state = apply_action(state, PlaceCoralAction("staghorn", (2, 2, 0)))
    state = apply_action(state, PlaceCoralAction("staghorn", (0, 0, 1)))

    assert state.players[list(state.players.keys())[0]].score >= 5


def test_adjacency_bonus_scores(initial_state):
    state = apply_action(initial_state, PlaceCoralAction("staghorn", (0, 0, 0)))
    state = apply_action(state, PlaceCoralAction("staghorn", (2, 2, 0)))
    state = apply_action(state, PlaceCoralAction("staghorn", (1, 0, 0)))

    assert state.players[list(state.players.keys())[0]].score >= 5
