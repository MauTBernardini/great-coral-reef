from copy import deepcopy

from reef_game.engine.actions import PassAction
from reef_game.engine.enums import PlayerId
from reef_game.engine.models import ClimateCard
from reef_game.engine.setup import create_initial_state, load_balance_rules
from reef_game.engine.termination import _set_winner
from reef_game.engine.transitions import apply_action


def _four_player_state(initial_state, rotate_start_player=False):
    rules = load_balance_rules("configs/balance_rules.yaml")
    rules["climate"]["deck_size"] = 0
    rules["players"]["rotate_start_player"] = rotate_start_player
    return create_initial_state(
        seed=initial_state.seed,
        coral_definitions=initial_state.available_corals,
        balance_rules=rules,
        climate_config={"deck": []},
        soil_definitions=initial_state.available_soils,
        fauna_definitions=initial_state.available_fauna,
    )


def test_production_configuration_creates_16x16x3_board_and_four_players(initial_state):
    state = _four_player_state(initial_state)

    assert (state.board.width, state.board.height, state.board.max_layers) == (16, 16, 3)
    assert len(state.board.cells) == 16 * 16 * 3
    assert list(state.players) == [PlayerId.P1, PlayerId.P2, PlayerId.P3, PlayerId.P4]
    assert all(len(player.hand) == 5 for player in state.players.values())


def test_turns_rotate_across_four_players_and_skip_players_who_passed(initial_state):
    state = _four_player_state(initial_state)

    state = apply_action(state, PassAction())
    assert state.active_player == PlayerId.P2
    state = apply_action(state, PassAction())
    assert state.active_player == PlayerId.P3
    state = apply_action(state, PassAction())
    assert state.active_player == PlayerId.P4
    state = apply_action(state, PassAction())

    assert state.round == 2
    assert state.active_player == PlayerId.P1
    assert all(not player.passed_this_round for player in state.players.values())


def test_winner_is_highest_scoring_player_and_ties_draw(initial_state):
    state = _four_player_state(initial_state)
    state.players[PlayerId.P1].score = 5
    state.players[PlayerId.P2].score = 7
    state.players[PlayerId.P3].score = 12
    state.players[PlayerId.P4].score = 9
    _set_winner(state)
    assert state.winner == PlayerId.P3

    tied = deepcopy(state)
    tied.players[PlayerId.P4].score = 12
    _set_winner(tied)
    assert tied.winner is None


def test_starting_player_rotates_each_round_when_enabled(initial_state):
    state = _four_player_state(initial_state, rotate_start_player=True)
    state.climate_deck = [
        ClimateCard(card_id=f"stable-{index}", era=1, label="Stable")
        for index in range(10)
    ]

    for expected_starter in (PlayerId.P2, PlayerId.P3, PlayerId.P4, PlayerId.P1):
        for _ in state.players:
            state = apply_action(state, PassAction())
        assert state.active_player == expected_starter
