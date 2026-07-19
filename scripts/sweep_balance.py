from copy import deepcopy
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

import pandas as pd

from reef_game.simulation.tournament import TournamentConfig, run_tournament, summarize_tournament


def main():
    rows = []
    for sun_boost in [0, 1, 2]:
        config = TournamentConfig(
            games=20,
            corals_path=str(ROOT / "configs" / "corals.yaml"),
            soils_path=str(ROOT / "configs" / "soils.yaml"),
            balance_rules_path=str(ROOT / "configs" / "balance_rules.yaml"),
            climate_path=str(ROOT / "configs" / "climate.yaml"),
            agent_p1="random",
            agent_p2="greedy",
            seed_start=1000 + sun_boost * 100,
        )
        summary = summarize_tournament(run_tournament(config))
        summary["sun_boost_placeholder"] = sun_boost
        rows.append(summary)

    print(pd.DataFrame(rows).to_string(index=False))


if __name__ == "__main__":
    main()
