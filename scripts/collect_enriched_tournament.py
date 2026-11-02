from __future__ import annotations

import argparse
import json
import random
import sys
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd
from tqdm.auto import tqdm

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))


def load_game_content():
    from reef_game.content.loader import (
        load_corals,
        load_fauna,
        load_instincts,
        load_soils,
        load_upgrades,
    )
    from reef_game.engine.setup import load_balance_rules, load_climate_config

    return {
        "corals": load_corals(ROOT / "configs" / "corals.yaml"),
        "soils": load_soils(ROOT / "configs" / "soils.yaml"),
        "fauna": load_fauna(ROOT / "configs" / "fauna.yaml"),
        "instincts": load_instincts(ROOT / "configs" / "instincts.yaml"),
        "upgrades": load_upgrades(ROOT / "configs" / "upgrades.yaml"),
        "balance": load_balance_rules(ROOT / "configs" / "balance_rules.yaml"),
        "climate": load_climate_config(ROOT / "configs" / "climate.yaml"),
    }


def resource_value(mapping, resource) -> int:
    return int(mapping.get(resource, 0))


def printed_cost(definition) -> int:
    return int(sum(definition.cost.values.values()))


def card_events(state, agents_by_player: dict, winner) -> list[dict]:
    rows = []
    for event in state.action_history:
        player = int(event["player"])
        agent = agents_by_player[player]
        common = {
            "seed": state.seed,
            "player": player,
            "agent": agent,
            "won": int(winner is not None and winner.value == player),
            "round": int(event.get("round", state.round)),
            "turn": int(event["turn"]),
        }
        fauna_id = event.get("fauna_id")
        coral_id = event.get("coral_id")
        soil_id = event.get("soil_id")
        if fauna_id and event.get("result") in {"play_fauna", "play_parasite"}:
            definition = state.available_fauna[fauna_id]
            rows.append(
                {
                    **common,
                    "category": "fauna",
                    "card": fauna_id,
                    "copies": 1,
                    "printed_cost": printed_cost(definition),
                    "immediate_points": float(event.get("points_gained", 0)),
                }
            )
        elif coral_id and event.get("action_type") in {
            "place_coral",
            "place_staghorn_pair",
        }:
            definition = state.available_corals[coral_id]
            copies = 2 if event.get("action_type") == "place_staghorn_pair" else 1
            rows.append(
                {
                    **common,
                    "category": "coral",
                    "card": coral_id,
                    "copies": copies,
                    "printed_cost": printed_cost(definition),
                    "immediate_points": float(event.get("points_gained", 0)),
                }
            )
        elif soil_id and event.get("result") == "place_soil":
            definition = state.available_soils[soil_id]
            rows.append(
                {
                    **common,
                    "category": "soil",
                    "card": soil_id,
                    "copies": 1,
                    "printed_cost": printed_cost(definition),
                    "immediate_points": 0.0,
                }
            )
    return rows


