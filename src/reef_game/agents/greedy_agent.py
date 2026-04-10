from ..engine.enums import ActionType
from ..engine.scoring import score_incremental_after_placement
from .base import BaseAgent


class GreedyAgent(BaseAgent):
    def choose_action(self, state, legal_actions):
        best = None
        best_value = float("-inf")

        for action in legal_actions:
            if action.action_type == ActionType.PASS:
                value = -9999
            else:
                coral = state.available_corals[action.coral_id]
                mock_placed = type("Placed", (), {
                    "coral_id": action.coral_id,
                    "position": action.position,
                    "owner": state.active_player,
                })()
                immediate_points = score_incremental_after_placement(state, mock_placed)
                normalized_cost = sum(coral.cost.values.values())
                value = immediate_points - 0.15 * normalized_cost

            if value > best_value:
                best = action
                best_value = value

        return best
