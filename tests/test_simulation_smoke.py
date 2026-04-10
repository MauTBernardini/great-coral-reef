from reef_game.agents.greedy_agent import GreedyAgent
from reef_game.agents.random_agent import RandomAgent
from reef_game.engine.enums import PlayerId
from reef_game.simulation.runner import run_game


def test_random_vs_greedy_completes(initial_state):
    agents = {PlayerId.P1: RandomAgent(seed=1), PlayerId.P2: GreedyAgent()}
    final_state, summary, telemetry = run_game(initial_state, agents=agents, max_rounds=20)

    assert final_state.is_terminal
    assert summary["turns"] >= 1
    assert len(telemetry.states) >= 2
