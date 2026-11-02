from __future__ import annotations

import argparse
import json
import sys
from copy import deepcopy
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd
from tqdm.auto import tqdm

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from reef_game.content.loader import (  # noqa: E402
    load_corals,
    load_fauna,
    load_instincts,
    load_soils,
    load_upgrades,
)
from reef_game.engine.enums import PlayerId, ResourceType  # noqa: E402
from reef_game.engine.setup import (  # noqa: E402
    create_initial_state,
    load_balance_rules,
    load_climate_config,
)
from reef_game.simulation.runner import run_game  # noqa: E402
from reef_game.simulation.tournament import AGENT_FACTORY  # noqa: E402

BASE_LINEUP = ("greedy", "longterm", "greedy", "longterm")
SOIL_PROPORTIONS = {
    "sandy_bed": 0.40,
    "rocky_reef": 0.25,
    "dark_overhang": 0.25,
    "seagrass_meadow": 0.10,
}


def _scaled_soils(soils: dict, total_supply: int) -> dict:
    quantities = {
        soil_id: round(total_supply * proportion)
        for soil_id, proportion in SOIL_PROPORTIONS.items()
    }
    difference = total_supply - sum(quantities.values())
    quantities["sandy_bed"] += difference
    return {
        soil_id: replace(soil, supply=quantities[soil_id])
        for soil_id, soil in soils.items()
    }


def _rotated_lineup(rotation: int) -> tuple[str, ...]:
    offset = rotation % len(BASE_LINEUP)
    return BASE_LINEUP[offset:] + BASE_LINEUP[:offset]


def _scenario_rules(base_rules: dict, rotate: bool, critical_temperature: float) -> dict:
    rules = deepcopy(base_rules)
    rules["players"]["rotate_start_player"] = rotate
    rules["climate"]["critical_temperature"] = critical_temperature
    return rules


def _play_scenario(
    scenario: dict,
    seeds: int,
    rotations: int,
    seed_start: int,
    content: dict,
) -> list[dict]:
    rows = []
    total = seeds * rotations
    progress = tqdm(total=total, desc=scenario["label"], unit="game")
    soils = _scaled_soils(content["soils"], scenario["soil_supply"])
    rules = _scenario_rules(
        content["rules"],
        rotate=scenario["rotate_start"],
        critical_temperature=scenario["critical_temperature"],
    )

    for seed_offset in range(seeds):
        seed = seed_start + seed_offset
        for rotation in range(rotations):
            lineup = _rotated_lineup(rotation)
            state = create_initial_state(
                seed=seed,
                coral_definitions=content["corals"],
                balance_rules=rules,
                climate_config=content["climate"],
                soil_definitions=soils,
                fauna_definitions=content["fauna"],
                instinct_definitions=content["instincts"],
                upgrade_definitions=content["upgrades"],
            )
            agents = {
                player_id: AGENT_FACTORY[agent_name](seed + player_id.value - 1)
                for player_id, agent_name in zip(PlayerId, lineup, strict=True)
            }
            final_state, summary, _ = run_game(
                state,
                agents=agents,
                max_rounds=50,
                record_telemetry=False,
                compact_spatial_actions=True,
            )
            winner = summary["winner"]
            row = {
                "scenario": scenario["id"],
                "scenario_label": scenario["label"],
                "seed": seed,
                "rotation": rotation,
                "rotate_start": scenario["rotate_start"],
                "soil_supply": scenario["soil_supply"],
                "critical_temperature": scenario["critical_temperature"],
                "winner": winner,
                "winner_agent": lineup[winner - 1] if winner else "draw",
                "turns": summary["turns"],
                "rounds": summary["rounds"],
                "temperature": summary["temperature"],
                "ph": summary["ph"],
                "board_occupancy": summary["board_occupancy"],
                "soil_remaining": summary["soil_pile_remaining"],
                "deck_remaining": summary["coral_deck_remaining"],
            }
            for player_id, agent_name in zip(PlayerId, lineup, strict=True):
                pid = player_id.value
                row[f"p{pid}_agent"] = agent_name
                row[f"p{pid}_score"] = summary["scores"][pid]
                row[f"p{pid}_soils"] = summary["soils_on_board"][pid]
                row[f"p{pid}_hand"] = summary["hand_size"][pid]
                row[f"p{pid}_sun_produced"] = summary["produced_resources"][pid]["sun"]
                row[f"p{pid}_plankton_produced"] = summary["produced_resources"][pid][
                    "plankton"
                ]
                row[f"p{pid}_o2_produced"] = summary["produced_resources"][pid]["o2"]
                row[f"p{pid}_sun_spent"] = summary["spent_resources"][pid]["sun"]
                row[f"p{pid}_plankton_spent"] = summary["spent_resources"][pid][
                    "plankton"
                ]
                row[f"p{pid}_o2_spent"] = summary["spent_resources"][pid]["o2"]
                player = final_state.players[player_id]
                row[f"p{pid}_sun_remaining"] = player.resources.get(
                    ResourceType.SUN, 0
                )
                row[f"p{pid}_plankton_remaining"] = player.resources.get(
                    ResourceType.PLANKTON, 0
                )
                row[f"p{pid}_o2_remaining"] = player.resources.get(
                    ResourceType.O2, 0
                )
                row[f"p{pid}_fauna"] = sum(summary["fauna_by_type"][pid].values())
                row[f"p{pid}_habitat"] = summary["habitat_capacity"][pid]
            rows.append(row)
            progress.update(1)
    progress.close()
    return rows


