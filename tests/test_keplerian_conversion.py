from datetime import datetime, timezone
import math

import pytest

from orion_ahop.ingestion.keplerian import (
    OsculatingKeplerianElements,
    keplerian_to_cartesian,
    solve_kepler_elliptic,
)


def _elements(**overrides):
    values = dict(
        semi_major_axis_km=7000.0,
        eccentricity=0.0,
        inclination_deg=0.0,
        raan_deg=0.0,
        argument_of_perigee_deg=0.0,
        mean_anomaly_deg=0.0,
        epoch=datetime(2026, 1, 1, tzinfo=timezone.utc),
        frame="EME2000",
        source="test fixture (not observational data)",
        object_id="TEST-001",
    )
    values.update(overrides)
    return OsculatingKeplerianElements(**values)


def test_circular_equatorial_conversion():
    state = keplerian_to_cartesian(_elements())
    assert state.position_km == pytest.approx((7000.0, 0.0, 0.0), abs=1e-9)
    expected_speed = math.sqrt(398600.4418 / 7000.0)
    assert state.velocity_km_s == pytest.approx((0.0, expected_speed, 0.0), abs=1e-12)
    assert state.frame == "EME2000"
    assert state.metadata["sgp4_used"] is False
    assert state.metadata["element_type"] == "osculating"


def test_kepler_solver_satisfies_equation():
    mean = math.radians(125.0)
    eccentricity = 0.7
    eccentric = solve_kepler_elliptic(mean, eccentricity)
    assert eccentric - eccentricity * math.sin(eccentric) == pytest.approx(mean)


def test_elliptical_inclined_state_has_finite_components():
    state = keplerian_to_cartesian(_elements(
        eccentricity=0.1,
        inclination_deg=51.6,
        raan_deg=120.0,
        argument_of_perigee_deg=45.0,
        mean_anomaly_deg=210.0,
    ))
    assert all(math.isfinite(value) for value in state.position_km + state.velocity_km_s)
    assert math.sqrt(sum(x * x for x in state.position_km)) > 0
    assert math.sqrt(sum(v * v for v in state.velocity_km_s)) > 0


@pytest.mark.parametrize("eccentricity", [-0.1, 1.0, 1.2])
def test_rejects_non_elliptic_eccentricity(eccentricity):
    with pytest.raises(ValueError):
        keplerian_to_cartesian(_elements(eccentricity=eccentricity))


def test_requires_timezone_aware_epoch():
    with pytest.raises(ValueError, match="timezone-aware"):
        keplerian_to_cartesian(_elements(epoch=datetime(2026, 1, 1)))


def test_requires_explicit_frame():
    with pytest.raises(ValueError, match="reference frame"):
        keplerian_to_cartesian(_elements(frame="  "))
