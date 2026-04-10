from .enums import PlayerId


def check_game_end(state, max_rounds: int | None = None):
    temperature_limit_reached = state.temperature >= state.critical_temperature
    ph_limit_reached = state.ph <= state.critical_ph
    climate_deck_exhausted = state.active_player == PlayerId.P1 and len(state.climate_deck) == 0
    rounds_limit_reached = max_rounds is not None and state.round >= max_rounds

    if temperature_limit_reached or ph_limit_reached or climate_deck_exhausted or rounds_limit_reached:
        state.is_terminal = True
        _set_winner(state)


def _set_winner(state):
    players = list(state.players.values())
    p1, p2 = players[0], players[1]

    if p1.score > p2.score:
        state.winner = p1.player_id
    elif p2.score > p1.score:
        state.winner = p2.player_id
    else:
        state.winner = None
