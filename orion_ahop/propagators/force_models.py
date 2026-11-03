"""Configurable perturbing accelerations for Cowell propagation.

All states use an Earth-centred inertial frame and kilometres/seconds.
Atmospheric density is in kg/m^3; area-to-mass ratio is in m^2/kg.
The exponential atmosphere and cylindrical eclipse are research approximations,
not operational environment models.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Callable, Sequence

from orion_ahop.propagators.earth_orientation import EarthOrientationState

import numpy as np
from numpy.typing import NDArray

Vector3 = NDArray[np.float64]
PositionProvider = Callable[[datetime], Sequence[float]]

MU_EARTH_KM3_S2 = 398600.4418
EARTH_RADIUS_KM = 6378.1363
EARTH_J2 = 1.08262668e-3
EARTH_ROTATION_RAD_S = 7.2921150e-5
ASTRONOMICAL_UNIT_KM = 149597870.7
SOLAR_PRESSURE_N_M2_AT_1_AU = 4.56e-6


@dataclass(frozen=True)
class ExponentialAtmosphere:
    """Simple exponential density model, intended for sensitivity studies."""

    reference_altitude_km: float
    reference_density_kg_m3: float
    scale_height_km: float

    def __post_init__(self) -> None:
        if self.reference_altitude_km < 0:
            raise ValueError("reference_altitude_km must be non-negative.")
        if self.reference_density_kg_m3 <= 0:
            raise ValueError("reference_density_kg_m3 must be positive.")
        if self.scale_height_km <= 0:
            raise ValueError("scale_height_km must be positive.")

    def density(self, altitude_km: float) -> float:
        exponent = -(altitude_km - self.reference_altitude_km) / self.scale_height_km
        return float(self.reference_density_kg_m3 * np.exp(np.clip(exponent, -100.0, 100.0)))


@dataclass(frozen=True)
class ThirdBody:
    """Third-body gravity using a geocentric position provider in the same frame."""

    name: str
    gravitational_parameter_km3_s2: float
    position_provider: PositionProvider

    def __post_init__(self) -> None:
        if self.gravitational_parameter_km3_s2 <= 0:
            raise ValueError("Third-body gravitational parameter must be positive.")


@dataclass(frozen=True)
class ForceModelConfig:
    """Force-model switches and physical properties for one propagated object."""

    include_j2: bool = True
    atmosphere: ExponentialAtmosphere | None = None
    drag_coefficient: float | None = None
    area_to_mass_m2_kg: float | None = None
    include_solar_radiation_pressure: bool = False
    reflectivity_coefficient: float = 1.3
    sun_position_provider: PositionProvider | None = None
    third_bodies: tuple[ThirdBody, ...] = field(default_factory=tuple)
    earth_mu_km3_s2: float = MU_EARTH_KM3_S2
    earth_radius_km: float = EARTH_RADIUS_KM
    earth_j2: float = EARTH_J2
    earth_rotation_rad_s: float = EARTH_ROTATION_RAD_S
    earth_orientation_provider: Callable[[datetime], EarthOrientationState] | None = None

    def __post_init__(self) -> None:
        if self.earth_mu_km3_s2 <= 0 or self.earth_radius_km <= 0:
            raise ValueError("Earth gravitational parameter and radius must be positive.")
        if self.atmosphere is not None:
            if self.drag_coefficient is None or self.drag_coefficient <= 0:
                raise ValueError("A positive drag_coefficient is required when drag is enabled.")
            if self.area_to_mass_m2_kg is None or self.area_to_mass_m2_kg <= 0:
                raise ValueError("A positive area_to_mass_m2_kg is required when drag is enabled.")
        if self.include_solar_radiation_pressure:
            if self.sun_position_provider is None:
                raise ValueError("SRP requires a Sun position provider.")
            if self.area_to_mass_m2_kg is None or self.area_to_mass_m2_kg <= 0:
                raise ValueError("SRP requires a positive area_to_mass_m2_kg.")
            if self.reflectivity_coefficient <= 0:
                raise ValueError("reflectivity_coefficient must be positive.")


def _vector3(value: Sequence[float], label: str) -> Vector3:
    vector = np.asarray(value, dtype=float)
    if vector.shape != (3,) or not np.isfinite(vector).all():
        raise ValueError(f"{label} must contain three finite values.")
    return vector


def central_gravity(position_km: Vector3, mu_km3_s2: float = MU_EARTH_KM3_S2) -> Vector3:
    radius = float(np.linalg.norm(position_km))
    if radius <= 0:
        raise ValueError("Position magnitude must be positive.")
    return -mu_km3_s2 * position_km / radius**3


def j2_acceleration(
    position_km: Vector3,
    mu_km3_s2: float = MU_EARTH_KM3_S2,
    radius_km: float = EARTH_RADIUS_KM,
    j2: float = EARTH_J2,
    pole_unit_vector: Sequence[float] = (0.0, 0.0, 1.0),
) -> Vector3:
    """Earth J2 perturbation for a pole direction expressed in the state frame.

    The default +Z pole preserves the conventional Earth-equatorial inertial
    formulation. Supply the Earth pole in the spacecraft state frame when the
    state is expressed in another inertial frame, such as GCRS.
    """
    position = _vector3(position_km, "position_km")
    pole = _vector3(pole_unit_vector, "pole_unit_vector")
    pole_norm = float(np.linalg.norm(pole))
    if pole_norm <= 0:
        raise ValueError("pole_unit_vector must have non-zero magnitude.")
    pole = pole / pole_norm

    r_squared = float(np.dot(position, position))
    r = float(np.sqrt(r_squared))
    if r <= 0:
        raise ValueError("Position magnitude must be positive.")
    projection = float(np.dot(position, pole))
    factor = 1.5 * j2 * mu_km3_s2 * radius_km**2 / r**5
    return factor * (
        (5.0 * projection**2 / r_squared - 1.0) * position
        - 2.0 * projection * pole
    )


def atmospheric_drag_acceleration(
    epoch: datetime,
    position_km: Vector3,
    velocity_km_s: Vector3,
    atmosphere: ExponentialAtmosphere,
    drag_coefficient: float,
    area_to_mass_m2_kg: float,
    earth_radius_km: float = EARTH_RADIUS_KM,
    earth_rotation_rad_s: float = EARTH_ROTATION_RAD_S,
    earth_angular_velocity_vector_rad_s: Sequence[float] | None = None,
) -> Vector3:
    """Drag with a co-rotating atmosphere; returns km/s^2.

    If supplied, earth_angular_velocity_vector_rad_s must be expressed in the
    same inertial frame as position and velocity. The scalar rotation argument
    remains as a legacy +Z-axis approximation.
    """
    del epoch
    position = _vector3(position_km, "position_km")
    velocity = _vector3(velocity_km_s, "velocity_km_s")
    if earth_angular_velocity_vector_rad_s is None:
        angular_velocity = np.array([0.0, 0.0, earth_rotation_rad_s], dtype=float)
    else:
        angular_velocity = _vector3(
            earth_angular_velocity_vector_rad_s,
            "earth_angular_velocity_vector_rad_s",
        )
    altitude_km = float(np.linalg.norm(position)) - earth_radius_km
    rho = atmosphere.density(altitude_km)
    omega_cross_r = np.cross(angular_velocity, position)
    relative_velocity_m_s = (velocity - omega_cross_r) * 1000.0
    speed_m_s = float(np.linalg.norm(relative_velocity_m_s))
    acceleration_m_s2 = (
        -0.5 * rho * drag_coefficient * area_to_mass_m2_kg
        * speed_m_s * relative_velocity_m_s
    )
    return acceleration_m_s2 / 1000.0


def third_body_acceleration(
    position_km: Vector3,
    third_body_position_km: Vector3,
    mu_body_km3_s2: float,
) -> Vector3:
    """Differential third-body acceleration in an Earth-centred frame."""
    relative = third_body_position_km - position_km
    body_distance = float(np.linalg.norm(third_body_position_km))
    relative_distance = float(np.linalg.norm(relative))
    if body_distance <= 0 or relative_distance <= 0:
        raise ValueError("Third-body distances must be positive.")
    return mu_body_km3_s2 * (
        relative / relative_distance**3
        - third_body_position_km / body_distance**3
    )


def solar_radiation_pressure_acceleration(
    position_km: Vector3,
    sun_position_km: Vector3,
    area_to_mass_m2_kg: float,
    reflectivity_coefficient: float = 1.3,
    earth_radius_km: float = EARTH_RADIUS_KM,
) -> Vector3:
    """SRP acceleration with a simple cylindrical Earth-umbra shadow."""
    sun_distance = float(np.linalg.norm(sun_position_km))
    if sun_distance <= 0:
        raise ValueError("Sun position magnitude must be positive.")
    sun_unit = sun_position_km / sun_distance
    anti_sun_axis = -sun_unit
    along_axis = float(np.dot(position_km, anti_sun_axis))
    perpendicular = position_km - along_axis * anti_sun_axis
    if along_axis > 0 and float(np.linalg.norm(perpendicular)) < earth_radius_km:
        return np.zeros(3, dtype=float)

    away_from_sun = position_km - sun_position_km
    distance = float(np.linalg.norm(away_from_sun))
    if distance <= 0:
        raise ValueError("Spacecraft-to-Sun distance must be positive.")
    scale = (ASTRONOMICAL_UNIT_KM / distance) ** 2
    acceleration_m_s2 = (
        SOLAR_PRESSURE_N_M2_AT_1_AU * reflectivity_coefficient
        * area_to_mass_m2_kg * scale
    )
    return acceleration_m_s2 / 1000.0 * (away_from_sun / distance)


def total_acceleration(
    epoch: datetime,
    position_km: Sequence[float],
    velocity_km_s: Sequence[float],
    config: ForceModelConfig,
) -> Vector3:
    """Evaluate the configured acceleration sum in km/s^2."""
    r = _vector3(position_km, "position_km")
    v = _vector3(velocity_km_s, "velocity_km_s")
    acceleration = central_gravity(r, config.earth_mu_km3_s2)

    orientation = None
    if config.earth_orientation_provider is not None and (
        config.include_j2 or config.atmosphere is not None
    ):
        orientation = config.earth_orientation_provider(epoch)

    if config.include_j2:
        pole = (
            orientation.pole_unit_vector_gcrs
            if orientation is not None else (0.0, 0.0, 1.0)
        )
        acceleration += j2_acceleration(
            r, config.earth_mu_km3_s2, config.earth_radius_km,
            config.earth_j2, pole_unit_vector=pole,
        )
    if config.atmosphere is not None:
        acceleration += atmospheric_drag_acceleration(
            epoch, r, v, config.atmosphere, float(config.drag_coefficient),
            float(config.area_to_mass_m2_kg), config.earth_radius_km,
            config.earth_rotation_rad_s,
            earth_angular_velocity_vector_rad_s=(
                orientation.angular_velocity_vector_gcrs_rad_s
                if orientation is not None else None
            ),
        )
    if config.include_solar_radiation_pressure:
        sun_position = _vector3(config.sun_position_provider(epoch), "sun_position_km")
        acceleration += solar_radiation_pressure_acceleration(
            r, sun_position, float(config.area_to_mass_m2_kg),
            config.reflectivity_coefficient, config.earth_radius_km,
        )
    for body in config.third_bodies:
        body_position = _vector3(body.position_provider(epoch), f"{body.name}_position_km")
        acceleration += third_body_acceleration(
            r, body_position, body.gravitational_parameter_km3_s2
        )
    return acceleration
