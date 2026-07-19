from pathlib import Path

import yaml

from ..engine.enums import CoralTrait, ResourceType
from ..engine.models import CoralDefinition, Cost, FloraDefinition, SoilDefinition


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


def load_flora(path: str | Path) -> dict[str, FloraDefinition]:
    data = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    result = {}

    for item in data["flora"]:
        flora = FloraDefinition(
            flora_id=item["flora_id"],
            name=item["name"],
            count=item.get("count", 0),
        )
        result[flora.flora_id] = flora

    return result


def load_yaml_config(path: str | Path) -> dict:
    return yaml.safe_load(Path(path).read_text(encoding="utf-8"))
