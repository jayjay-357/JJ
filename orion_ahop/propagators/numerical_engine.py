"""Educational two-body RK4 integrator; not a high-fidelity propagator."""
from datetime import datetime, timedelta
import numpy as np

MU_EARTH_KM3_S2 = 398600.4418

def _derivative(state: np.ndarray) -> np.ndarray:
    r, v = state[:3], state[3:]
    radius = float(np.linalg.norm(r))
    if radius <= 0:
        raise ValueError("Position magnitude must be positive.")
    return np.concatenate((v, -MU_EARTH_KM3_S2 * r / radius**3))

def propagate_two_body(position_km, velocity_km_s, epoch: datetime,
                       duration_s: float, step_s: float = 10.0):
    if duration_s < 0 or step_s <= 0:
        raise ValueError("duration_s must be non-negative and step_s positive.")
    state = np.array((*position_km, *velocity_km_s), dtype=float)
    result = [(epoch, state.copy())]
    elapsed = 0.0
    while elapsed < duration_s:
        h = min(step_s, duration_s - elapsed)
        k1 = _derivative(state)
        k2 = _derivative(state + h*k1/2)
        k3 = _derivative(state + h*k2/2)
        k4 = _derivative(state + h*k3)
        state = state + h*(k1 + 2*k2 + 2*k3 + k4)/6
        elapsed += h
        result.append((epoch + timedelta(seconds=elapsed), state.copy()))
    return result
