from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class ExtractionRequest(BaseModel):
    seed: int = Field(default=2026, ge=1, le=999999)
    threshold: float | None = Field(default=None, ge=0.1, le=0.95)


class ScenarioRequest(BaseModel):
    kind: Literal["flood_corridor", "bridge_failure", "construction", "critical_link"] = (
        "critical_link"
    )
    severity: float = Field(default=0.55, ge=0.05, le=1.0)
    removed_edges: list[str] | None = None
    origin: str | None = None
    destination: str | None = None
    seed: int = Field(default=2026, ge=1, le=999999)


class RouteRequest(BaseModel):
    origin: str
    destination: str
    excluded_edges: list[str] = Field(default_factory=list)
    alternatives: int = Field(default=3, ge=1, le=5)
    seed: int = Field(default=2026, ge=1, le=999999)
