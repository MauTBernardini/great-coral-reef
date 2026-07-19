from pathlib import Path
from random import Random

import yaml

from .enums import PlayerId, ResourceType
from .models import BoardState, Cell, ClimateCard, GameState, PlayerState


def create_empty_board(width: int, height: int, max_layers: int) -> BoardState:
    cells = {}
    for x in range(width):
        for y in range(height):
            for z in range(max_layers):
                cells[(x, y, z)] = Cell(position=(x, y, z))
    return BoardState(width=width, height=height, max_layers=max_layers, cells=cells)


def load_balance_rules(path: str | Path) -> dict:
    return yaml.safe_load(Path(path).read_text(encoding="utf-8"))


def load_climate_config(path: str | Path) -> dict:
    return yaml.safe_load(Path(path).read_text(encoding="utf-8"))


def _default_balance_rules() -> dict:
    return {
        "board": {"width": 4, "height": 4, "max_layers": 3},
        "players": {"initial_resources": {"sun": 10, "plankton": 10}},
        "climate": {
            "initial_temperature": 28.0,
            "initial_ph": 8.1,
            "temperature_step": 0.5,
            "ph_step": 0.05,
            "critical_temperature": 32.0,
            "critical_ph": 7.4,
            "deck_size": 6,
            "era_thresholds": {
                "2": {"temperature": 29.0, "ph": 7.95},
                "3": {"temperature": 30.5, "ph": 7.8},
            },
        },
    }


def build_climate_deck(seed: int, climate_cfg: dict) -> list[ClimateCard]:
    expanded_deck = []
    for item in climate_cfg["deck"]:
        copies = item.get("number_of_cards", 1)
        for _ in range(copies):
            expanded_deck.append(
                ClimateCard(
                    card_id=item["card_id"],
                    era=item["era"],
                    label=item.get("label", item["card_id"]),
                    number_of_cards=item.get("number_of_cards", 1),
                    event_type=item.get("event_type", "condition"),
                    original_climate_change=item.get("original_climate_change", "Nenhuma"),
                    effect_text=item.get("effect_text", ""),
                    temperature_steps=item.get("temperature_steps", 0),
                    ph_steps=item.get("ph_steps", 0),
                )
            )

    deck_size = climate_cfg.get("deck_size", len(expanded_deck))
    if deck_size > len(expanded_deck):
        raise ValueError("Configured climate deck_size exceeds the number of available card instances.")

    rng = Random(seed)
    rng.shuffle(expanded_deck)
    return expanded_deck[:deck_size]


def create_initial_state(
    seed: int,
    coral_definitions: dict,
    balance_rules: dict | None = None,
    climate_config: dict | None = None,
    soil_definitions: dict | None = None,
) -> GameState:
    balance_rules = balance_rules or _default_balance_rules()
    climate_config = climate_config or {"deck": []}
    soil_definitions = soil_definitions or {}
    soil_supply = {soil_id: soil.supply for soil_id, soil in soil_definitions.items()}

    board_cfg = balance_rules["board"]
    resource_cfg = balance_rules["players"]["initial_resources"]
    climate_cfg = balance_rules["climate"]
    era_thresholds = {int(era): values for era, values in climate_cfg["era_thresholds"].items()}
    climate_deck_cfg = {
        "deck_size": climate_cfg.get("deck_size"),
        "deck": climate_config.get("deck", []),
    }

    board = create_empty_board(
        width=board_cfg["width"],
        height=board_cfg["height"],
        max_layers=board_cfg["max_layers"],
    )

    def initial_resources():
        return {
            ResourceType.SUN: resource_cfg["sun"],
            ResourceType.PLANKTON: resource_cfg["plankton"],
        }

    def zeroed():
        return {ResourceType.SUN: 0, ResourceType.PLANKTON: 0}

    players = {
        PlayerId.P1: PlayerState(
            player_id=PlayerId.P1,
            resources=initial_resources(),
            spent_resources=zeroed(),
            produced_resources=zeroed(),
        ),
        PlayerId.P2: PlayerState(
            player_id=PlayerId.P2,
            resources=initial_resources(),
            spent_resources=zeroed(),
            produced_resources=zeroed(),
        ),
    }

    return GameState(
        seed=seed,
        turn=1,
        round=1,
        active_player=PlayerId.P1,
        players=players,
        board=board,
        available_corals=coral_definitions,
        temperature=climate_cfg["initial_temperature"],
        ph=climate_cfg["initial_ph"],
        temperature_step=climate_cfg["temperature_step"],
        ph_step=climate_cfg["ph_step"],
        critical_temperature=climate_cfg["critical_temperature"],
        critical_ph=climate_cfg["critical_ph"],
        current_era=1,
        era_thresholds=era_thresholds,
        climate_deck=build_climate_deck(seed=seed, climate_cfg=climate_deck_cfg),
        available_soils=soil_definitions,
        soil_supply=soil_supply,
    )
