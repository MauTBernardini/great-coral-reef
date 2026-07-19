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
    """Comprar o solo do topo da pilha e baixá-lo no fundo (z=0), na posição dada.

    O tipo de solo é o topo da pilha (não se escolhe). Se o custo (Sol) do solo
    sacado for maior que o Sol do jogador, a ação é perdida e o solo volta ao topo.
    """

    position: Tuple[int, int, int]

    def __init__(self, position: Tuple[int, int, int]):
        object.__setattr__(self, "action_type", ActionType.PLACE_SOIL)
        object.__setattr__(self, "position", position)


@dataclass(frozen=True)
class BuyFloraAction(Action):
    """Comprar 2 cartas de flora fechadas (sacar do deck para a mão, teto de 10)."""

    count: int = 2

    def __init__(self, count: int = 2):
        object.__setattr__(self, "action_type", ActionType.BUY_FLORA)
        object.__setattr__(self, "count", count)


@dataclass(frozen=True)
class PassAction(Action):
    def __init__(self):
        object.__setattr__(self, "action_type", ActionType.PASS)
