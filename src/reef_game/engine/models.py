from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from .enums import CoralTrait, PlayerId, ResourceType

Coord3D = Tuple[int, int, int]

# Número máximo de cartas de coral na mão de um jogador.
MAX_HAND_SIZE = 10
# Cartas de coral distribuídas a cada jogador no início.
STARTING_HAND_SIZE = 5


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
    allowed_layers: Optional[List[int]] = None
    # Base resources this coral yields each Production Phase (empty = none).
    production: Dict[ResourceType, int] = field(default_factory=dict)
    # Só pode ser construído se o solo da base da coluna for este soil_id (Sun Coral).
    required_soil: Optional[str] = None
    # Oponentes não podem construir em células vizinhas (mesma camada) a este coral (Fox Coral).
    blocks_opponent_adjacent: bool = False
    # Rebate: se construído numa coluna com este solo, devolve refund_sun Sol (Branched Finger).
    refund_soil: Optional[str] = None
    refund_sun: int = 0
    # Quantas cópias deste coral existem no baralho fechado (disponibilidade).
    deck_count: int = 0
    # O2 gerado por rodada na Fase de Produção (base para futura Fauna).
    o2: int = 0
    # Capacidade habitacional: quantas Faunas podem morar neste coral (futuro).
    habitat_capacity: int = 0


@dataclass(frozen=True)
class SoilDefinition:
    soil_id: str
    name: str
    cost: Cost
    # Recursos que o solo gera por Fase de Produção.
    production: Dict[ResourceType, int] = field(default_factory=dict)
    # Habilidade (Rocky Reef): reduz o custo (Sol) dos corais construídos na coluna.
    coral_cost_reduction: int = 0
    # Quantidade disponível no suprimento compartilhado.
    supply: int = 0


@dataclass(frozen=True)
class FaunaDefinition:
    fauna_id: str
    name: str
    cost: Cost
    base_points: int = 0
    deck_count: int = 0
    # Capacidade habitacional que ocupa no coral (Seahorse em Gorgonian = 0, tratado à parte).
    habitat_cost: int = 1
    # Só pode ser jogada num coral cuja base seja este solo (Mandarin: rocky; Sea Cucumber: sandy).
    required_soil: Optional[str] = None
    # Só pode ser jogada num coral nestas camadas (Anthias: [1, 2]).
    allowed_layers: Optional[List[int]] = None
    # Recursos que a fauna gera na Fase de Produção (Lanternfish/Sea Cucumber).
    production: Dict[ResourceType, int] = field(default_factory=dict)
    # Ao ser jogada, saca imediatamente N cartas do baralho (Cyclothone: 1).
    on_play_draw: int = 0
    # Enquanto no board, cada compra de cartas ("explore") saca +N (Leafy Seadragon: 1).
    explore_bonus: int = 0
    # Conta como "peixe pequeno" (pode ser sacrificado como custo, ex.: do tubarão).
    is_small_fish: bool = False
    # Imune a predadores: pode ser jogada mesmo adjacente a um predador patrulhando (Mandarin).
    predator_immune: bool = False
    # Predador que patrulha: bloqueia outra fauna nos tiles adjacentes (Blacktip).
    patrol: bool = False
    # Ao ser jogada, sacrifica N peixes pequenos do seu board como custo (Blacktip: 1).
    sacrifice_small_fish: int = 0


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
class PlacedSoil:
    soil_id: str
    owner: PlayerId
    position: Coord3D


@dataclass
class Cell:
    position: Coord3D
    occupant: Optional[PlacedCoral] = None
    soil: Optional[PlacedSoil] = None
    # Fauna morando no coral desta célula (fauna_ids); dono = dono do coral.
    fauna: List[str] = field(default_factory=list)


@dataclass
class PlayerState:
    player_id: PlayerId
    resources: Dict[ResourceType, int]
    hand: List[str] = field(default_factory=list)
    score: int = 0
    passed_last_turn: bool = False
    spent_resources: Dict[ResourceType, int] = field(default_factory=dict)
    produced_resources: Dict[ResourceType, int] = field(default_factory=dict)
    placed_corals: int = 0
    dead_turns: int = 0
    # Saiu da rodada atual (passou) — deixa de receber turnos até a rodada acabar.
    passed_this_round: bool = False
    # Já comprou do baralho de corais nesta rodada (máx. 1x/rodada).
    bought_corals_this_round: bool = False


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
    available_soils: Dict[str, SoilDefinition] = field(default_factory=dict)
    # Pilha de compra de solos: fila embaralhada de soil_ids; compra-se do topo (índice 0).
    soil_pile: List[str] = field(default_factory=list)
    # Baralho fechado COMPARTILHADO: fila embaralhada de coral_ids E fauna_ids (compra do topo).
    coral_deck: List[str] = field(default_factory=list)
    available_fauna: Dict[str, "FaunaDefinition"] = field(default_factory=dict)
