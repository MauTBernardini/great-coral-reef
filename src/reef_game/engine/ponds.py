"""Sistema de 'ponds'.

Uma pond é um ciclo fechado de corais numa ÚNICA camada (o menor é um bloco 2x2),
com >=4 corais e >=2 colunas "de altura" (coluna com 2+ corais empilhados). É formada
por quem coloca o coral que FECHA o ciclo — esse jogador vira dono (mesmo que os demais
corais sejam do oponente => 'roubo'). Ao formar, o dono ganha uma oferta de Instinto
(escolher 1 de 2), até o teto de instintos. Entre duas ponds só pode haver 1 coral em
comum (regra de interseção): um ciclo que compartilharia >=2 corais com uma pond
existente não forma nova pond.
"""

from collections import deque

from .models import PondState

# Teto de cartas por jogador: 1 instinto inicial + 3 cartas de pond (instinto e/ou upgrade).
MAX_CARDS = 4
MIN_POND_CORALS = 4
MIN_TALL_COLUMNS = 2
TALL_MIN_HEIGHT = 2


def _same_layer_neighbors(pos):
    x, y, z = pos
    return [(x + 1, y, z), (x - 1, y, z), (x, y + 1, z), (x, y - 1, z)]


def _coral_graph_on_layer(state, z):
    """Grafo de corais na camada z: pos -> set(vizinhos ortogonais com coral)."""
    corals = {
        pos for pos, cell in state.board.cells.items()
        if pos[2] == z and cell.occupant is not None
    }
    graph = {}
    for pos in corals:
        graph[pos] = {n for n in _same_layer_neighbors(pos) if n in corals}
    return graph


def _shortest_path(graph, start, goal, blocked):
    """Menor caminho (lista de nós) start->goal sem passar por ``blocked``."""
    if start == goal:
        return [start]
    prev = {start: None}
    q = deque([start])
    while q:
        node = q.popleft()
        for nb in graph.get(node, ()):
            if nb == blocked or nb in prev:
                continue
            prev[nb] = node
            if nb == goal:
                path = [goal]
                while prev[path[-1]] is not None:
                    path.append(prev[path[-1]])
                return list(reversed(path))
            q.append(nb)
    return None


def _shortest_cycle_through(graph, v):
    """Menor ciclo (conjunto de células) que passa por ``v``, ou None."""
    neighbors = list(graph.get(v, ()))
    best = None
    for i in range(len(neighbors)):
        for j in range(i + 1, len(neighbors)):
            path = _shortest_path(graph, neighbors[i], neighbors[j], blocked=v)
            if path is None:
                continue
            cycle = set(path)
            cycle.add(v)
            if best is None or len(cycle) < len(best):
                best = cycle
    return best


def _column_height(state, x, y):
    """Quantos corais empilhados há na coluna (x, y), somando todas as camadas."""
    count = 0
    for z in range(state.board.max_layers):
        cell = state.board.cells.get((x, y, z))
        if cell is not None and cell.occupant is not None:
            count += 1
    return count


def detect_new_pond(state, position):
    """Se o coral em ``position`` acabou de fechar um ciclo válido, retorna o conjunto
    de células (frozenset) da pond; senão, None."""
    z = position[2]
    graph = _coral_graph_on_layer(state, z)
    cycle = _shortest_cycle_through(graph, position)
    if cycle is None or len(cycle) < MIN_POND_CORALS:
        return None

    tall = sum(1 for (x, y, _z) in cycle if _column_height(state, x, y) >= TALL_MIN_HEIGHT)
    if tall < MIN_TALL_COLUMNS:
        return None

    # Regra de interseção: no máximo 1 coral compartilhado com cada pond existente.
    for pond in state.ponds:
        if len(cycle & pond.cells) >= 2:
            return None

    return frozenset(cycle)


def _grant_card_offer(state, player_id):
    """Oferta de pond: 2 Instintos + 2 Upgrades, para o jogador escolher 1 (no runner)."""
    player = state.players[player_id]
    owned = len(player.instinct_cards) + len(player.upgrade_cards)
    if owned + len(player.pending_card_offers) >= MAX_CARDS:
        return
    instincts = [state.instinct_deck.pop(0) for _ in range(min(2, len(state.instinct_deck)))]
    upgrades = [state.upgrade_deck.pop(0) for _ in range(min(2, len(state.upgrade_deck)))]
    if instincts or upgrades:
        player.pending_card_offers.append({"instincts": instincts, "upgrades": upgrades})


def maybe_form_pond(state, position, placer):
    """Após colocar um coral, tenta formar uma pond fechada por ele. Se formar, o
    ``placer`` vira dono e ganha uma oferta de carta (Instinto ou Upgrade), até o teto."""
    cells = detect_new_pond(state, position)
    if cells is None:
        return None
    state.ponds.append(PondState(cells=cells, owner=placer))
    _grant_card_offer(state, placer)
    return cells
