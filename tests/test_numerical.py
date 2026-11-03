from datetime import datetime, timezone

import numpy as np
import pytest

from orion_ahop.propagators.force_models import ForceModelConfig, MU_EARTH_KM3_S2
from orion_ahop.propagators.numerical_engine import propagate_cowell, propagate_two_body


EPOCH = datetime(2026, 1, 1, tzinfo=timezone.utc)


def specific_energy(state):
    r = state[:3]
    v = state[3:]
    return 0.5 * float(np.dot(v, v)) - MU_EARTH_KM3_S2 / float(np.linalg.norm(r))


def test_cowell_dop853_returns_initial_and_final_states():
    result = propagate_cowell(
        (7000, 0, 0), (0, 7.5, 0), EPOCH, 120,
        force_model=ForceModelConfig(include_j2=False),
        output_step_s=60, max_step_s=30,
    )
    assert result.success
    assert result.method == "DOP853"
    assert result.states_km_km_s.shape == (3, 6)
    assert result.times_s[0] == 0
    assert result.times_s[-1] == 120
    assert np.isfinite(result.states_km_km_s).all()


def test_two_body_energy_is_conserved_to_numerical_tolerance():
    initial = np.array([7000.0, 0.0, 0.0, 0.0, 7.54605329, 0.0])
    result = propagate_cowell(
        initial[:3], initial[3:], EPOCH, 5400,
        force_model=ForceModelConfig(include_j2=False),
        output_step_s=300, max_step_s=120,
        relative_tolerance=1e-12,
        position_absolute_tolerance_km=1e-11,
        velocity_absolute_tolerance_km_s=1e-14,
    )
    assert result.success
    energy_error = abs(specific_energy(result.states_km_km_s[-1]) - specific_energy(initial))
    assert energy_error < 1e-9


def test_zero_duration_returns_initial_state():
    result = propagate_cowell((7000, 0, 0), (0, 7.5, 0), EPOCH, 0)
    assert result.success
    assert result.states_km_km_s.shape == (1, 6)
    np.testing.assert_allclose(result.states_km_km_s[0], [7000, 0, 0, 0, 7.5, 0])


def test_invalid_inputs_are_rejected():
    with pytest.raises(ValueError):
        propagate_cowell((0, 0, 0), (0, 7.5, 0), EPOCH, 100)
    with pytest.raises(ValueError):
        propagate_cowell((7000, 0, 0), (0, 7.5, 0), EPOCH, 100, max_step_s=0)


def test_legacy_two_body_wrapper_still_returns_epoch_state_pairs():
    result = propagate_two_body((7000, 0, 0), (0, 7.5, 0), EPOCH, 20, 10)
    assert len(result) == 3
    assert result[0][0] == EPOCH
    assert result[-1][0] > EPOCH
    assert np.isfinite(result[-1][1]).all()



def test_drag_force_reduces_specific_orbital_energy():
    from orion_ahop.propagators.force_models import ExponentialAtmosphere

    radius_km = 6378.1363 + 400.0
    circular_speed = (MU_EARTH_KM3_S2 / radius_km) ** 0.5
    initial = np.array([radius_km, 0.0, 0.0, 0.0, circular_speed, 0.0])
    model = ForceModelConfig(
        include_j2=False,
        atmosphere=ExponentialAtmosphere(400.0, 4e-12, 60.0),
        drag_coefficient=2.2,
        area_to_mass_m2_kg=0.01,
    )
    result = propagate_cowell(
        initial[:3], initial[3:], EPOCH, 600.0,
        force_model=model, output_step_s=600.0, max_step_s=10.0,
    )
    assert result.success
    assert specific_energy(result.states_km_km_s[-1]) < specific_energy(initial)
