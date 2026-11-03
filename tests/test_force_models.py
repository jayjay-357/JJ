from datetime import datetime, timezone

import numpy as np
import pytest

from orion_ahop.propagators.force_models import (
    ExponentialAtmosphere,
    ForceModelConfig,
    ThirdBody,
    central_gravity,
    j2_acceleration,
    atmospheric_drag_acceleration,
    third_body_acceleration,
    solar_radiation_pressure_acceleration,
    total_acceleration,
)

EPOCH = datetime(2026, 1, 1, tzinfo=timezone.utc)


def test_central_gravity_points_toward_earth_center():
    acceleration = central_gravity(np.array([7000.0, 0.0, 0.0]))
    assert acceleration[0] < 0
    assert acceleration[1] == 0
    assert acceleration[2] == 0


def test_j2_acceleration_is_finite_and_nonzero():
    acceleration = j2_acceleration(np.array([7000.0, 0.0, 1000.0]))
    assert np.isfinite(acceleration).all()
    assert np.linalg.norm(acceleration) > 0


def test_drag_opposes_atmosphere_relative_velocity():
    atmosphere = ExponentialAtmosphere(400.0, 4e-12, 60.0)
    acceleration = atmospheric_drag_acceleration(
        EPOCH, np.array([6778.1363, 0.0, 0.0]),
        np.array([0.0, 7.7, 0.0]), atmosphere, 2.2, 0.01,
    )
    assert acceleration[1] < 0


def test_third_body_differential_acceleration_is_finite():
    acceleration = third_body_acceleration(
        np.array([7000.0, 0.0, 0.0]),
        np.array([149597870.7, 0.0, 0.0]),
        1.32712440018e11,
    )
    assert np.isfinite(acceleration).all()


def test_srp_points_approximately_away_from_sun_outside_shadow():
    acceleration = solar_radiation_pressure_acceleration(
        np.array([7000.0, 0.0, 0.0]),
        np.array([149597870.7, 0.0, 0.0]),
        0.01,
    )
    assert acceleration[0] < 0


def test_srp_is_zero_in_cylindrical_earth_shadow():
    acceleration = solar_radiation_pressure_acceleration(
        np.array([-7000.0, 0.0, 0.0]),
        np.array([149597870.7, 0.0, 0.0]),
        0.01,
    )
    np.testing.assert_allclose(acceleration, np.zeros(3))


def test_force_model_requires_physical_inputs_for_drag_and_srp():
    with pytest.raises(ValueError):
        ForceModelConfig(atmosphere=ExponentialAtmosphere(400, 4e-12, 60))
    with pytest.raises(ValueError):
        ForceModelConfig(include_solar_radiation_pressure=True)


def test_total_acceleration_includes_third_body_provider():
    body = ThirdBody("test", 1e5, lambda _epoch: (1e6, 0.0, 0.0))
    acceleration = total_acceleration(
        EPOCH, (7000.0, 0.0, 0.0), (0.0, 7.5, 0.0),
        ForceModelConfig(include_j2=False, third_bodies=(body,)),
    )
    assert np.isfinite(acceleration).all()
