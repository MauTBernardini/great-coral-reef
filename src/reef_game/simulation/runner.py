from ..engine.actions import (
    BuyCoralsAction,
    PassAction,
    PlaceCoralAction,
    PlaceSoilAction,
    PlaceStaghornPairAction,
)
from ..engine.transitions import apply_action
from ..engine.validators import InvalidActionError, validate_action
from .metrics import summarize_game
from .telemetry import GameTelemetry

STAGHORN_ID = "staghorn"


def enumerate_legal_actions(state):
    actions = [PassAction()]
    legal_staghorn_positions = []
    hand = state.players[state.active_player].hand

    # Comprar 2 cartas de coral (se há baralho e espaço na mão).
    buy = BuyCoralsAction()
    try:
        validate_action(state, buy)
        actions.append(buy)
    except InvalidActionError:
        pass

    # Comprar+baixar solo (topo da pilha) em qualquer célula vazia do fundo (z=0).
    # Afordabilidade não filtra aqui: o topo pode ser caro demais (ação perdida).
    for pos, cell in state.board.cells.items():
        if pos[2] == 0 and cell.soil is None:
            action = PlaceSoilAction(position=pos)
            try:
                validate_action(state, action)
                actions.append(action)
            except InvalidActionError:
                pass

    # Só corais que estão na mão do jogador podem ser construídos.
    for coral_id in set(hand):
        for pos, cell in state.board.cells.items():
            if cell.occupant is None:
                action = PlaceCoralAction(coral_id=coral_id, position=pos)
                try:
                    validate_action(state, action)
                    actions.append(action)
                    if coral_id == STAGHORN_ID:
                        legal_staghorn_positions.append(pos)
                except InvalidActionError:
                    pass

    # Staghorn ability: pair placements over independently-legal staghorn spots.
    # (Pairs where the second staghorn stacks directly on the first are supported
    # by the engine but not enumerated here.)
    for i in range(len(legal_staghorn_positions)):
        for j in range(i + 1, len(legal_staghorn_positions)):
            pair = PlaceStaghornPairAction(
                legal_staghorn_positions[i], legal_staghorn_positions[j]
            )
            try:
                validate_action(state, pair)
                actions.append(pair)
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
