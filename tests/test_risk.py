import numpy as np
from orion_ahop.qarc.risk import gaussian_disk_event, monte_carlo_probability

def test_monte_carlo_reproducible_for_fixed_seed():
    event = gaussian_disk_event((0.0, 0.0), np.eye(2) * 0.01, 0.5)
    first = monte_carlo_probability(event, 500, seed=7)
    second = monte_carlo_probability(event, 500, seed=7)
    assert first == second
    assert 0 <= first["probability"] <= 1
