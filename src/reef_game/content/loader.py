from pathlib import Path

import yaml

from ..engine.enums import CoralTrait, ResourceType
from ..engine.models import CoralDefinition, Cost


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
        )
        result[coral.coral_id] = coral

    return result


def load_yaml_config(path: str | Path) -> dict:
    return yaml.safe_load(Path(path).read_text(encoding="utf-8"))
