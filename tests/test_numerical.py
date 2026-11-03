from datetime import datetime, timezone
import numpy as np
from orion_ahop.propagators.numerical_engine import propagate_two_body

def test_two_body_integrator_returns_initial_and_final_states():
    epoch = datetime(2026, 1, 1, tzinfo=timezone.utc)
    states = propagate_two_body((7000, 0, 0), (0, 7.5, 0), epoch, 20, 10)
    assert len(states) == 3
    assert states[0][0] == epoch
    assert states[-1][0] > epoch
    assert np.isfinite(states[-1][1]).all()
