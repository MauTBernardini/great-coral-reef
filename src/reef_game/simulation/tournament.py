import random
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
from ..agents.long_term_agent import LongTermAgent
from ..agents.random_agent import RandomAgent
from ..content.loader import load_corals, load_fauna, load_soils, load_yaml_config
from ..engine.enums import PlayerId
from ..engine.setup import create_initial_state, load_balance_rules, load_climate_config
from .runner import run_game


@dataclass
class TournamentConfig:
    games: int = 100
    corals_path: str = "configs/corals.yaml"
    soils_path: str = "configs/soils.yaml"
    fauna_path: str = "configs/fauna.yaml"
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
    # Aleatoriza (por seed) qual agente ocupa a cadeira P1/P2, para comparar por AGENTE
    # em vez de por ordem de turno. As colunas p1_agent/p2_agent registram a atribuição real.
    randomize_seats: bool = False


AGENT_FACTORY = {
    "random": lambda seed: RandomAgent(seed=seed),
    "greedy": lambda seed: GreedyAgent(),
    "longterm": lambda seed: LongTermAgent(),
}


def run_tournament(config: TournamentConfig) -> pd.DataFrame:
    corals = load_corals(config.corals_path)
    soils = load_soils(config.soils_path)
    fauna = load_fauna(config.fauna_path)
    balance_rules = load_balance_rules(config.balance_rules_path)
    climate_config = load_climate_config(config.climate_path)
    version_config = load_yaml_config(config.version_path)

    coral_ids = sorted(corals.keys())
    soil_ids = sorted(soils.keys())
    fauna_ids = sorted(fauna.keys())
    seat_rng = random.Random(config.seed_start) if config.randomize_seats else None

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
            fauna_definitions=fauna,
        )
        # Atribuição de agente a cada cadeira (opcionalmente trocada por seed).
        p1_agent, p2_agent = config.agent_p1, config.agent_p2
        if seat_rng is not None and seat_rng.random() < 0.5:
            p1_agent, p2_agent = p2_agent, p1_agent

        agents = {
            PlayerId.P1: AGENT_FACTORY[p1_agent](seed),
            PlayerId.P2: AGENT_FACTORY[p2_agent](seed + 1),
        }
        final_state, summary, telemetry = run_game(
            state, agents=agents, max_rounds=config.max_rounds
        )

        if config.save_turn_states:
            for turn_row in telemetry.to_rows():
                turn_row["p1_agent"] = p1_agent
                turn_row["p2_agent"] = p2_agent
                turn_row["agent"] = p1_agent if turn_row["player"] == 1 else p2_agent
                turn_state_rows.append(turn_row)
        if config.save_turn_states_detail:
            turn_state_snapshots.extend(telemetry.states)

        row = {
                "seed": seed,
                "p1_agent": p1_agent,
                "p2_agent": p2_agent,
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
                "coral_deck_remaining": summary["coral_deck_remaining"],
                "terminal": final_state.is_terminal,
        }
        # Volume por tipo de coral, solo e fauna, por jogador (para análise volume x score).
        for pid in (1, 2):
            corals_by_type = summary["corals_by_type"][pid]
            for coral_id in coral_ids:
                row[f"p{pid}_coral_{coral_id}"] = corals_by_type.get(coral_id, 0)
            soils_by_type = summary["soils_by_type"][pid]
            for soil_id in soil_ids:
                row[f"p{pid}_soil_{soil_id}"] = soils_by_type.get(soil_id, 0)
            fauna_by_type = summary["fauna_by_type"][pid]
            for fauna_id in fauna_ids:
                row[f"p{pid}_fauna_{fauna_id}"] = fauna_by_type.get(fauna_id, 0)
            row[f"p{pid}_fauna_total"] = sum(fauna_by_type.values())
            row[f"p{pid}_habitat"] = summary["habitat_capacity"][pid]
            row[f"p{pid}_produced_o2"] = summary["produced_resources"][pid].get("o2", 0)
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


def _play_scored_game(content, seed, p1_name, p2_name, max_rounds):
    corals, soils, fauna, balance_rules, climate_config = content
    state = create_initial_state(
        seed=seed,
        coral_definitions=corals,
        balance_rules=balance_rules,
        climate_config=climate_config,
        soil_definitions=soils,
        fauna_definitions=fauna,
    )
    agents = {
        PlayerId.P1: AGENT_FACTORY[p1_name](seed),
        PlayerId.P2: AGENT_FACTORY[p2_name](seed + 1),
    }
    _, summary, _ = run_game(state, agents=agents, max_rounds=max_rounds)
    return summary["scores"][1], summary["scores"][2], summary["winner"]


