"""Pair-specific conjunction and collision-risk calculations.

The probability model uses a Gaussian relative-position uncertainty projected
onto the encounter plane at TCA. It is intended for research evaluation, not
as a replacement for an operational conjunction-data-message processor.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from math import cos, pi, sin, sqrt
from typing import Iterable

import numpy as np
from scipy.integrate import quad


class ObjectType(str, Enum):
    DEBRIS = "debris"
    SATELLITE = "satellite"
    ROCKET = "rocket"


class PairType(str, Enum):
    DEBRIS_DEBRIS = "debris-debris"
    SATELLITE_DEBRIS = "satellite-debris"
    ROCKET_DEBRIS = "rocket-debris"


@dataclass(frozen=True)
class SpaceObject:
    """Object metadata required for pair-risk assessment.

    ``position_covariance_km2`` is the 3x3 position covariance at TCA in the
    same inertial frame as the conjunction state. A 6x6 state covariance is
    also accepted by :func:`position_covariance_from_state`.
    """

    object_id: str
    object_type: ObjectType
    hard_body_radius_m: float
    position_covariance_km2: tuple[tuple[float, float, float], ...] | None = None

    def __post_init__(self) -> None:
        if not self.object_id.strip():
            raise ValueError("object_id must not be empty.")
        if self.hard_body_radius_m <= 0 or not np.isfinite(self.hard_body_radius_m):
            raise ValueError("hard_body_radius_m must be positive and finite.")
        if self.position_covariance_km2 is not None:
            covariance = np.asarray(self.position_covariance_km2, dtype=float)
            validate_position_covariance(covariance)


@dataclass(frozen=True)
class PairRiskResult:
    object_1: str
    object_2: str
    pair_type: PairType
    miss_distance_km: float
    hard_body_radius_km: float
    relative_speed_km_s: float
    collision_probability: float | None
    risk_level: str
    geometric_collision: bool


def pair_type_for(object_1: ObjectType, object_2: ObjectType) -> PairType:
    """Return the supported debris-involving pair category."""
    pair = {object_1, object_2}
    if pair == {ObjectType.DEBRIS}:
        return PairType.DEBRIS_DEBRIS
    if pair == {ObjectType.SATELLITE, ObjectType.DEBRIS}:
        return PairType.SATELLITE_DEBRIS
    if pair == {ObjectType.ROCKET, ObjectType.DEBRIS}:
        return PairType.ROCKET_DEBRIS
    raise ValueError(
        "Supported pair types are debris-debris, satellite-debris, and rocket-debris."
    )


def validate_position_covariance(covariance_km2: np.ndarray) -> None:
    """Validate a symmetric positive-semidefinite 3x3 covariance matrix."""
    if covariance_km2.shape != (3, 3):
        raise ValueError("Position covariance must have shape (3, 3).")
    if not np.isfinite(covariance_km2).all():
        raise ValueError("Position covariance must contain only finite values.")
    if not np.allclose(covariance_km2, covariance_km2.T, atol=1e-12):
        raise ValueError("Position covariance must be symmetric.")
    if float(np.min(np.linalg.eigvalsh(covariance_km2))) < -1e-12:
        raise ValueError("Position covariance must be positive semidefinite.")


def position_covariance_from_state(covariance: Iterable[Iterable[float]]) -> np.ndarray:
    """Extract the position block from a 3x3 or 6x6 state covariance."""
    matrix = np.asarray(covariance, dtype=float)
    if matrix.shape == (3, 3):
        result = matrix
    elif matrix.shape == (6, 6):
        result = matrix[:3, :3]
    else:
        raise ValueError("Covariance must have shape (3, 3) or (6, 6).")
    validate_position_covariance(result)
    return result.copy()


def _encounter_basis(relative_velocity_km_s: np.ndarray) -> np.ndarray:
    speed = float(np.linalg.norm(relative_velocity_km_s))
    if speed <= 0:
        raise ValueError("Relative velocity must be non-zero for encounter-plane probability.")
    normal = relative_velocity_km_s / speed
    reference = np.array([0.0, 0.0, 1.0])
    if abs(float(np.dot(normal, reference))) > 0.9:
        reference = np.array([0.0, 1.0, 0.0])
    axis_1 = np.cross(normal, reference)
    axis_1 /= np.linalg.norm(axis_1)
    axis_2 = np.cross(normal, axis_1)
    return np.column_stack((axis_1, axis_2))


def encounter_plane_probability(
    miss_vector_km: Iterable[float],
    relative_velocity_km_s: Iterable[float],
    relative_position_covariance_km2: Iterable[Iterable[float]],
    hard_body_radius_km: float,
) -> float:
    """Calculate Gaussian collision probability inside the hard-body disk.

    The relative position covariance is projected onto the plane normal to
    relative velocity. The probability is the integral of that 2-D Gaussian
    over a circle centered on the origin with radius ``hard_body_radius_km``.
    """
    miss = np.asarray(tuple(miss_vector_km), dtype=float)
    velocity = np.asarray(tuple(relative_velocity_km_s), dtype=float)
    covariance = np.asarray(relative_position_covariance_km2, dtype=float)
    if miss.shape != (3,) or velocity.shape != (3,):
        raise ValueError("Miss vector and relative velocity must each have 3 components.")
    if not np.isfinite(miss).all() or not np.isfinite(velocity).all():
        raise ValueError("Miss vector and relative velocity must be finite.")
    if hard_body_radius_km <= 0 or not np.isfinite(hard_body_radius_km):
        raise ValueError("hard_body_radius_km must be positive and finite.")
    validate_position_covariance(covariance)

    basis = _encounter_basis(velocity)
    mean_2d = basis.T @ miss
    covariance_2d = basis.T @ covariance @ basis
    covariance_2d = 0.5 * (covariance_2d + covariance_2d.T)
    eigenvalues = np.linalg.eigvalsh(covariance_2d)
    if float(np.min(eigenvalues)) <= 1e-15:
        raise ValueError("Encounter-plane covariance must be positive definite.")

    determinant = float(np.linalg.det(covariance_2d))
    inverse = np.linalg.inv(covariance_2d)
    normalization = 1.0 / (2.0 * pi * sqrt(determinant))
    radius = float(hard_body_radius_km)

    def radial_integral(theta: float) -> float:
        direction = np.array([cos(theta), sin(theta)])

        def integrand(rho: float) -> float:
            delta = rho * direction - mean_2d
            exponent = -0.5 * float(delta @ inverse @ delta)
            return normalization * np.exp(exponent) * rho

        value, _ = quad(integrand, 0.0, radius, epsabs=1e-12, epsrel=2e-7, limit=100)
        return value

    probability, _ = quad(radial_integral, 0.0, 2.0 * pi, epsabs=1e-11, epsrel=2e-6, limit=100)
    return float(np.clip(probability, 0.0, 1.0))


def risk_level(collision_probability: float | None) -> str:
    """Map collision probability to the project's HIGH/MEDIUM/LOW levels."""
    if collision_probability is None:
        return "UNQUANTIFIED"
    if not 0.0 <= collision_probability <= 1.0:
        raise ValueError("collision_probability must be between 0 and 1.")
    if collision_probability >= 1e-4:
        return "HIGH"
    if collision_probability >= 1e-6:
        return "MEDIUM"
    return "LOW"


