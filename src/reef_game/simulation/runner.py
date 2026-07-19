from ..engine.actions import (
    BuyCoralsAction,
    MoveFaunaAction,
    PassAction,
    PlaceCoralAction,
    PlaceSoilAction,
    PlaceStaghornPairAction,
    PlayFaunaAction,
    PlayParasiteAction,
)
from ..engine.scoring import orthogonal_neighbors_3d
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
        if coral_id not in state.available_corals:
            continue
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

    # Jogar fauna da mão sobre um coral seu com capacidade livre.
    active = state.active_player
    own_coral_positions = [
        pos for pos, cell in state.board.cells.items()
        if cell.occupant is not None and cell.occupant.owner == active
    ]
    for fauna_id in set(hand):
        if fauna_id not in state.available_fauna:
            continue
        for pos in own_coral_positions:
            action = PlayFaunaAction(fauna_id=fauna_id, position=pos)
            try:
                validate_action(state, action)
                actions.append(action)
            except InvalidActionError:
                pass

    # Parasitismo: jogar fauna da mão em coral INIMIGO (só quem tem a carta de Instinto).
    if state.players[active].instinct_card == "opportunistic_parasite":
        enemy_coral_positions = [
            pos for pos, cell in state.board.cells.items()
            if cell.occupant is not None and cell.occupant.owner != active
        ]
        for fauna_id in set(hand):
            if fauna_id not in state.available_fauna:
                continue
            for pos in enemy_coral_positions:
                action = PlayParasiteAction(fauna_id=fauna_id, position=pos)
                try:
                    validate_action(state, action)
                    actions.append(action)
                except InvalidActionError:
                    pass

    # Mover fauna móvel (Moon Jelly) para um coral seu vizinho (1x/rodada).
    own_position_set = set(own_coral_positions)
    for pos in own_coral_positions:
        cell = state.board.cells[pos]
        for fauna_id in set(cell.fauna):
            fauna = state.available_fauna.get(fauna_id)
            if fauna is None or not fauna.can_move:
                continue
            for dest in orthogonal_neighbors_3d(pos):
                if dest not in own_position_set:
                    continue
                action = MoveFaunaAction(fauna_id=fauna_id, from_position=pos, to_position=dest)
                try:
                    validate_action(state, action)
                    actions.append(action)
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
    # Escolha de Instinto (1 de 2) no início da partida, por jogador.
    for pid, player in state.players.items():
        if player.instinct_options and player.instinct_card is None:
            player.instinct_card = agents[pid].choose_instinct(state, pid, player.instinct_options)
    telemetry = GameTelemetry()
    telemetry.record_state(state)

    while not state.is_terminal:
        legal_actions = enumerate_legal_actions(state)
        agent = agents[state.active_player]
        action = agent.choose_action(state, legal_actions)
        state = apply_action(state, action, max_rounds=max_rounds)
        telemetry.record_state(state)

    return state, summarize_game(state, telemetry), telemetry
