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
class PlaceStaghornPairAction(Action):
    """Staghorn ability: place two staghorns in a single turn.

    Costs both staghorns' resources plus a +1 Plankton surcharge; the turn only
    advances once. ``first_position`` is placed before ``second_position`` so the
    second staghorn may be stacked directly on the first.
    """

    first_position: Tuple[int, int, int]
    second_position: Tuple[int, int, int]

    def __init__(self, first_position: Tuple[int, int, int], second_position: Tuple[int, int, int]):
        object.__setattr__(self, "action_type", ActionType.PLACE_STAGHORN_PAIR)
        object.__setattr__(self, "first_position", first_position)
        object.__setattr__(self, "second_position", second_position)


@dataclass(frozen=True)
class PlaceSoilAction(Action):
    """Comprar e colocar um tile de solo na camada do fundo (z=0)."""

    soil_id: str
    position: Tuple[int, int, int]

    def __init__(self, soil_id: str, position: Tuple[int, int, int]):
        object.__setattr__(self, "action_type", ActionType.PLACE_SOIL)
        object.__setattr__(self, "soil_id", soil_id)
        object.__setattr__(self, "position", position)


@dataclass(frozen=True)
class PassAction(Action):
    def __init__(self):
        object.__setattr__(self, "action_type", ActionType.PASS)
