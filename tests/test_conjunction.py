import numpy as np
import pytest
from orion_ahop.conjunction import refine_linear_tca, screen_trajectory_pair, screen_all_pairs

def test_linear_tca_refinement():
    dt, miss = refine_linear_tca((1.0, 2.0, 0.0), (-1.0, 0.0, 0.0), 5.0)
    assert dt == pytest.approx(1.0)
    assert miss == pytest.approx(2.0)

def test_pair_screening_returns_candidate():
    times = np.array([0.0, 10.0, 20.0])
    r1 = np.array([[0., 0., 0.], [0., 0., 0.], [0., 0., 0.]])
    r2 = np.array([[10., 2., 0.], [2., 2., 0.], [10., 2., 0.]])
    v1 = np.zeros((3, 3))
    v2 = np.tile([-.8, 0., 0.], (3, 1))
    result = screen_trajectory_pair("A", "B", times, r1, v1, r2, v2, 5.0)
    assert result is not None
    assert result.miss_distance_km == pytest.approx(2.0)

def test_pair_screening_rejects_far_pair():
    times = np.array([0.0, 10.0])
    r1 = np.zeros((2, 3))
    r2 = np.tile([100., 0., 0.], (2, 1))
    v = np.zeros((2, 3))
    assert screen_trajectory_pair("A", "B", times, r1, v, r2, v, 5.0) is None

def test_all_pairs_unique():
    times = np.array([0.0, 1.0])
    z = np.zeros((2, 3))
    trajectories = {
        "A": {"positions_km": z, "velocities_km_s": z},
        "B": {"positions_km": z + [1, 0, 0], "velocities_km_s": z},
        "C": {"positions_km": z + [2, 0, 0], "velocities_km_s": z},
    }
    assert len(screen_all_pairs(times, trajectories, 3.0)) == 3