def run_paired_tournament(config: TournamentConfig) -> pd.DataFrame:
    """Compara agent_p1 (A) vs agent_p2 (B) de forma justa: cada seed é jogado nas
    DUAS ordens, cancelando a vantagem de posição."""
    content = (
        load_corals(config.corals_path),
        load_soils(config.soils_path),
        load_fauna(config.fauna_path),
        load_balance_rules(config.balance_rules_path),
        load_climate_config(config.climate_path),
    )
    version_config = load_yaml_config(config.version_path)
    agent_a, agent_b = config.agent_p1, config.agent_p2

    def winner_agent(winner, p1_is_a):
        if winner is None:
            return "draw"
        p1_won = winner == 1
        if p1_won:
            return "a" if p1_is_a else "b"
        return "b" if p1_is_a else "a"

    rows = []
    for i in tqdm(
        range(config.games), total=config.games, desc="Paired", disable=not config.show_progress
    ):
        seed = config.seed_start + i
        a1, b1, w1 = _play_scored_game(content, seed, agent_a, agent_b, config.max_rounds)
        b2, a2, w2 = _play_scored_game(content, seed, agent_b, agent_a, config.max_rounds)
        rows.append(
            {
                "seed": seed,
                "a_as_p1_score": a1,
                "b_as_p2_score": b1,
                "game1_winner": winner_agent(w1, p1_is_a=True),
                "b_as_p1_score": b2,
                "a_as_p2_score": a2,
                "game2_winner": winner_agent(w2, p1_is_a=False),
                "a_total_score": a1 + a2,
                "b_total_score": b1 + b2,
            }
        )

    df = pd.DataFrame(rows)
    df.attrs["agent_a"] = agent_a
    df.attrs["agent_b"] = agent_b

    if config.save_results:
        artifact_dir = _save_paired_results(df, config, version_config)
        df.attrs["artifact_dir"] = str(artifact_dir)

    return df


def summarize_paired(
    df: pd.DataFrame, agent_a: str | None = None, agent_b: str | None = None
) -> dict:
    agent_a = agent_a or df.attrs.get("agent_a", "A")
    agent_b = agent_b or df.attrs.get("agent_b", "B")
    total_games = 2 * len(df)

    winners = list(df["game1_winner"]) + list(df["game2_winner"])
    a_scores = list(df["a_as_p1_score"]) + list(df["a_as_p2_score"])
    b_scores = list(df["b_as_p1_score"]) + list(df["b_as_p2_score"])
    # P1 venceu quando: jogo1 -> A ('a'); jogo2 -> B ('b').
    p1_wins = int((df["game1_winner"] == "a").sum() + (df["game2_winner"] == "b").sum())

    return {
        "agent_a": agent_a,
        "agent_b": agent_b,
        "paired_games": total_games,
        "a_winrate": winners.count("a") / total_games,
        "b_winrate": winners.count("b") / total_games,
        "draw_rate": winners.count("draw") / total_games,
        "a_avg_score": sum(a_scores) / total_games,
        "b_avg_score": sum(b_scores) / total_games,
        "seeds_a_better": float((df["a_total_score"] > df["b_total_score"]).mean()),
        "seeds_b_better": float((df["b_total_score"] > df["a_total_score"]).mean()),
        # Efeito de posição residual (deve continuar alto, mas agora simétrico entre A e B):
        "residual_first_player_winrate": p1_wins / total_games,
    }


def _save_paired_results(df: pd.DataFrame, config: TournamentConfig, version_config: dict) -> Path:
    version_block = version_config.get("version", {})
    code_version = version_block.get("code_version", "unknown")
    timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    artifact_dir = Path(config.output_dir) / f"paired_{timestamp}_v{code_version}"
    artifact_dir.mkdir(parents=True, exist_ok=True)

    results_path = artifact_dir / "paired_results.csv"
    df.to_csv(results_path, index=False)

    metadata = {
        "saved_at_utc": timestamp,
        "version": version_block,
        "mode": "paired",
        "tournament_config": asdict(config),
        "summary": summarize_paired(df),
        "files": {"paired_results_csv": str(results_path)},
    }
    (artifact_dir / "metadata.json").write_text(_json_dumps(metadata), encoding="utf-8")
    return artifact_dir


def summarize_by_agent(df: pd.DataFrame) -> dict:
    """Compara por AGENTE (não por cadeira): agrega o desempenho de cada agente
    somando as partidas em que ele foi P1 e as em que foi P2.

    Só é uma comparação *justa* quando as cadeiras foram aleatorizadas
    (``randomize_seats``); em cadeiras fixas, cada agente aparece em uma só cadeira e
    isto reduz às métricas por posição.
    """
    agent_names = sorted(set(df["p1_agent"]) | set(df["p2_agent"]))
    result = {}
    for agent in agent_names:
        as_p1 = df[df["p1_agent"] == agent]
        as_p2 = df[df["p2_agent"] == agent]
        games = len(as_p1) + len(as_p2)
        if games == 0:
            continue
        score_sum = float(as_p1["p1_score"].sum() + as_p2["p2_score"].sum())
        wins = int((as_p1["winner"] == 1).sum() + (as_p2["winner"] == 2).sum())
        result[agent] = {
            "games": games,
            "games_as_p1": len(as_p1),
            "games_as_p2": len(as_p2),
            "avg_score": score_sum / games,
            "winrate": wins / games,
        }
    return result


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
        "avg_coral_deck_remaining": float(df["coral_deck_remaining"].mean()),
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
