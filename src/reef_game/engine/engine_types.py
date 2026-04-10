from dataclasses import dataclass
from typing import List, Tuple

Coord3D = Tuple[int, int, int]


@dataclass(frozen=True)
class NeighborPositions:
    same_layer: List[Coord3D]