def _player_rows(results: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for _, game in results.iterrows():
        for pid in range(1, 5):
            rows.append(
                {
                    "scenario": game["scenario"],
                    "seat": pid,
                    "agent": game[f"p{pid}_agent"],
                    "won": int(game["winner"] == pid),
                    "score": game[f"p{pid}_score"],
                    "soils": game[f"p{pid}_soils"],
                    "sun_produced": game[f"p{pid}_sun_produced"],
                    "plankton_produced": game[f"p{pid}_plankton_produced"],
                    "o2_produced": game[f"p{pid}_o2_produced"],
                    "sun_spent": game[f"p{pid}_sun_spent"],
                    "plankton_spent": game[f"p{pid}_plankton_spent"],
                    "o2_spent": game[f"p{pid}_o2_spent"],
                    "sun_remaining": game[f"p{pid}_sun_remaining"],
                    "plankton_remaining": game[f"p{pid}_plankton_remaining"],
                    "o2_remaining": game[f"p{pid}_o2_remaining"],
                    "fauna": game[f"p{pid}_fauna"],
                    "habitat": game[f"p{pid}_habitat"],
                }
            )
    return pd.DataFrame(rows)


def _summaries(results: pd.DataFrame) -> pd.DataFrame:
    players = _player_rows(results)
    rows = []
    for scenario_id, games in results.groupby("scenario", sort=False):
        scenario_players = players[players["scenario"] == scenario_id]
        seat_rates = scenario_players.groupby("seat")["won"].mean()
        agent_rates = games["winner_agent"].value_counts(normalize=True)
        supply = int(games["soil_supply"].iloc[0])
        rows.append(
            {
                "scenario": scenario_id,
                "label": games["scenario_label"].iloc[0],
                "games": len(games),
                "soil_supply": supply,
                "critical_temperature": games["critical_temperature"].iloc[0],
                "avg_turns": games["turns"].mean(),
                "avg_rounds": games["rounds"].mean(),
                "avg_occupancy": games["board_occupancy"].mean(),
                "avg_soil_remaining": games["soil_remaining"].mean(),
                "soil_remaining_rate": games["soil_remaining"].mean() / supply,
                "avg_deck_remaining": games["deck_remaining"].mean(),
                "seat_win_spread": seat_rates.max() - seat_rates.min(),
                **{f"p{pid}_winrate": seat_rates.get(pid, 0.0) for pid in range(1, 5)},
                "greedy_winrate": agent_rates.get("greedy", 0.0),
                "longterm_winrate": agent_rates.get("longterm", 0.0),
                "draw_rate": agent_rates.get("draw", 0.0),
                "greedy_avg_score": scenario_players.loc[
                    scenario_players["agent"] == "greedy", "score"
                ].mean(),
                "longterm_avg_score": scenario_players.loc[
                    scenario_players["agent"] == "longterm", "score"
                ].mean(),
            }
        )
    return pd.DataFrame(rows)


def _choose_supply(summary: pd.DataFrame) -> int:
    candidates = summary[summary["scenario"].isin(["soil_40", "soil_60", "soil_80"])].copy()
    candidates["selection_score"] = (
        (candidates["avg_occupancy"] - 0.15).abs()
        + 0.25 * (candidates["soil_remaining_rate"] - 0.15).abs()
        + 0.25 * candidates["seat_win_spread"]
    )
    return int(candidates.sort_values("selection_score").iloc[0]["soil_supply"])


def main() -> None:
    parser = argparse.ArgumentParser(description="Run ordered four-player balance experiments.")
    parser.add_argument(
        "--seeds",
        type=int,
        default=10,
        help="Independent seeds per scenario (multiplied by --rotations).",
    )
    parser.add_argument("--rotations", type=int, default=2, choices=(2, 4))
    parser.add_argument("--seed-start", type=int, default=5000)
    args = parser.parse_args()

    content = {
        "corals": load_corals(ROOT / "configs" / "corals.yaml"),
        "soils": load_soils(ROOT / "configs" / "soils.yaml"),
        "fauna": load_fauna(ROOT / "configs" / "fauna.yaml"),
        "instincts": load_instincts(ROOT / "configs" / "instincts.yaml"),
        "upgrades": load_upgrades(ROOT / "configs" / "upgrades.yaml"),
        "rules": load_balance_rules(ROOT / "configs" / "balance_rules.yaml"),
        "climate": load_climate_config(ROOT / "configs" / "climate.yaml"),
    }
    scenarios = [
        {
            "id": "baseline",
            "label": "1. Baseline",
            "rotate_start": False,
            "soil_supply": 20,
            "critical_temperature": 32.0,
        },
        {
            "id": "rotation",
            "label": "2. Rotação do inicial",
            "rotate_start": True,
            "soil_supply": 20,
            "critical_temperature": 32.0,
        },
        {
            "id": "soil_40",
            "label": "3. Rotação + 40 solos",
            "rotate_start": True,
            "soil_supply": 40,
            "critical_temperature": 32.0,
        },
        {
            "id": "soil_60",
            "label": "4. Rotação + 60 solos",
            "rotate_start": True,
            "soil_supply": 60,
            "critical_temperature": 32.0,
        },
        {
            "id": "soil_80",
            "label": "5. Rotação + 80 solos",
            "rotate_start": True,
            "soil_supply": 80,
            "critical_temperature": 32.0,
        },
    ]

    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    output = ROOT / "artifacts" / "experiments" / f"balance_{stamp}"
    output.mkdir(parents=True, exist_ok=False)
    all_rows = []
    for scenario in scenarios:
        all_rows.extend(
            _play_scenario(scenario, args.seeds, args.rotations, args.seed_start, content)
        )
        pd.DataFrame(all_rows).to_csv(output / "games_partial.csv", index=False)

    partial_summary = _summaries(pd.DataFrame(all_rows))
    best_supply = _choose_supply(partial_summary)
    climate_scenario = {
        "id": "climate",
        "label": f"6. {best_supply} solos + temperatura crítica 33°C",
        "rotate_start": True,
        "soil_supply": best_supply,
        "critical_temperature": 33.0,
    }
    all_rows.extend(
        _play_scenario(
            climate_scenario,
            args.seeds,
            args.rotations,
            args.seed_start,
            content,
        )
    )

    results = pd.DataFrame(all_rows)
    summary = _summaries(results)
    players = _player_rows(results)
    results.to_csv(output / "games.csv", index=False)
    players.to_csv(output / "players.csv", index=False)
    summary.to_csv(output / "summary.csv", index=False)
    metadata = {
        "generated_at_utc": stamp,
        "seeds_per_scenario": args.seeds,
        "rotations_per_seed": args.rotations,
        "games_per_scenario": args.seeds * args.rotations,
        "seed_start": args.seed_start,
        "lineup": list(BASE_LINEUP),
        "selected_soil_supply": best_supply,
        "scenarios": scenarios + [climate_scenario],
    }
    (output / "metadata.json").write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (output / "games_partial.csv").unlink(missing_ok=True)
    print(f"ARTIFACT_DIR={output}")
    print(summary.round(4).to_string(index=False))


if __name__ == "__main__":
    main()