def assess_pair_risk(
    object_1: SpaceObject,
    object_2: SpaceObject,
    miss_distance_km: float,
    relative_velocity_km_s: Iterable[float],
    miss_vector_km: Iterable[float] | None = None,
) -> PairRiskResult:
    """Assess a debris-involving pair and calculate collision probability."""
    pair_type = pair_type_for(object_1.object_type, object_2.object_type)
    velocity = np.asarray(tuple(relative_velocity_km_s), dtype=float)
    if velocity.shape != (3,) or not np.isfinite(velocity).all():
        raise ValueError("relative_velocity_km_s must be a finite 3-vector.")
    if miss_distance_km < 0 or not np.isfinite(miss_distance_km):
        raise ValueError("miss_distance_km must be finite and non-negative.")

    hbr_km = (object_1.hard_body_radius_m + object_2.hard_body_radius_m) / 1000.0
    geometric_collision = miss_distance_km <= hbr_km
    covariance_1 = object_1.position_covariance_km2
    covariance_2 = object_2.position_covariance_km2
    probability = None
    if covariance_1 is not None and covariance_2 is not None:
        if miss_vector_km is None:
            raise ValueError("miss_vector_km is required when calculating collision probability.")
        combined_covariance = (
            np.asarray(covariance_1, dtype=float) + np.asarray(covariance_2, dtype=float)
        )
        probability = encounter_plane_probability(
            miss_vector_km, velocity, combined_covariance, hbr_km
        )

    return PairRiskResult(
        object_1=object_1.object_id,
        object_2=object_2.object_id,
        pair_type=pair_type,
        miss_distance_km=float(miss_distance_km),
        hard_body_radius_km=hbr_km,
        relative_speed_km_s=float(np.linalg.norm(velocity)),
        collision_probability=probability,
        risk_level=risk_level(probability),
        geometric_collision=geometric_collision,
    )
