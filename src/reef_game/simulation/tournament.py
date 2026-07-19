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
from ..content.loader import load_corals, load_flora, load_soils, load_yaml_config
from ..engine.enums import PlayerId
from ..engine.setup import create_initial_state, load_balance_rules, load_climate_config
from .runner import run_game


@dataclass
class TournamentConfig:
    games: int = 100
    corals_path: str = "configs/corals.yaml"
    soils_path: str = "configs/soils.yaml"
    flora_path: str = "configs/flora.yaml"
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
    # Estado turno a turno: CSV longo (metricas por jogador) + JSONL detalhado (board + mao).
    save_turn_states: bool = True
    save_turn_states_detail: bool = True


AGENT_FACTORY = {
    "random": lambda seed: RandomAgent(seed=seed),
    "greedy": lambda seed: GreedyAgent(),
}


def run_tournament(config: TournamentConfig) -> pd.DataFrame:
    corals = load_corals(config.corals_path)
    soils = load_soils(config.soils_path)
    flora = load_flora(config.flora_path)
    balance_rules = load_balance_rules(config.balance_rules_path)
    climate_config = load_climate_config(config.climate_path)
    version_config = load_yaml_config(config.version_path)

    coral_ids = sorted(corals.keys())
    soil_ids = sorted(soils.keys())

    rows = []
    turn_state_rows = []
    turn_state_snapshots = []
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
            soil_definitions=soils,
            flora_definitions=flora,
        )
        agents = {
            PlayerId.P1: AGENT_FACTORY[config.agent_p1](seed),
            PlayerId.P2: AGENT_FACTORY[config.agent_p2](seed + 1),
        }
        final_state, summary, telemetry = run_game(
            state, agents=agents, max_rounds=config.max_rounds
        )

        if config.save_turn_states:
            turn_state_rows.extend(telemetry.to_rows())
        if config.save_turn_states_detail:
            turn_state_snapshots.extend(telemetry.states)

        row = {
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
                "p1_produced_sun": summary["produced_resources"][1]["sun"],
                "p2_produced_sun": summary["produced_resources"][2]["sun"],
                "p1_produced_plankton": summary["produced_resources"][1]["plankton"],
                "p2_produced_plankton": summary["produced_resources"][2]["plankton"],
                "p1_soils": summary["soils_on_board"][1],
                "p2_soils": summary["soils_on_board"][2],
                "p1_lost_soil_buys": summary["soil_purchases_lost"][1],
                "p2_lost_soil_buys": summary["soil_purchases_lost"][2],
                "p1_hand": summary["hand_size"][1],
                "p2_hand": summary["hand_size"][2],
                "soil_pile_remaining": summary["soil_pile_remaining"],
                "flora_deck_remaining": summary["flora_deck_remaining"],
                "terminal": final_state.is_terminal,
        }
        # Volume por tipo de coral e de solo, por jogador (para análise volume x score).
        for pid in (1, 2):
            corals_by_type = summary["corals_by_type"][pid]
            for coral_id in coral_ids:
                row[f"p{pid}_coral_{coral_id}"] = corals_by_type.get(coral_id, 0)
            soils_by_type = summary["soils_by_type"][pid]
            for soil_id in soil_ids:
                row[f"p{pid}_soil_{soil_id}"] = soils_by_type.get(soil_id, 0)
        rows.append(row)

    df = pd.DataFrame(rows)

    if config.save_results:
        artifact_dir = save_tournament_results(
            df=df,
            config=config,
            version_config=version_config,
            turn_state_rows=turn_state_rows,
            turn_state_snapshots=turn_state_snapshots,
        )
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
        "avg_soils_per_player": float((df["p1_soils"] + df["p2_soils"]).mean() / 2),
        "avg_soil_lost_per_player": float(
            (df["p1_lost_soil_buys"] + df["p2_lost_soil_buys"]).mean() / 2
        ),
        "avg_produced_sun_per_player": float(
            (df["p1_produced_sun"] + df["p2_produced_sun"]).mean() / 2
        ),
        "avg_hand_per_player": float((df["p1_hand"] + df["p2_hand"]).mean() / 2),
        "avg_flora_deck_remaining": float(df["flora_deck_remaining"].mean()),
    }


def save_tournament_results(
    df: pd.DataFrame,
    config: TournamentConfig,
    version_config: dict,
    turn_state_rows: list | None = None,
    turn_state_snapshots: list | None = None,
) -> Path:
    version_block = version_config.get("version", {})
    code_version = version_block.get("code_version", "unknown")
    timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    artifact_dir = Path(config.output_dir) / f"{timestamp}_v{code_version}"
    artifact_dir.mkdir(parents=True, exist_ok=True)

    results_path = artifact_dir / "results.csv"
    metadata_path = artifact_dir / "metadata.json"

    df.to_csv(results_path, index=False)

    files = {"results_csv": str(results_path)}

    # Estado turno a turno (long format) para analisar a progressao por jogador.
    if config.save_turn_states and turn_state_rows:
        turn_states_path = artifact_dir / "turn_states.csv"
        pd.DataFrame(turn_state_rows).to_csv(turn_states_path, index=False)
        files["turn_states_csv"] = str(turn_states_path)

    # Snapshot completo por turno (inclui board e mao de cada jogador), 1 JSON por linha.
    if config.save_turn_states_detail and turn_state_snapshots:
        detail_path = artifact_dir / "turn_states.jsonl"
        with detail_path.open("w", encoding="utf-8") as handle:
            for snapshot in turn_state_snapshots:
                handle.write(_json_dumps_compact(snapshot))
                handle.write("\n")
        files["turn_states_jsonl"] = str(detail_path)

    summary = summarize_tournament(df)
    metadata = {
        "saved_at_utc": timestamp,
        "version": version_block,
        "tournament_config": asdict(config),
        "summary": summary,
        "files": files,
    }
    metadata_path.write_text(_json_dumps(metadata), encoding="utf-8")

    return artifact_dir


def _json_dumps(payload: dict) -> str:
    import json

    return json.dumps(payload, ensure_ascii=False, indent=2)


def _json_dumps_compact(payload: dict) -> str:
    import json

    return json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
