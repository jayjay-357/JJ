from datetime import datetime, timezone

import numpy as np
import pytest

from orion_ahop.models import OrbitalState
from orion_ahop.propagators.frame_transforms import teme_to_gcrs


EPOCH = datetime(2024, 1, 1, tzinfo=timezone.utc)


def make_state(**overrides):
    values = {
        "epoch": EPOCH,
        "frame": "TEME",
        "position_km": (-4610.0, 5010.0, -0.001),
        "velocity_km_s": (-3.6, -3.3, 5.9),
    }
    values.update(overrides)
    return OrbitalState(**values)


def test_teme_to_gcrs_transforms_position_and_velocity():
    result = teme_to_gcrs(make_state())
    assert result.frame == "GCRS"
    assert result.epoch == EPOCH
    assert result.source_format == "OPM"
    assert result.metadata["frame_transform"] == "TEME_TO_GCRS"
    assert np.isfinite(result.position_km).all()
    assert np.isfinite(result.velocity_km_s).all()
    assert np.linalg.norm(result.position_km) == pytest.approx(6808.0, abs=2.0)
    assert np.linalg.norm(result.velocity_km_s) == pytest.approx(7.67, abs=0.1)


def test_teme_to_gcrs_rejects_non_teme_frame():
    with pytest.raises(ValueError, match="TEME input"):
        teme_to_gcrs(make_state(frame="GCRS"))


def test_teme_to_gcrs_rejects_naive_epoch():
    with pytest.raises(ValueError, match="timezone-aware"):
        teme_to_gcrs(make_state(epoch=datetime(2024, 1, 1)))


def test_teme_to_gcrs_rejects_covariance_until_jacobian_is_implemented():
    state = make_state(covariance=np.eye(6).tolist())
    with pytest.raises(NotImplementedError, match="6x6 Jacobian"):
        teme_to_gcrs(state)


def test_teme_to_gcrs_rejects_nonfinite_state():
    with pytest.raises(ValueError, match="finite"):
        teme_to_gcrs(make_state(position_km=(np.nan, 0.0, 0.0)))
