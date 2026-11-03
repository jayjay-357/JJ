import numpy as np

from orion_ahop.collision_risk import ObjectType, SpaceObject
from orion_ahop.pair_analysis import assess_supported_pairs


def test_supported_pair_analysis_includes_debris_satellite_and_rocket_pairs():
    times = np.array([0.0, 10.0, 20.0])
    zero_v = np.zeros((3, 3))
    trajectories = {
        "D": {"positions_km": np.zeros((3, 3)), "velocities_km_s": zero_v},
        "S": {"positions_km": np.tile([2.0, 0.0, 0.0], (3, 1)), "velocities_km_s": zero_v},
        "R": {"positions_km": np.tile([3.0, 0.0, 0.0], (3, 1)), "velocities_km_s": zero_v},
    }
    objects = {
        "D": SpaceObject("D", ObjectType.DEBRIS, 1.0),
        "S": SpaceObject("S", ObjectType.SATELLITE, 1.0),
        "R": SpaceObject("R", ObjectType.ROCKET, 1.0),
    }
    results = assess_supported_pairs(times, trajectories, objects, 5.0)
    pair_types = {result.risk.pair_type.value for result in results}
    assert pair_types == {"debris-debris", "satellite-debris", "rocket-debris"}
    assert len(results) == 3
