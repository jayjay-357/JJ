"""Shared data models."""
from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

@dataclass
class CCSDSMessage:
    message_type: str
    metadata: dict[str, str] = field(default_factory=dict)
    data: dict[str, str] = field(default_factory=dict)
    raw_text: str = ""

@dataclass
class OrbitalState:
    epoch: datetime
    frame: str
    position_km: tuple[float, float, float]
    velocity_km_s: tuple[float, float, float]
    covariance: list[list[float]] | None = None
    source_format: str = "OPM"
    metadata: dict[str, Any] = field(default_factory=dict)

@dataclass
class AdaptiveIndicators:
    uncertainty: float | None = None
    data_age: float | None = None
    conjunction_relevance: float | None = None

@dataclass
class AdaptiveDecision:
    score: float
    level: str
    recommended_effort: str
    available_indicators: tuple[str, ...]

@dataclass
class StateVector:
    epoch: datetime
    position_km: tuple[float, float, float]
    velocity_km_s: tuple[float, float, float]
    frame: str = "GCRF"
