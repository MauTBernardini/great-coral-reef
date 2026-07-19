"""Long-term (strategic) agent — the opposite of the myopic GreedyAgent.

Where the greedy maximizes the immediate score of a single action, this agent
invests for the future:

* Values **soil production as a stream** over the game left (a soil bought early
  pays off for many rounds), so it builds economy first.
* Rewards **structural potential**: foundations that can be stacked on (Grooved
  Brain gives +1 per coral above), staghorn **cluster seeds** (a lone staghorn is
  worth ~1 now but compounds as the cluster grows), and top-layer Elkhorns (which
  enable the +1 Sun production cluster).
* Loves the **staghorn pair** (starts a 2-cluster in one action) — exactly what
  the greedy ignores.
* Refuses to waste turns hoarding useless flora; it would rather pass.

It is a heuristic (no search), evaluating each action cheaply — same order of cost
as the greedy — but with a value function tuned for the long game.
"""

from ..engine.economy import effective_cost
from ..engine.enums import ActionType, ResourceType
from ..engine.scoring import STAGHORN_ID as _STAGHORN_ID
from ..engine.scoring import orthogonal_neighbors_3d, score_coral
from .base import BaseAgent

STAGHORN_ID = _STAGHORN_ID
GROOVED_BRAIN_ID = "grooved_brain_coral"
ELKHORN_ID = "elkhorn"
STAGHORN_PAIR_PLANKTON_SURCHARGE = 1

# Sol vale mais que Plâncton na economia atual (só o Elkhorn/par gastam Plâncton).
_PRODUCTION_WEIGHT = {ResourceType.SUN: 1.0, ResourceType.PLANKTON: 0.6}

W_POTENTIAL = 0.5   # peso do potencial estrutural (setup futuro)
W_SOIL = 0.30       # peso do fluxo de produção do solo ao longo do jogo
W_COST = 0.20       # aversão a custo
HORIZON_CAP = 10.0  # teto de "rodadas restantes" estimadas


def _mock_placed(coral_id, position, owner):
    return type("Placed", (), {"coral_id": coral_id, "position": position, "owner": owner})()


def _rounds_left_estimate(state) -> float:
    """Aproxima quantas rodadas ainda restam a partir da folga de temperatura.

    Quanto mais cedo (mais frio), maior o horizonte -> mais valor à produção.
    """
    room = state.critical_temperature - state.temperature
    step = state.temperature_step or 0.5
    return max(0.5, min(HORIZON_CAP, room / step))


def _empty_buildable_neighbors(state, position) -> int:
    count = 0
    for pos in orthogonal_neighbors_3d(position):
        cell = state.board.cells.get(pos)
        if cell is not None and cell.occupant is None:
            count += 1
    return count


def _coral_potential(state, coral_id, position) -> float:
    x, y, z = position
    top = state.board.max_layers - 1
    if coral_id == GROOVED_BRAIN_ID:
        # Recompensa espaço para empilhar acima (cada coral acima dá +1 ao brain).
        return float(top - z)
    if coral_id == STAGHORN_ID:
        # Semente de cluster: quanto mais vizinhos livres, mais o cluster pode crescer.
        return float(_empty_buildable_neighbors(state, position))
    if coral_id == ELKHORN_ID:
        # No topo, habilita o cluster de produção de Sol.
        return 1.0 if z == top else 0.0
    return 0.0


class LongTermAgent(BaseAgent):
    def choose_action(self, state, legal_actions):
        best = None
        best_value = float("-inf")
        for action in legal_actions:
            value = self._value_of(state, action)
            if value > best_value:
                best = action
                best_value = value
        return best

    def _value_of(self, state, action):
        owner = state.active_player

        if action.action_type == ActionType.PASS:
            # Preferível a desperdiçar turno com flora inútil ou compra impagável.
            return -1.0

        if action.action_type == ActionType.BUY_FLORA:
            # Flora não tem efeito ainda; evitar encher a mão à toa.
            return -2.0

        if action.action_type == ActionType.PLACE_SOIL:
            soil_id = state.soil_pile[0]
            soil = state.available_soils[soil_id]
            sun_cost = soil.cost.values.get(ResourceType.SUN, 0)
            if state.players[owner].resources.get(ResourceType.SUN, 0) < sun_cost:
                return -50.0
            per_round = sum(_PRODUCTION_WEIGHT.get(r, 0.0) * a for r, a in soil.production.items())
            stream = per_round * _rounds_left_estimate(state)
            cost = sum(soil.cost.values.values())
            return W_SOIL * stream - W_COST * cost

        if action.action_type == ActionType.PLACE_STAGHORN_PAIR:
            coral = state.available_corals[STAGHORN_ID]
            first, second = action.first_position, action.second_position
            immediate = (
                score_coral(state, _mock_placed(STAGHORN_ID, first, owner))
                + score_coral(state, _mock_placed(STAGHORN_ID, second, owner))
            )
            if second in orthogonal_neighbors_3d(first):
                immediate += 2.0  # os dois staghorns se conectam entre si
            potential = _coral_potential(state, STAGHORN_ID, first) + _coral_potential(
                state, STAGHORN_ID, second
            )
            cost = STAGHORN_PAIR_PLANKTON_SURCHARGE + sum(
                sum(effective_cost(state, coral, p).values()) for p in (first, second)
            )
            return immediate + W_POTENTIAL * potential - W_COST * cost

        coral = state.available_corals[action.coral_id]
        immediate = score_coral(state, _mock_placed(action.coral_id, action.position, owner))
        potential = _coral_potential(state, action.coral_id, action.position)
        cost = sum(effective_cost(state, coral, action.position).values())
        return immediate + W_POTENTIAL * potential - W_COST * cost
