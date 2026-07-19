from pathlib import Path

import yaml

from ..engine.enums import CoralTrait, ResourceType
from ..engine.models import CoralDefinition, Cost, FaunaDefinition, SoilDefinition


def load_corals(path: str | Path) -> dict[str, CoralDefinition]:
    data = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    result = {}

    for item in data["corals"]:
        coral = CoralDefinition(
            coral_id=item["coral_id"],
            name=item["name"],
            cost=Cost(values={ResourceType(k): v for k, v in item["cost"].items()}),
            base_points=item["base_points"],
            traits=[CoralTrait(t) for t in item["traits"]],
            max_height_gain=item.get("max_height_gain", 1),
            requires_support=item.get("requires_support", True),
            allowed_layers=item.get("allowed_layers"),
            production={ResourceType(k): v for k, v in item.get("production", {}).items()},
            required_soil=item.get("required_soil"),
            blocks_opponent_adjacent=item.get("blocks_opponent_adjacent", False),
            refund_soil=item.get("refund_soil"),
            refund_sun=item.get("refund_sun", 0),
            deck_count=item.get("deck_count", 0),
            o2=item.get("o2", 0),
            habitat_capacity=item.get("habitat_capacity", 0),
        )
        result[coral.coral_id] = coral

    return result


def load_soils(path: str | Path) -> dict[str, SoilDefinition]:
    data = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    result = {}

    for item in data["soils"]:
        soil = SoilDefinition(
            soil_id=item["soil_id"],
            name=item["name"],
            cost=Cost(values={ResourceType(k): v for k, v in item["cost"].items()}),
            production={ResourceType(k): v for k, v in item.get("production", {}).items()},
            coral_cost_reduction=item.get("coral_cost_reduction", 0),
            supply=item.get("supply", 0),
        )
        result[soil.soil_id] = soil

    return result


def load_fauna(path: str | Path) -> dict[str, FaunaDefinition]:
    data = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    result = {}

    for item in data["fauna"]:
        fauna = FaunaDefinition(
            fauna_id=item["fauna_id"],
            name=item["name"],
            cost=Cost(values={ResourceType(k): v for k, v in item.get("cost", {}).items()}),
            base_points=item.get("base_points", 0),
            deck_count=item.get("deck_count", 0),
            habitat_cost=item.get("habitat_cost", 1),
            required_soil=item.get("required_soil"),
            allowed_layers=item.get("allowed_layers"),
            production={ResourceType(k): v for k, v in item.get("production", {}).items()},
            on_play_draw=item.get("on_play_draw", 0),
            explore_bonus=item.get("explore_bonus", 0),
            is_small_fish=item.get("is_small_fish", False),
            predator_immune=item.get("predator_immune", False),
            patrol=item.get("patrol", False),
            sacrifice_small_fish=item.get("sacrifice_small_fish", 0),
        )
        result[fauna.fauna_id] = fauna

    return result


def load_yaml_config(path: str | Path) -> dict:
    return yaml.safe_load(Path(path).read_text(encoding="utf-8"))
