from datetime import datetime, timezone

import numpy as np
import pytest
from astropy import units as u
from astropy.utils import iers

from orion_ahop.propagators.earth_orientation import (
    EarthOrientationProvider,
    NOMINAL_EARTH_SPIN_RAD_S,
)


class FixedIersTable:
    def __init__(self, dx=0.0, dy=0.0, status=iers.FROM_IERS_B):
        self.dx = dx
        self.dy = dy
        self.status = status

    def dcip_xy(self, _time, return_status=False):
        result = (self.dx * u.arcsec, self.dy * u.arcsec)
        if return_status:
            return (*result, self.status)
        return result


EPOCH = datetime(2026, 11, 3, tzinfo=timezone.utc)


def test_provider_returns_finite_unit_gcrs_pole_and_spin_vector():
    state = EarthOrientationProvider(table=FixedIersTable())(EPOCH)
    pole = np.asarray(state.pole_unit_vector_gcrs)
    omega = np.asarray(state.angular_velocity_vector_gcrs_rad_s)

    assert np.isfinite(pole).all()
    assert np.isfinite(omega).all()
    np.testing.assert_allclose(np.linalg.norm(pole), 1.0, atol=1e-14)
    np.testing.assert_allclose(
        np.linalg.norm(omega), NOMINAL_EARTH_SPIN_RAD_S, rtol=1e-14
    )
    assert pole[2] > 0.99


def test_provider_applies_iers_celestial_pole_offsets():
    baseline = EarthOrientationProvider(table=FixedIersTable())(EPOCH)
    corrected = EarthOrientationProvider(
        table=FixedIersTable(dx=0.2, dy=-0.1)
    )(EPOCH)
    assert corrected.pole_unit_vector_gcrs != baseline.pole_unit_vector_gcrs


def test_provider_rejects_naive_epoch():
    provider = EarthOrientationProvider(table=FixedIersTable())
    with pytest.raises(ValueError, match="timezone-aware"):
        provider(datetime(2026, 11, 3))


def test_provider_rejects_epoch_outside_iers_coverage():
    provider = EarthOrientationProvider(
        table=FixedIersTable(status=iers.TIME_BEYOND_IERS_RANGE)
    )
    with pytest.raises(ValueError, match="outside the available IERS"):
        provider(EPOCH)


def test_provider_rejects_invalid_spin_rate():
    with pytest.raises(ValueError, match="nominal_spin_rad_s"):
        EarthOrientationProvider(table=FixedIersTable(), nominal_spin_rad_s=0.0)
