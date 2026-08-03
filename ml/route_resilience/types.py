from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Literal

RoadClass = Literal["primary", "secondary", "local", "bridge"]
OcclusionKind = Literal["cloud", "tree_canopy", "building_shadow"]


@dataclass(slots=True)
class RoadNode:
    id: str
    x: float
    y: float
    population: int
    facility: str | None = None


@dataclass(slots=True)
class RoadEdge:
    id: str
    source: str
    target: str
    geometry: list[tuple[float, float]]
    length_km: float
    lanes: int
    speed_kph: float
    road_class: RoadClass
    baseline_flow: int
    flood_risk: float
    occluded_fraction: float = 0.0

    @property
    def travel_minutes(self) -> float:
        return (self.length_km / max(self.speed_kph, 1.0)) * 60.0


@dataclass(slots=True)
class Occlusion:
    id: str
    kind: OcclusionKind
    x: float
    y: float
    width: float
    height: float
    confidence: float


@dataclass(slots=True)
class CityNetwork:
    name: str
    width: int
    height: int
    nodes: list[RoadNode]
    edges: list[RoadEdge]
    occlusions: list[Occlusion]
    seed: int = 2026

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class ExtractionResult:
    raw_mask: Any
    recovered_mask: Any
    confidence: Any
    gap_candidates: list[dict[str, Any]] = field(default_factory=list)
    metrics: dict[str, float] = field(default_factory=dict)


@dataclass(slots=True)
class EdgeCriticality:
    edge_id: str
    score: float
    rank: int
    betweenness: float
    detour_impact: float
    isolation_impact: float
    bridge: bool
    redundancy: float


@dataclass(slots=True)
class DisruptionResult:
    removed_edges: list[str]
    reachable_population_pct: float
    isolated_population: int
    mean_detour_pct: float
    network_efficiency_loss_pct: float
    connected_components: int
    alternate_routes: list[dict[str, Any]]
    edge_impacts: list[dict[str, Any]]
