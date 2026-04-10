from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd

try:
    from tqdm.auto import tqdm
except ImportError:
    def tqdm(iterable, **kwargs):
        return iterable

from ..agents.greedy_agent import GreedyAgent
from ..agents.random_agent import RandomAgent
from ..content.loader import load_corals, load_yaml_config
from ..engine.enums import PlayerId
from ..engine.setup import create_initial_state, load_balance_rules, load_climate_config
from .runner import run_game


@dataclass
class TournamentConfig:
    games: int = 100
    corals_path: str = "configs/corals.yaml"
    balance_rules_path: str = "configs/balance_rules.yaml"
    climate_path: str = "configs/climate.yaml"
    version_path: str = "configs/version.yaml"
    output_dir: str = "artifacts/tournaments"
    agent_p1: str = "random"
    agent_p2: str = "greedy"
    seed_start: int = 1000
    max_rounds: int = 50
    show_progress: bool = True
    save_results: bool = True


AGENT_FACTORY = {
    "random": lambda seed: RandomAgent(seed=seed),
    "greedy": lambda seed: GreedyAgent(),
}


def run_tournament(config: TournamentConfig) -> pd.DataFrame:
    corals = load_corals(config.corals_path)
    balance_rules = load_balance_rules(config.balance_rules_path)
    climate_config = load_climate_config(config.climate_path)
    version_config = load_yaml_config(config.version_path)

    rows = []
    for i in tqdm(
        range(config.games),
        total=config.games,
        desc="Tournament",
        disable=not config.show_progress,
    ):
        seed = config.seed_start + i
        state = create_initial_state(
            seed=seed,
            coral_definitions=corals,
            balance_rules=balance_rules,
            climate_config=climate_config,
        )
        agents = {
            PlayerId.P1: AGENT_FACTORY[config.agent_p1](seed),
            PlayerId.P2: AGENT_FACTORY[config.agent_p2](seed + 1),
        }
        final_state, summary, _ = run_game(state, agents=agents, max_rounds=config.max_rounds)
        rows.append(
            {
                "seed": seed,
                "winner": summary["winner"],
                "turns": summary["turns"],
                "rounds": summary["rounds"],
                "temperature": summary["temperature"],
                "ph": summary["ph"],
                "current_era": summary["current_era"],
                "consumed_climate_cards": summary["consumed_climate_cards"],
                "remaining_climate_cards": summary["remaining_climate_cards"],
                "board_occupancy": summary["board_occupancy"],
                "p1_score": summary["scores"][1],
                "p2_score": summary["scores"][2],
                "p1_efficiency": summary["efficiency_player_1"],
                "p2_efficiency": summary["efficiency_player_2"],
                "p1_dead_turns": summary["dead_turns"][1],
                "p2_dead_turns": summary["dead_turns"][2],
                "terminal": final_state.is_terminal,
            }
        )

    df = pd.DataFrame(rows)

    if config.save_results:
        artifact_dir = save_tournament_results(df=df, config=config, version_config=version_config)
        df.attrs["artifact_dir"] = str(artifact_dir)
        df.attrs["code_version"] = version_config.get("version", {}).get("code_version")

    return df


def summarize_tournament(df: pd.DataFrame) -> dict:
    return {
        "games": len(df),
        "p1_winrate": float((df["winner"] == 1).mean()),
        "p2_winrate": float((df["winner"] == 2).mean()),
        "draw_rate": float(df["winner"].isna().mean()),
        "avg_turns": float(df["turns"].mean()),
        "avg_rounds": float(df["rounds"].mean()),
        "avg_temperature": float(df["temperature"].mean()),
        "avg_ph": float(df["ph"].mean()),
        "avg_current_era": float(df["current_era"].mean()),
        "avg_p1_score": float(df["p1_score"].mean()),
        "avg_p2_score": float(df["p2_score"].mean()),
        "avg_board_occupancy": float(df["board_occupancy"].mean()),
    }


def save_tournament_results(df: pd.DataFrame, config: TournamentConfig, version_config: dict) -> Path:
    version_block = version_config.get("version", {})
    code_version = version_block.get("code_version", "unknown")
    timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    artifact_dir = Path(config.output_dir) / f"{timestamp}_v{code_version}"
    artifact_dir.mkdir(parents=True, exist_ok=True)

    results_path = artifact_dir / "results.csv"
    metadata_path = artifact_dir / "metadata.json"

    df.to_csv(results_path, index=False)

    summary = summarize_tournament(df)
    metadata = {
        "saved_at_utc": timestamp,
        "version": version_block,
        "tournament_config": asdict(config),
        "summary": summary,
        "files": {
            "results_csv": str(results_path),
        },
    }
    metadata_path.write_text(_json_dumps(metadata), encoding="utf-8")

    return artifact_dir


def _json_dumps(payload: dict) -> str:
    import json

    return json.dumps(payload, ensure_ascii=False, indent=2)
