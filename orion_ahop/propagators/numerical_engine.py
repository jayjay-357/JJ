"""Cowell Cartesian orbit propagation using adaptive DOP853 integration."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta

import numpy as np
from numpy.typing import NDArray
from scipy.integrate import solve_ivp

from orion_ahop.propagators.force_models import (
    ForceModelConfig,
    MU_EARTH_KM3_S2,
    total_acceleration,
)

StateArray = NDArray[np.float64]


@dataclass(frozen=True)
class PropagationResult:
    """Numerical propagation output; state columns are x,y,z,vx,vy,vz."""

    times_s: StateArray
    states_km_km_s: StateArray
    success: bool
    message: str
    function_evaluations: int
    method: str = "DOP853"


def _initial_state(position_km, velocity_km_s) -> StateArray:
    position = np.asarray(position_km, dtype=float)
    velocity = np.asarray(velocity_km_s, dtype=float)
    if position.shape != (3,) or velocity.shape != (3,):
        raise ValueError("Position and velocity must each contain exactly three values.")
    state = np.concatenate((position, velocity))
    if not np.isfinite(state).all():
        raise ValueError("Initial position and velocity must be finite.")
    if np.linalg.norm(position) <= 0:
        raise ValueError("Initial position magnitude must be positive.")
    return state


def _output_times(duration_s: float, output_step_s: float) -> StateArray:
    if duration_s == 0:
        return np.array([0.0])
    values = np.arange(0.0, duration_s, output_step_s, dtype=float)
    if values.size == 0 or not np.isclose(values[-1], duration_s):
        values = np.append(values, duration_s)
    else:
        values[-1] = duration_s
    return values


def propagate_cowell(
    position_km,
    velocity_km_s,
    epoch: datetime,
    duration_s: float,
    force_model: ForceModelConfig | None = None,
    *,
    output_step_s: float = 60.0,
    max_step_s: float = 300.0,
    relative_tolerance: float = 1e-10,
    position_absolute_tolerance_km: float = 1e-9,
    velocity_absolute_tolerance_km_s: float = 1e-12,
) -> PropagationResult:
    """Propagate an Earth-centred Cartesian state with Cowell's equations.

    DOP853 controls local integration error. It does not control force-model
    error, initial-state error, or uncertainty in physical parameters.
    """
    initial = _initial_state(position_km, velocity_km_s)
    if not isinstance(epoch, datetime):
        raise TypeError("epoch must be a datetime.")
    if epoch.tzinfo is None or epoch.utcoffset() is None:
        raise ValueError("epoch must be timezone-aware.")
    if not np.isfinite(duration_s) or duration_s < 0:
        raise ValueError("duration_s must be finite and non-negative.")
    if not np.isfinite(output_step_s) or output_step_s <= 0:
        raise ValueError("output_step_s must be finite and positive.")
    if not np.isfinite(max_step_s) or max_step_s <= 0:
        raise ValueError("max_step_s must be finite and positive.")
    tolerances = (
        relative_tolerance,
        position_absolute_tolerance_km,
        velocity_absolute_tolerance_km_s,
    )
    if any(not np.isfinite(value) or value <= 0 for value in tolerances):
        raise ValueError("All integration tolerances must be finite and positive.")

    config = force_model or ForceModelConfig()
    times = _output_times(float(duration_s), float(output_step_s))
    if duration_s == 0:
        return PropagationResult(
            times_s=times,
            states_km_km_s=initial.reshape(1, 6),
            success=True,
            message="Zero-duration propagation; initial state returned.",
            function_evaluations=0,
        )

    atol = np.array(
        [position_absolute_tolerance_km] * 3
        + [velocity_absolute_tolerance_km_s] * 3,
        dtype=float,
    )

    def equations(time_s: float, state: StateArray) -> StateArray:
        position = state[:3]
        velocity = state[3:]
        current_epoch = epoch + timedelta(seconds=float(time_s))
        acceleration = total_acceleration(current_epoch, position, velocity, config)
        return np.concatenate((velocity, acceleration))

    solution = solve_ivp(
        equations,
        (0.0, float(duration_s)),
        initial,
        method="DOP853",
        t_eval=times,
        rtol=float(relative_tolerance),
        atol=atol,
        max_step=float(max_step_s),
    )
    states = solution.y.T if solution.y.size else np.empty((0, 6), dtype=float)
    return PropagationResult(
        times_s=solution.t,
        states_km_km_s=states,
        success=bool(solution.success),
        message=str(solution.message),
        function_evaluations=int(solution.nfev),
    )


def propagate_two_body(
    position_km,
    velocity_km_s,
    epoch: datetime,
    duration_s: float,
    step_s: float = 10.0,
):
    """Backward-compatible two-body baseline API.

    New research code should call propagate_cowell with an explicit force model.
    """
    initial = _initial_state(position_km, velocity_km_s)
    if duration_s < 0 or step_s <= 0:
        raise ValueError("duration_s must be non-negative and step_s positive.")
    if duration_s == 0:
        return [(epoch, initial.copy())]

    def derivative(_time_s: float, state: StateArray) -> StateArray:
        r, v = state[:3], state[3:]
        radius = float(np.linalg.norm(r))
        if radius <= 0:
            raise ValueError("Position magnitude must be positive.")
        return np.concatenate((v, -MU_EARTH_KM3_S2 * r / radius**3))

    times = _output_times(float(duration_s), float(step_s))
    solution = solve_ivp(
        derivative, (0.0, float(duration_s)), initial, method="DOP853",
        t_eval=times, rtol=1e-11, atol=1e-12, max_step=float(step_s),
    )
    if not solution.success:
        raise RuntimeError(solution.message)
    return [
        (epoch + timedelta(seconds=float(t)), state.copy())
        for t, state in zip(solution.t, solution.y.T)
    ]
