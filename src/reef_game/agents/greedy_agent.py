from ..engine.economy import effective_cost
from ..engine.enums import ActionType, ResourceType
from ..engine.scoring import score_coral
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

        if action.action_type == ActionType.PLACE_SOIL:
            soil = state.available_soils[action.soil_id]
            production_value = sum(
                _PRODUCTION_WEIGHT.get(r, 0.0) * amount for r, amount in soil.production.items()
            )
            cost = sum(soil.cost.values.values())
            return production_value - 0.15 * cost

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
