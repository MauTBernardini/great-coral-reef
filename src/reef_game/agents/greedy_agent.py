from ..engine.economy import effective_cost
from ..engine.enums import ActionType, ResourceType
from ..engine.scoring import score_coral, score_fauna
from .base import BaseAgent

STAGHORN_ID = "staghorn"
STAGHORN_PAIR_PLANKTON_SURCHARGE = 1
# Peso da produção ao avaliar solos (Sol vale mais que Plâncton no jogo atual).
_PRODUCTION_WEIGHT = {ResourceType.SUN: 1.0, ResourceType.PLANKTON: 0.5}


def _mock_placed(coral_id, position, owner):
    return type("Placed", (), {"coral_id": coral_id, "position": position, "owner": owner})()


class GreedyAgent(BaseAgent):
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
            return -9999

        if action.action_type == ActionType.BUY_CORALS:
            # Comprar cartas é essencial (só constrói o que está na mão).
            hand = state.players[owner].hand
            return 2.0 if not hand else 0.4

        if action.action_type == ActionType.PLACE_SOIL:
            soil_id = state.soil_pile[0]
            soil = state.available_soils[soil_id]
            sun_cost = soil.cost.values.get(ResourceType.SUN, 0)
            if state.players[owner].resources.get(ResourceType.SUN, 0) < sun_cost:
                return -50  # topo caro demais: compra seria uma ação perdida
            production_value = sum(
                _PRODUCTION_WEIGHT.get(r, 0.0) * amount for r, amount in soil.production.items()
            )
            cost = sum(soil.cost.values.values())
            return production_value - 0.15 * cost

        if action.action_type == ActionType.PLAY_FAUNA:
            fauna = state.available_fauna[action.fauna_id]
            points = score_fauna(state, action.fauna_id, action.position, owner)
            cost = sum(fauna.cost.values.values())
            return points - 0.15 * cost

        if action.action_type == ActionType.PLAY_PARASITE:
            fauna = state.available_fauna[action.fauna_id]
            points = score_fauna(state, action.fauna_id, action.position, owner)
            cost = sum(fauna.cost.values.values())
            return points - 0.15 * cost

        if action.action_type == ActionType.MOVE_SMALL_FISH:
            # Bônus grátis; o greedy míope não modela reposicionamento -> neutro.
            return 0.0

        if action.action_type == ActionType.MOVE_FAUNA:
            # Só vale mover para um tile inédito e enquanto abaixo do teto de pontuação.
            visited = state.players[owner].moon_jelly_visited
            cap = state.available_fauna[action.fauna_id].visited_score_cap
            fresh = action.to_position not in visited
            below_cap = cap <= 0 or len(visited) < cap
            return 1.0 if (fresh and below_cap) else -0.2

        if action.action_type == ActionType.PLACE_STAGHORN_PAIR:
            coral = state.available_corals[STAGHORN_ID]
            points = 0
            cost = STAGHORN_PAIR_PLANKTON_SURCHARGE
            for position in (action.first_position, action.second_position):
                points += score_coral(state, _mock_placed(STAGHORN_ID, position, owner))
                cost += sum(effective_cost(state, coral, position).values())
            return points - 0.15 * cost

        coral = state.available_corals[action.coral_id]
        immediate_points = score_coral(state, _mock_placed(action.coral_id, action.position, owner))
        normalized_cost = sum(effective_cost(state, coral, action.position).values())
        return immediate_points - 0.15 * normalized_cost
