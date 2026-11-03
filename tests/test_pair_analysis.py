import numpy as np

from orion_ahop.collision_risk import ObjectType, SpaceObject
from orion_ahop.pair_analysis import assess_supported_pairs


def test_supported_pair_analysis_includes_debris_satellite_and_rocket_pairs():
    times = np.array([0.0, 10.0, 20.0])
    zero_v = np.zeros((3, 3))
    trajectories = {
        "D1": {"positions_km": np.zeros((3, 3)), "velocities_km_s": zero_v},
        "D2": {"positions_km": np.tile([0.5, 0.0, 0.0], (3, 1)), "velocities_km_s": zero_v},
        "S": {"positions_km": np.tile([2.0, 0.0, 0.0], (3, 1)), "velocities_km_s": zero_v},
        "R": {"positions_km": np.tile([3.0, 0.0, 0.0], (3, 1)), "velocities_km_s": zero_v},
    }
    objects = {
        "D1": SpaceObject("D1", ObjectType.DEBRIS, 1.0),
        "D2": SpaceObject("D2", ObjectType.DEBRIS, 1.0),
        "S": SpaceObject("S", ObjectType.SATELLITE, 1.0),
        "R": SpaceObject("R", ObjectType.ROCKET, 1.0),
    }

    results = assess_supported_pairs(times, trajectories, objects, 5.0)

    pair_types = {result.risk.pair_type.value for result in results}
    assert pair_types == {"debris-debris", "satellite-debris", "rocket-debris"}
    # One debris-debris pair, two satellite-debris pairs, and two rocket-debris pairs.
    assert len(results) == 5

    # Mixed pairs are reported from the debris threat toward the protected object.
    for result in results:
        if result.risk.pair_type.value != "debris-debris":
            assert objects[result.risk.object_1].object_type is ObjectType.DEBRIS
            assert objects[result.risk.object_2].object_type is not ObjectType.DEBRIS
