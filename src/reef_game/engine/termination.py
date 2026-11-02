def check_game_end(state, max_rounds: int | None = None):
    temperature_limit_reached = state.temperature >= state.critical_temperature
    ph_limit_reached = state.ph <= state.critical_ph
    first_player = next(iter(state.players))
    climate_deck_exhausted = state.active_player == first_player and len(state.climate_deck) == 0
    rounds_limit_reached = max_rounds is not None and state.round >= max_rounds

    if (
        temperature_limit_reached
        or ph_limit_reached
        or climate_deck_exhausted
        or rounds_limit_reached
    ):
        state.is_terminal = True
        _set_winner(state)


def _set_winner(state):
    players = list(state.players.values())
    best_score = max(player.score for player in players)
    leaders = [player for player in players if player.score == best_score]
    state.winner = leaders[0].player_id if len(leaders) == 1 else None
