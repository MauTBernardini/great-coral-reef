from enum import Enum


class ResourceType(str, Enum):
    SUN = "sun"
    PLANKTON = "plankton"


class PlayerId(int, Enum):
    P1 = 1
    P2 = 2


class ActionType(str, Enum):
    PLACE_CORAL = "place_coral"
    PASS = "pass"


class CoralTrait(str, Enum):
    BRANCHING = "branching"
    MASSIVE = "massive"
    SPONGE = "sponge"
    VERTICAL = "vertical"