def final_player_metrics(state, player_id, agent: str, winner) -> dict:
    from reef_game.engine.enums import ResourceType
    from reef_game.engine.scoring import (
        effective_habitat_capacity,
        occupied_habitat,
        score_coral,
        score_fauna,
        score_instinct,
    )

    player = state.players[player_id]
    layers = range(state.board.max_layers)
    coral_counts = {layer: 0 for layer in layers}
    coral_points = {layer: 0.0 for layer in layers}
    fauna_counts = {layer: 0 for layer in layers}
    fauna_points = {layer: 0.0 for layer in layers}
    habitat_capacity = 0
    habitat_used = 0
    coral_by_type = {coral_id: 0 for coral_id in state.available_corals}
    fauna_by_type = {fauna_id: 0 for fauna_id in state.available_fauna}
    soil_by_type = {soil_id: 0 for soil_id in state.available_soils}

    for position, cell in state.board.cells.items():
        layer = position[2]
        if cell.soil is not None and cell.soil.owner == player_id:
            soil_by_type[cell.soil.soil_id] += 1
        if cell.occupant is not None and cell.occupant.owner == player_id:
            coral_counts[layer] += 1
            coral_by_type[cell.occupant.coral_id] += 1
            coral_points[layer] += score_coral(state, cell.occupant)
            habitat_capacity += effective_habitat_capacity(state, cell)
            habitat_used += occupied_habitat(state, cell)
        for fauna_id, fauna_owner in cell.fauna_with_owners():
            if fauna_owner == player_id:
                fauna_counts[layer] += 1
                fauna_by_type[fauna_id] += 1
                fauna_points[layer] += score_fauna(state, fauna_id, position, player_id)

    full_towers = 0
    surface_columns = 0
    for x in range(state.board.width):
        for y in range(state.board.height):
            owners = [state.board.cells[(x, y, z)].occupant for z in layers]
            if all(occupant is not None and occupant.owner == player_id for occupant in owners):
                full_towers += 1
            top = owners[-1]
            if top is not None and top.owner == player_id:
                surface_columns += 1

    return {
        "seed": state.seed,
        "player": player_id.value,
        "agent": agent,
        "won": int(winner == player_id),
        "score": player.score,
        "turns": state.turn,
        "rounds": state.round,
        "corals_total": sum(coral_counts.values()),
        "fauna_total": sum(fauna_counts.values()),
        "coral_points_total": sum(coral_points.values()),
        "fauna_points_total": sum(fauna_points.values()),
        "instinct_points": score_instinct(state, player_id),
        "habitat_capacity": habitat_capacity,
        "habitat_used": habitat_used,
        "habitat_fill": habitat_used / habitat_capacity if habitat_capacity else 0,
        "full_towers": full_towers,
        "surface_columns": surface_columns,
        "ponds": sum(pond.owner == player_id for pond in state.ponds),
        "dead_turns": player.dead_turns,
        "hand_size": len(player.hand),
        "final_sun": resource_value(player.resources, ResourceType.SUN),
        "final_plankton": resource_value(player.resources, ResourceType.PLANKTON),
        "final_o2": resource_value(player.resources, ResourceType.O2),
        "produced_sun": resource_value(player.produced_resources, ResourceType.SUN),
        "produced_plankton": resource_value(player.produced_resources, ResourceType.PLANKTON),
        "produced_o2": resource_value(player.produced_resources, ResourceType.O2),
        "spent_sun": resource_value(player.spent_resources, ResourceType.SUN),
        "spent_plankton": resource_value(player.spent_resources, ResourceType.PLANKTON),
        "spent_o2": resource_value(player.spent_resources, ResourceType.O2),
        "instincts": ";".join(player.instinct_cards),
        "upgrades": ";".join(player.upgrade_cards),
        **{f"coral_{card_id}": count for card_id, count in coral_by_type.items()},
        **{f"fauna_{card_id}": count for card_id, count in fauna_by_type.items()},
        **{f"soil_{soil_id}": count for soil_id, count in soil_by_type.items()},
        **{f"corals_z{z}": coral_counts[z] for z in layers},
        **{f"coral_points_z{z}": coral_points[z] for z in layers},
        **{f"fauna_z{z}": fauna_counts[z] for z in layers},
        **{f"fauna_points_z{z}": fauna_points[z] for z in layers},
    }


def final_card_scores(state, agents_by_player: dict, winner) -> list[dict]:
    from reef_game.engine.scoring import score_coral, score_fauna

    rows = []
    for position, cell in state.board.cells.items():
        if cell.occupant is not None:
            owner = cell.occupant.owner
            definition = state.available_corals[cell.occupant.coral_id]
            rows.append(
                {
                    "seed": state.seed,
                    "player": owner.value,
                    "agent": agents_by_player[owner.value],
                    "won": int(winner == owner),
                    "category": "coral",
                    "card": cell.occupant.coral_id,
                    "layer": position[2],
                    "printed_cost": printed_cost(definition),
                    "final_points": score_coral(state, cell.occupant),
                }
            )
        for fauna_id, owner in cell.fauna_with_owners():
            definition = state.available_fauna[fauna_id]
            rows.append(
                {
                    "seed": state.seed,
                    "player": owner.value,
                    "agent": agents_by_player[owner.value],
                    "won": int(winner == owner),
                    "category": "fauna",
                    "card": fauna_id,
                    "layer": position[2],
                    "printed_cost": printed_cost(definition),
                    "final_points": score_fauna(state, fauna_id, position, owner),
                }
            )
    return rows


def curve_rows(telemetry, agents_by_player: dict) -> list[dict]:
    last_by_round = {}
    for snapshot in telemetry.states:
        last_by_round[int(snapshot["round"])] = snapshot

    rows = []
    previous_turn = 0
    for round_number, snapshot in sorted(last_by_round.items()):
        turns_in_round = int(snapshot["turn"]) - previous_turn
        previous_turn = int(snapshot["turn"])
        for player_id, player in snapshot["players"].items():
            rows.append(
                {
                    "seed": snapshot["seed"],
                    "round": round_number,
                    "player": player_id,
                    "agent": agents_by_player[player_id],
                    "turn": snapshot["turn"],
                    "turns_in_round": turns_in_round,
                    "temperature": snapshot["temperature"],
                    "ph": snapshot["ph"],
                    "era": snapshot["current_era"],
                    "occupancy": snapshot["occupancy_ratio"],
                    "sun": player["resources"]["sun"],
                    "plankton": player["resources"]["plankton"],
                    "o2": player["resources"]["o2"],
                    "produced_sun": player["produced"]["sun"],
                    "produced_plankton": player["produced"]["plankton"],
                    "produced_o2": player["produced"]["o2"],
                    "spent_sun": player["spent"]["sun"],
                    "spent_plankton": player["spent"]["plankton"],
                    "score": player["score"],
                    "fauna": player["fauna_count"],
                    "habitat": player["habitat_capacity"],
                    "corals_z0": player["corals_by_layer"].get(0, 0),
                    "corals_z1": player["corals_by_layer"].get(1, 0),
                    "corals_z2": player["corals_by_layer"].get(2, 0),
                }
            )
    return rows


