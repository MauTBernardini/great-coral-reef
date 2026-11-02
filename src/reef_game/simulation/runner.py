from ..engine.actions import (
    BuyCoralsAction,
    MoveFaunaAction,
    MoveSmallFishAction,
    PassAction,
    PlaceCoralAction,
    PlaceSoilAction,
    PlaceStaghornPairAction,
    PlayFaunaAction,
    PlayParasiteAction,
)
from ..engine.scoring import orthogonal_neighbors_3d, recompute_scores
from ..engine.transitions import apply_action
from ..engine.validators import InvalidActionError, validate_action
from .metrics import summarize_game
from .telemetry import GameTelemetry

STAGHORN_ID = "staghorn"


def enumerate_legal_actions(state, compact_spatial_actions: bool = False):
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
                if compact_spatial_actions:
                    break
            except InvalidActionError:
                pass

    # Pré-filtra colunas com solo antes da validação completa. Em tabuleiros grandes,
    # isso evita testar centenas de células onde nenhum coral pode ser construído.
    coral_positions = []
    for pos, cell in state.board.cells.items():
        if cell.occupant is not None:
            continue
        x, y, z = pos
        if state.board.cells[(x, y, 0)].soil is not None:
            coral_positions.append(pos)

    # Só corais que estão na mão do jogador podem ser construídos.
    for coral_id in set(hand):
        if coral_id not in state.available_corals:
            continue
        coral = state.available_corals[coral_id]
        for pos in coral_positions:
            x, y, z = pos
            if (
                coral.requires_support
                and z > 0
                and state.board.cells[(x, y, z - 1)].occupant is None
            ):
                continue
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
    if "opportunistic_parasite" in state.players[active].instinct_cards:
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

    # Attraction Pheromones (bônus grátis 1x/turno): mover 1 small fish (seu ou do inimigo)
    # para um coral adjacente.
    if (
        "attraction_pheromones" in state.players[active].upgrade_cards
        and not state.players[active].moved_small_fish_this_turn
    ):
        for pos, cell in state.board.cells.items():
            for fid in set(cell.fauna):
                fauna = state.available_fauna.get(fid)
                if fauna is None or not fauna.is_small_fish:
                    continue
                for dest in orthogonal_neighbors_3d(pos):
                    dcell = state.board.cells.get(dest)
                    if dcell is None or dcell.occupant is None:
                        continue
                    action = MoveSmallFishAction(fauna_id=fid, from_position=pos, to_position=dest)
                    try:
                        validate_action(state, action)
                        actions.append(action)
                    except InvalidActionError:
                        pass

    # Staghorn ability: pair placements over independently-legal staghorn spots.
    # (Pairs where the second staghorn stacks directly on the first are supported
    # by the engine but not enumerated here.)
    if hand.count(STAGHORN_ID) >= 2:
        pair_positions = set()
        if compact_spatial_actions:
            legal_set = set(legal_staghorn_positions)
            for first in legal_staghorn_positions:
                for second in orthogonal_neighbors_3d(first):
                    if second in legal_set:
                        pair_positions.add(tuple(sorted((first, second))))

            # Pares adjacentes são os estrategicamente relevantes e evitam O(n²) no
            # sweep. Sem adjacência, mantém uma pequena amostra desconectada.
            if not pair_positions:
                for index, first in enumerate(legal_staghorn_positions[:8]):
                    for second in legal_staghorn_positions[index + 1 : 8]:
                        pair_positions.add((first, second))
        else:
            for index, first in enumerate(legal_staghorn_positions):
                for second in legal_staghorn_positions[index + 1 :]:
                    pair_positions.add((first, second))

        for first, second in pair_positions:
            pair = PlaceStaghornPairAction(first, second)
            try:
                validate_action(state, pair)
                actions.append(pair)
            except InvalidActionError:
                pass

    return actions


def _resolve_instinct_offers(state, agents: dict) -> None:
    """Resolve ofertas de carta pendentes (inicial + de ponds): o agente escolhe 1 carta
    (Instinto OU Upgrade) de cada oferta; as não-escolhidas são descartadas."""
    changed = False
    for pid, player in state.players.items():
        while player.pending_card_offers:
            offer = player.pending_card_offers.pop(0)
            candidates = list(offer.get("instincts", [])) + list(offer.get("upgrades", []))
            if not candidates:
                continue
            choice = agents[pid].choose_card(state, pid, offer)
            if choice not in candidates:
                choice = candidates[0]
            if choice in offer.get("upgrades", []):
                if choice not in player.upgrade_cards:
                    player.upgrade_cards.append(choice)
            elif choice not in player.instinct_cards:
                player.instinct_cards.append(choice)
            changed = True
    if changed:
        recompute_scores(state)


def run_game(
    initial_state,
    agents: dict,
    max_rounds: int | None = None,
    record_telemetry: bool = True,
    compact_spatial_actions: bool = False,
):
    state = initial_state
    _resolve_instinct_offers(state, agents)  # escolha inicial de Instinto
    telemetry = GameTelemetry()
    if record_telemetry:
        telemetry.record_state(state)

    while not state.is_terminal:
        legal_actions = enumerate_legal_actions(
            state, compact_spatial_actions=compact_spatial_actions
        )
        agent = agents[state.active_player]
        action = agent.choose_action(state, legal_actions)
        state = apply_action(state, action, max_rounds=max_rounds)
        _resolve_instinct_offers(state, agents)  # ponds podem render novas ofertas
        if record_telemetry:
            telemetry.record_state(state)

    return state, summarize_game(state, telemetry), telemetry
