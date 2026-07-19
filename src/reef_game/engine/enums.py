from enum import Enum


class ResourceType(str, Enum):
    SUN = "sun"
    PLANKTON = "plankton"


class PlayerId(int, Enum):
    P1 = 1
    P2 = 2


class ActionType(str, Enum):
    PLACE_CORAL = "place_coral"
    PLACE_STAGHORN_PAIR = "place_staghorn_pair"
    PLACE_SOIL = "place_soil"
    BUY_FLORA = "buy_flora"
    PASS = "pass"


class CoralTrait(str, Enum):
    BRANCHING = "branching"
    MASSIVE = "massive"
    SPONGE = "sponge"
    VERTICAL = "vertical"
