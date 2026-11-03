"""Synchronized trajectory screening and linear TCA refinement.

Inputs must already be propagated into the same inertial frame, time grid,
and units (km and seconds). This module performs geometric screening; it
does not calculate collision probability or replace an operational CDM tool.
"""
from __future__ import annotations
from dataclasses import dataclass
from itertools import combinations
import numpy as np


@dataclass(frozen=True)
class Conjunction:
    object_1: str
    object_2: str
    sample_index: int
    tca_offset_s: float
    miss_distance_km: float
    relative_speed_km_s: float
    screening_distance_km: float


def refine_linear_tca(relative_position_km, relative_velocity_km_s,
                      max_offset_s: float) -> tuple[float, float]:
    """Return bounded linearized TCA offset and miss distance."""
    r = np.asarray(relative_position_km, dtype=float)
    v = np.asarray(relative_velocity_km_s, dtype=float)
    if r.shape != (3,) or v.shape != (3,):
        raise ValueError("Relative position and velocity must each have 3 components.")
    if max_offset_s < 0:
        raise ValueError("max_offset_s must be non-negative.")
    speed_sq = float(np.dot(v, v))
    dt = 0.0 if speed_sq == 0 else -float(np.dot(r, v)) / speed_sq
    dt = float(np.clip(dt, -max_offset_s, max_offset_s))
    miss = float(np.linalg.norm(r + v * dt))
    return dt, miss


def screen_trajectory_pair(object_1: str, object_2: str, times_s,
                           positions_1_km, velocities_1_km_s,
                           positions_2_km, velocities_2_km_s,
                           screening_distance_km: float) -> Conjunction | None:
    """Screen two synchronized trajectories and refine their closest sample."""
    times = np.asarray(times_s, dtype=float)
    r1, r2 = np.asarray(positions_1_km, dtype=float), np.asarray(positions_2_km, dtype=float)
    v1, v2 = np.asarray(velocities_1_km_s, dtype=float), np.asarray(velocities_2_km_s, dtype=float)
    if screening_distance_km <= 0:
        raise ValueError("screening_distance_km must be positive.")
    if times.ndim != 1 or len(times) < 2 or np.any(np.diff(times) <= 0):
        raise ValueError("times_s must contain at least two strictly increasing samples.")
    expected = (len(times), 3)
    if any(a.shape != expected for a in (r1, r2, v1, v2)):
        raise ValueError(f"All trajectory arrays must have shape {expected}.")
    if not all(np.isfinite(a).all() for a in (times, r1, r2, v1, v2)):
        raise ValueError("Trajectory arrays must contain only finite values.")

    relative_r, relative_v = r1 - r2, v1 - v2
    distances = np.linalg.norm(relative_r, axis=1)
    index = int(np.argmin(distances))
    if distances[index] > screening_distance_km:
        return None
    # Use half the local interval as a conservative linear-refinement bound.
    left = times[index] - times[index - 1] if index > 0 else times[1] - times[0]
    right = times[index + 1] - times[index] if index < len(times) - 1 else times[-1] - times[-2]
    bound = 0.5 * min(left, right)
    dt, miss = refine_linear_tca(relative_r[index], relative_v[index], bound)
    return Conjunction(
        object_1, object_2, index, float(times[index] + dt), miss,
        float(np.linalg.norm(relative_v[index])), float(screening_distance_km)
    )


def screen_all_pairs(times_s, trajectories: dict[str, dict[str, np.ndarray]],
                     screening_distance_km: float) -> list[Conjunction]:
    """Screen every unique object pair.

    Each trajectory entry contains positions_km and velocities_km_s arrays.
    All objects must share the same time grid and reference frame.
    """
    results = []
    for name_a, name_b in combinations(sorted(trajectories), 2):
        a, b = trajectories[name_a], trajectories[name_b]
        result = screen_trajectory_pair(
            name_a, name_b, times_s, a["positions_km"], a["velocities_km_s"],
            b["positions_km"], b["velocities_km_s"], screening_distance_km
        )
        if result is not None:
            results.append(result)
    return sorted(results, key=lambda item: item.tca_offset_s)
