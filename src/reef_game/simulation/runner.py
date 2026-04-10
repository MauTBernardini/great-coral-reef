from ..engine.actions import PassAction, PlaceCoralAction
from ..engine.transitions import apply_action
from ..engine.validators import InvalidActionError, validate_action
from .metrics import summarize_game
from .telemetry import GameTelemetry


def enumerate_legal_actions(state):
    actions = [PassAction()]

    for coral_id in state.available_corals:
        for pos, cell in state.board.cells.items():
            if cell.occupant is None:
                action = PlaceCoralAction(coral_id=coral_id, position=pos)
                try:
                    validate_action(state, action)
                    actions.append(action)
                except InvalidActionError:
                    pass

    return actions


def run_game(initial_state, agents: dict, max_rounds: int | None = None):
    state = initial_state
    telemetry = GameTelemetry()
    telemetry.record_state(state)

    while not state.is_terminal:
        legal_actions = enumerate_legal_actions(state)
        agent = agents[state.active_player]
        action = agent.choose_action(state, legal_actions)
        state = apply_action(state, action, max_rounds=max_rounds)
        telemetry.record_state(state)

    return state, summarize_game(state, telemetry), telemetry
