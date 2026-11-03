"""Pair-aware conjunction screening and collision-risk assessment."""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .collision_risk import PairRiskResult, SpaceObject, assess_pair_risk, pair_type_for
from .conjunction import Conjunction, screen_all_pairs


@dataclass(frozen=True)
class PairConjunctionAssessment:
    conjunction: Conjunction
    risk: PairRiskResult


def assess_supported_pairs(
    times_s,
    trajectories: dict[str, dict[str, np.ndarray]],
    objects: dict[str, SpaceObject],
    screening_distance_km: float,
) -> list[PairConjunctionAssessment]:
    """Screen and assess debris-debris, satellite-debris, and rocket-debris pairs.

    Every trajectory must contain synchronized ``positions_km`` and
    ``velocities_km_s`` arrays. Each object descriptor supplies its class,
    hard-body radius, and optional TCA position covariance.
    """
    missing = sorted(set(trajectories) - set(objects))
    if missing:
        raise ValueError(f"Missing object metadata for: {', '.join(missing)}")

    times = np.asarray(times_s, dtype=float)
    conjunctions = screen_all_pairs(times, trajectories, screening_distance_km)
    assessments: list[PairConjunctionAssessment] = []

    for conjunction in conjunctions:
        object_1 = objects[conjunction.object_1]
        object_2 = objects[conjunction.object_2]
        try:
            pair_type_for(object_1.object_type, object_2.object_type)
        except ValueError:
            continue

        a = trajectories[conjunction.object_1]
        b = trajectories[conjunction.object_2]
        index = conjunction.sample_index
        dt = conjunction.tca_offset_s - float(times[index])
        relative_position = (
            np.asarray(a["positions_km"], dtype=float)[index]
            - np.asarray(b["positions_km"], dtype=float)[index]
            + (
                np.asarray(a["velocities_km_s"], dtype=float)[index]
                - np.asarray(b["velocities_km_s"], dtype=float)[index]
            ) * dt
        )
        relative_velocity = (
            np.asarray(a["velocities_km_s"], dtype=float)[index]
            - np.asarray(b["velocities_km_s"], dtype=float)[index]
        )
        risk = assess_pair_risk(
            object_1,
            object_2,
            conjunction.miss_distance_km,
            relative_velocity,
            relative_position,
        )
        assessments.append(PairConjunctionAssessment(conjunction, risk))

    return sorted(assessments, key=lambda item: item.conjunction.tca_offset_s)
