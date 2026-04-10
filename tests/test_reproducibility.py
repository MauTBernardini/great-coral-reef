from reef_game.agents.random_agent import RandomAgent
from reef_game.engine.enums import PlayerId
from reef_game.simulation.runner import run_game


def test_same_seed_and_agents_produce_same_summary(initial_state):
    agents_a = {PlayerId.P1: RandomAgent(seed=7), PlayerId.P2: RandomAgent(seed=8)}
    agents_b = {PlayerId.P1: RandomAgent(seed=7), PlayerId.P2: RandomAgent(seed=8)}

    _, summary_a, _ = run_game(initial_state, agents=agents_a, max_rounds=20)

    from reef_game.content.loader import load_corals
    from reef_game.engine.setup import create_initial_state, load_balance_rules, load_climate_config
    from pathlib import Path

    root = Path(__file__).resolve().parents[1]
    coral_defs = load_corals(root / "configs" / "corals.yaml")
    balance_rules = load_balance_rules(root / "configs" / "balance_rules.yaml")
    climate_config = load_climate_config(root / "configs" / "climate.yaml")
    fresh_state = create_initial_state(
        seed=42,
        coral_definitions=coral_defs,
        balance_rules=balance_rules,
        climate_config=climate_config,
    )
    _, summary_b, _ = run_game(fresh_state, agents=agents_b, max_rounds=20)

    assert summary_a == summary_b
