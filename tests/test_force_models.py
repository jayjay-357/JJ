from datetime import datetime, timezone

import numpy as np
import pytest

from orion_ahop.propagators.earth_orientation import EarthOrientationState

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



def test_j2_acceleration_is_rotation_covariant_with_rotated_pole():
    position = np.array([6800.0, 1200.0, -900.0])
    angle = 0.73
    rotation = np.array([
        [np.cos(angle), 0.0, np.sin(angle)],
        [0.0, 1.0, 0.0],
        [-np.sin(angle), 0.0, np.cos(angle)],
    ])
    original = j2_acceleration(position)
    rotated = j2_acceleration(
        rotation @ position,
        pole_unit_vector=rotation @ np.array([0.0, 0.0, 1.0]),
    )
    np.testing.assert_allclose(rotated, rotation @ original, rtol=1e-12, atol=1e-15)


def test_j2_rejects_zero_pole_vector():
    with pytest.raises(ValueError, match="non-zero"):
        j2_acceleration(np.array([7000.0, 0.0, 0.0]), pole_unit_vector=(0, 0, 0))


def test_j2_rejects_nonfinite_pole_vector():
    with pytest.raises(ValueError, match="finite"):
        j2_acceleration(
            np.array([7000.0, 0.0, 0.0]),
            pole_unit_vector=(0.0, np.nan, 1.0),
        )


def test_drag_acceleration_is_rotation_covariant_with_rotated_earth_spin():
    atmosphere = ExponentialAtmosphere(400.0, 4e-12, 60.0)
    position = np.array([6778.1363, 200.0, -100.0])
    velocity = np.array([-0.2, 7.6, 0.4])
    omega = np.array([1.0e-6, -2.0e-6, 7.29e-5])
    angle = 0.61
    rotation = np.array([
        [np.cos(angle), 0.0, np.sin(angle)],
        [0.0, 1.0, 0.0],
        [-np.sin(angle), 0.0, np.cos(angle)],
    ])
    original = atmospheric_drag_acceleration(
        EPOCH, position, velocity, atmosphere, 2.2, 0.01,
        earth_angular_velocity_vector_rad_s=omega,
    )
    rotated = atmospheric_drag_acceleration(
        EPOCH, rotation @ position, rotation @ velocity,
        atmosphere, 2.2, 0.01,
        earth_angular_velocity_vector_rad_s=rotation @ omega,
    )
    np.testing.assert_allclose(rotated, rotation @ original, rtol=1e-12, atol=1e-15)


def test_total_acceleration_uses_injected_gcrs_earth_orientation():
    pole = (0.01, -0.02, 0.99975)
    omega = (1.0e-6, -2.0e-6, 7.289e-5)
    calls = []

    def provider(epoch):
        calls.append(epoch)
        return EarthOrientationState(EPOCH, pole, omega, 0)

    atmosphere = ExponentialAtmosphere(400.0, 4e-12, 60.0)
    config = ForceModelConfig(
        include_j2=True,
        atmosphere=atmosphere,
        drag_coefficient=2.2,
        area_to_mass_m2_kg=0.01,
        earth_orientation_provider=provider,
    )
    position = np.array([6778.1363, 200.0, -100.0])
    velocity = np.array([-0.2, 7.6, 0.4])
    actual = total_acceleration(EPOCH, position, velocity, config)
    expected = (
        central_gravity(position)
        + j2_acceleration(position, pole_unit_vector=pole)
        + atmospheric_drag_acceleration(
            EPOCH, position, velocity, atmosphere, 2.2, 0.01,
            earth_angular_velocity_vector_rad_s=omega,
        )
    )
    np.testing.assert_allclose(actual, expected, rtol=1e-13, atol=1e-16)
    assert calls == [EPOCH]


def test_force_model_rejects_non_callable_earth_orientation_provider():
    with pytest.raises(ValueError, match="must be callable"):
        ForceModelConfig(earth_orientation_provider=object())
