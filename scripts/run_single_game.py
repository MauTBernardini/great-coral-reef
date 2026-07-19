from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from reef_game.agents.greedy_agent import GreedyAgent
from reef_game.agents.random_agent import RandomAgent
from reef_game.content.loader import load_corals, load_fauna, load_soils
from reef_game.engine.enums import PlayerId
from reef_game.engine.setup import create_initial_state, load_balance_rules, load_climate_config
from reef_game.simulation.runner import run_game
from reef_game.utils.serialization import dumps


def main():
    corals = load_corals(ROOT / "configs" / "corals.yaml")
    soils = load_soils(ROOT / "configs" / "soils.yaml")
    fauna = load_fauna(ROOT / "configs" / "fauna.yaml")
    balance_rules = load_balance_rules(ROOT / "configs" / "balance_rules.yaml")
    climate_config = load_climate_config(ROOT / "configs" / "climate.yaml")
    state = create_initial_state(
        seed=42,
        coral_definitions=corals,
        balance_rules=balance_rules,
        climate_config=climate_config,
        soil_definitions=soils,
        fauna_definitions=fauna,
    )

    agents = {
        PlayerId.P1: RandomAgent(seed=42),
        PlayerId.P2: GreedyAgent(),
    }

    final_state, summary, _ = run_game(state, agents=agents, max_rounds=50)
    print(dumps(summary))
    print(f"Winner: {final_state.winner}")


if __name__ == "__main__":
    main()
