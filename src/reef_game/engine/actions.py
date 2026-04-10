from dataclasses import dataclass
from typing import Tuple

from .enums import ActionType


@dataclass(frozen=True)
class Action:
    action_type: ActionType


@dataclass(frozen=True)
class PlaceCoralAction(Action):
    coral_id: str
    position: Tuple[int, int, int]

    def __init__(self, coral_id: str, position: Tuple[int, int, int]):
        object.__setattr__(self, "action_type", ActionType.PLACE_CORAL)
        object.__setattr__(self, "coral_id", coral_id)
        object.__setattr__(self, "position", position)


@dataclass(frozen=True)
class PassAction(Action):
    def __init__(self):
        object.__setattr__(self, "action_type", ActionType.PASS)
