"""Convert validated osculating Keplerian elements to Cartesian states.

This module performs a two-body element conversion only. It does not propagate
an orbit, interpret GP mean elements, or call SGP4.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import math

from orion_ahop.models import OrbitalState

EARTH_MU_KM3_S2 = 398600.4418


@dataclass(frozen=True)
class OsculatingKeplerianElements:
    """Earth-centred elliptic osculating elements at one explicit epoch."""

    semi_major_axis_km: float
    eccentricity: float
    inclination_deg: float
    raan_deg: float
    argument_of_perigee_deg: float
    mean_anomaly_deg: float
    epoch: datetime
    frame: str
    source: str
    object_id: str | None = None


def _finite(name: str, value: float) -> float:
    value = float(value)
    if not math.isfinite(value):
        raise ValueError(f"{name} must be finite.")
    return value


def solve_kepler_elliptic(mean_anomaly_rad: float, eccentricity: float,
                          tolerance: float = 1e-13,
                          max_iterations: int = 100) -> float:
    """Solve M = E - e sin(E) for an elliptic orbit using Newton iteration."""
    mean_anomaly_rad = _finite("mean_anomaly_rad", mean_anomaly_rad)
    eccentricity = _finite("eccentricity", eccentricity)
    if not 0.0 <= eccentricity < 1.0:
        raise ValueError("Elliptic eccentricity must satisfy 0 <= e < 1.")
    if tolerance <= 0 or max_iterations < 1:
        raise ValueError("A positive tolerance and max_iterations are required.")

    mean = math.fmod(mean_anomaly_rad, 2.0 * math.pi)
    estimate = mean if eccentricity < 0.8 else (math.pi if mean >= 0 else -math.pi)
    for _ in range(max_iterations):
        residual = estimate - eccentricity * math.sin(estimate) - mean
        derivative = 1.0 - eccentricity * math.cos(estimate)
        step = residual / derivative
        estimate -= step
        if abs(step) <= tolerance:
            return estimate
    raise ValueError("Kepler equation solver did not converge.")


def keplerian_to_cartesian(elements: OsculatingKeplerianElements,
                           mu_km3_s2: float = EARTH_MU_KM3_S2) -> OrbitalState:
    """Convert osculating elements into an inertial Cartesian state.

    Angles are in degrees; distance and velocity outputs are km and km/s.
    The supplied epoch and frame are retained unchanged. The caller is
    responsible for establishing that the source elements are osculating,
    Earth-centred, and expressed in the declared frame/time system.
    """
    if not isinstance(elements.epoch, datetime):
        raise TypeError("epoch must be a datetime.")
    if elements.epoch.tzinfo is None or elements.epoch.utcoffset() is None:
        raise ValueError("epoch must be timezone-aware.")
    frame = str(elements.frame).strip()
    source = str(elements.source).strip()
    if not frame:
        raise ValueError("An explicit reference frame is required.")
    if not source:
        raise ValueError("Source provenance is required.")

    a = _finite("semi_major_axis_km", elements.semi_major_axis_km)
    e = _finite("eccentricity", elements.eccentricity)
    inc = math.radians(_finite("inclination_deg", elements.inclination_deg))
    raan = math.radians(_finite("raan_deg", elements.raan_deg))
    argp = math.radians(_finite("argument_of_perigee_deg",
                               elements.argument_of_perigee_deg))
    mean = math.radians(_finite("mean_anomaly_deg", elements.mean_anomaly_deg))
    mu = _finite("mu_km3_s2", mu_km3_s2)

    if a <= 0:
        raise ValueError("Semi-major axis must be positive.")
    if not 0.0 <= e < 1.0:
        raise ValueError("Only elliptic osculating orbits (0 <= e < 1) are supported.")
    if not 0.0 <= inc <= math.pi:
        raise ValueError("Inclination must be between 0 and 180 degrees.")
    if mu <= 0:
        raise ValueError("Gravitational parameter must be positive.")

    eccentric_anomaly = solve_kepler_elliptic(mean, e)
    cos_e = math.cos(eccentric_anomaly)
    sin_e = math.sin(eccentric_anomaly)
    root = math.sqrt(1.0 - e * e)

    # Perifocal position and velocity for an elliptic two-body orbit.
    x_p = a * (cos_e - e)
    y_p = a * root * sin_e
    mean_motion = math.sqrt(mu / (a * a * a))
    denominator = 1.0 - e * cos_e
    vx_p = -a * mean_motion * sin_e / denominator
    vy_p = a * mean_motion * root * cos_e / denominator

    cO, sO = math.cos(raan), math.sin(raan)
    ci, si = math.cos(inc), math.sin(inc)
    cw, sw = math.cos(argp), math.sin(argp)

    # R3(RAAN) * R1(inclination) * R3(argument of perigee).
    r11 = cO * cw - sO * sw * ci
    r12 = -cO * sw - sO * cw * ci
    r21 = sO * cw + cO * sw * ci
    r22 = -sO * sw + cO * cw * ci
    r31 = sw * si
    r32 = cw * si

    position = (
        r11 * x_p + r12 * y_p,
        r21 * x_p + r22 * y_p,
        r31 * x_p + r32 * y_p,
    )
    velocity = (
        r11 * vx_p + r12 * vy_p,
        r21 * vx_p + r22 * vy_p,
        r31 * vx_p + r32 * vy_p,
    )

    return OrbitalState(
        epoch=elements.epoch,
        frame=frame,
        position_km=position,
        velocity_km_s=velocity,
        source_format="OSCULATING_KEPLERIAN",
        metadata={
            "source": source,
            "object_id": elements.object_id,
            "element_type": "osculating",
            "conversion": "two_body_keplerian_to_cartesian",
            "gravitational_parameter_km3_s2": mu,
            "sgp4_used": False,
            "covariance_available": False,
        },
    )