def collect(games: int) -> Path:
    from reef_game.agents.greedy_agent import GreedyAgent
    from reef_game.agents.long_term_agent import LongTermAgent
    from reef_game.engine.enums import PlayerId
    from reef_game.engine.setup import create_initial_state
    from reef_game.simulation.runner import run_game

    content = load_game_content()
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    output = ROOT / "artifacts" / "tournaments" / f"enriched_{stamp}_v0.1.0"
    output.mkdir(parents=True, exist_ok=False)
    seat_rng = random.Random(1000)
    game_rows = []
    player_rows = []
    event_rows = []
    final_card_rows = []
    curves = []
    soil_supply = sum(soil.supply for soil in content["soils"].values())

    for index in tqdm(range(games), desc="Enriched tournament"):
        seed = 1000 + index
        state = create_initial_state(
            seed=seed,
            coral_definitions=content["corals"],
            balance_rules=content["balance"],
            climate_config=content["climate"],
            soil_definitions=content["soils"],
            fauna_definitions=content["fauna"],
            instinct_definitions=content["instincts"],
            upgrade_definitions=content["upgrades"],
        )
        seat_names = ["greedy", "longterm", "greedy", "longterm"]
        seat_rng.shuffle(seat_names)
        agent_names = {
            player_id.value: agent_name
            for player_id, agent_name in zip(PlayerId, seat_names, strict=True)
        }
        agents = {
            player_id: GreedyAgent() if agent_name == "greedy" else LongTermAgent()
            for player_id, agent_name in zip(PlayerId, seat_names, strict=True)
        }
        final_state, summary, telemetry = run_game(
            state,
            agents,
            max_rounds=50,
            compact_spatial_actions=True,
        )
        winner = final_state.winner
        game_rows.append(
            {
                "seed": seed,
                "winner": winner.value if winner else None,
                **{f"p{pid}_agent": name for pid, name in agent_names.items()},
                "turns": final_state.turn,
                "rounds": final_state.round,
                "temperature": final_state.temperature,
                "ph": final_state.ph,
                "occupancy": summary["board_occupancy"],
                "deck_remaining": len(final_state.coral_deck),
                "soil_remaining": len(final_state.soil_pile),
                "soil_supply": soil_supply,
            }
        )
        for player_id in PlayerId:
            player_rows.append(
                final_player_metrics(
                    final_state, player_id, agent_names[player_id.value], winner
                )
            )
        event_rows.extend(card_events(final_state, agent_names, winner))
        final_card_rows.extend(final_card_scores(final_state, agent_names, winner))
        curves.extend(curve_rows(telemetry, agent_names))

    files = {
        "games": "enriched_games.csv",
        "players": "enriched_players.csv",
        "card_events": "card_events.csv",
        "final_cards": "final_card_scores.csv",
        "curves": "round_curves.csv",
    }
    pd.DataFrame(game_rows).to_csv(output / files["games"], index=False)
    pd.DataFrame(player_rows).to_csv(output / files["players"], index=False)
    pd.DataFrame(event_rows).to_csv(output / files["card_events"], index=False)
    pd.DataFrame(final_card_rows).to_csv(output / files["final_cards"], index=False)
    pd.DataFrame(curves).to_csv(output / files["curves"], index=False)
    metadata = {
        "generated_at_utc": stamp,
        "games": games,
        "seed_start": 1000,
        "agents": ["greedy", "longterm"],
        "player_count": content["balance"]["players"]["count"],
        "board": content["balance"]["board"],
        "soil_supply": soil_supply,
        "soil_supply_by_type": {
            soil_id: soil.supply for soil_id, soil in content["soils"].items()
        },
        "randomize_seats": True,
        "compact_spatial_actions": True,
        "files": files,
    }
    (output / "metadata.json").write_text(
        json.dumps(metadata, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    return output


def main() -> None:
    parser = argparse.ArgumentParser(description="Coleta métricas enriquecidas do torneio.")
    parser.add_argument("--games", type=int, default=200)
    args = parser.parse_args()
    output = collect(args.games)
    print(f"Enriched artifact: {output}")


if __name__ == "__main__":
    main()
