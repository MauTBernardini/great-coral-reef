from enum import Enum


class ResourceType(str, Enum):
    SUN = "sun"
    PLANKTON = "plankton"
    O2 = "o2"


class PlayerId(int, Enum):
    P1 = 1
    P2 = 2


class ActionType(str, Enum):
    PLACE_CORAL = "place_coral"
    PLACE_STAGHORN_PAIR = "place_staghorn_pair"
    PLACE_SOIL = "place_soil"
    PLAY_FAUNA = "play_fauna"
    PLAY_PARASITE = "play_parasite"
    MOVE_FAUNA = "move_fauna"
    MOVE_SMALL_FISH = "move_small_fish"
    BUY_CORALS = "buy_corals"
    PASS = "pass"


class CoralTrait(str, Enum):
    BRANCHING = "branching"
    MASSIVE = "massive"
    SPONGE = "sponge"
    VERTICAL = "vertical"
