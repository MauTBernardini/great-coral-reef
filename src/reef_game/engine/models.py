from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from .enums import CoralTrait, PlayerId, ResourceType

Coord3D = Tuple[int, int, int]


@dataclass(frozen=True)
class Cost:
    values: Dict[ResourceType, int]


@dataclass(frozen=True)
class CoralDefinition:
    coral_id: str
    name: str
    cost: Cost
    base_points: int
    traits: List[CoralTrait]
    max_height_gain: int = 1
    requires_support: bool = True


@dataclass(frozen=True)
class ClimateCard:
    card_id: str
    era: int
    label: str
    number_of_cards: int = 1
    event_type: str = "condition"
    original_climate_change: str = "Nenhuma"
    effect_text: str = ""
    temperature_steps: int = 0
    ph_steps: int = 0


@dataclass
class PlacedCoral:
    instance_id: str
    coral_id: str
    owner: PlayerId
    position: Coord3D


@dataclass
class Cell:
    position: Coord3D
    occupant: Optional[PlacedCoral] = None


@dataclass
class PlayerState:
    player_id: PlayerId
    resources: Dict[ResourceType, int]
    hand: List[str] = field(default_factory=list)
    score: int = 0
    passed_last_turn: bool = False
    spent_resources: Dict[ResourceType, int] = field(default_factory=dict)
    placed_corals: int = 0
    dead_turns: int = 0


@dataclass
class BoardState:
    width: int
    height: int
    max_layers: int
    cells: Dict[Coord3D, Cell]


@dataclass
class GameState:
    seed: int
    turn: int
    round: int
    active_player: PlayerId
    players: Dict[PlayerId, PlayerState]
    board: BoardState
    available_corals: Dict[str, CoralDefinition]
    temperature: float
    ph: float
    temperature_step: float
    ph_step: float
    critical_temperature: float
    critical_ph: float
    current_era: int
    era_thresholds: Dict[int, dict]
    climate_deck: List[ClimateCard] = field(default_factory=list)
    climate_discard: List[ClimateCard] = field(default_factory=list)
    era_transition_log: List[dict] = field(default_factory=list)
    action_history: List[dict] = field(default_factory=list)
    is_terminal: bool = False
    winner: Optional[PlayerId] = None
