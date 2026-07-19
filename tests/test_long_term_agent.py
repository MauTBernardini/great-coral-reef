from reef_game.agents.greedy_agent import GreedyAgent
from reef_game.agents.long_term_agent import LongTermAgent
from reef_game.engine.enums import PlayerId
from reef_game.simulation.runner import enumerate_legal_actions, run_game


def test_choose_action_returns_a_legal_action(initial_state):
    agent = LongTermAgent()
    legal = enumerate_legal_actions(initial_state)
    action = agent.choose_action(initial_state, legal)
    assert action in legal


def test_long_term_vs_greedy_game_completes(initial_state):
    agents = {PlayerId.P1: LongTermAgent(), PlayerId.P2: GreedyAgent()}
    final_state, summary, telemetry = run_game(initial_state, agents=agents, max_rounds=20)
    assert final_state.is_terminal
    assert len(telemetry.states) >= 2
