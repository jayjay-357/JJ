"""Earth-orientation quantities for GCRS force models.

The provider uses the IAU 2006/2000A precession-nutation model with IERS
celestial-intermediate-pole corrections. The returned angular velocity is a
first-order rigid-Earth approximation: nominal spin rate directed along the
corrected celestial intermediate pole. Sub-daily variations, polar-motion
rates, and length-of-day corrections are not included.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

import erfa
import numpy as np
from astropy import units as u
from astropy.time import Time
from astropy.utils import iers

NOMINAL_EARTH_SPIN_RAD_S = 7.2921150e-5


@dataclass(frozen=True)
class EarthOrientationState:
    """Earth pole and nominal spin vector, both expressed in GCRS."""

    epoch: datetime
    pole_unit_vector_gcrs: tuple[float, float, float]
    angular_velocity_vector_gcrs_rad_s: tuple[float, float, float]
    cip_status: int


class EarthOrientationProvider:
    """Compute a GCRS Earth-pole/spin approximation using local IERS data.

    Network refresh is disabled while the local IERS-A table is opened.
    Dates outside the table's celestial-pole-correction coverage are rejected;
    no extrapolation is performed by this provider.
    """

    def __init__(self, table=None, *, nominal_spin_rad_s: float = NOMINAL_EARTH_SPIN_RAD_S):
        if not np.isfinite(nominal_spin_rad_s) or nominal_spin_rad_s <= 0:
            raise ValueError("nominal_spin_rad_s must be finite and positive.")
        self.nominal_spin_rad_s = float(nominal_spin_rad_s)
        if table is None:
            # Use the packaged/cache table only. Never initiate a network fetch.
            with iers.conf.set_temp("auto_download", False):
                table = iers.IERS_Auto.open()
        self._table = table

    def at(self, epoch: datetime) -> EarthOrientationState:
        """Return corrected CIP direction and nominal spin vector at epoch."""
        if not isinstance(epoch, datetime):
            raise TypeError("epoch must be a datetime.")
        if epoch.tzinfo is None or epoch.utcoffset() is None:
            raise ValueError("epoch must be timezone-aware.")

        time = Time(epoch, scale="utc")
        dx, dy, status = self._table.dcip_xy(time, return_status=True)
        status_value = int(np.asarray(status).item())
        if status_value in (iers.TIME_BEFORE_IERS_RANGE, iers.TIME_BEYOND_IERS_RANGE):
            raise ValueError(
                "Epoch is outside the available IERS celestial-pole-correction range; "
                "provide a suitable local IERS table."
            )

        # IAU 2006/2000A model gives the theoretical CIP coordinates in GCRS.
        x, y, _s = erfa.xys06a(time.tt.jd1, time.tt.jd2)
        x = float(x) + float(dx.to_value(u.rad))
        y = float(y) + float(dy.to_value(u.rad))
        radial_squared = x * x + y * y
        if not np.isfinite(radial_squared) or radial_squared >= 1.0:
            raise ValueError("Computed celestial intermediate pole is invalid.")

        pole = np.array([x, y, np.sqrt(1.0 - radial_squared)], dtype=float)
        pole /= np.linalg.norm(pole)
        omega = pole * self.nominal_spin_rad_s
        return EarthOrientationState(
            epoch=epoch,
            pole_unit_vector_gcrs=tuple(float(v) for v in pole),
            angular_velocity_vector_gcrs_rad_s=tuple(float(v) for v in omega),
            cip_status=status_value,
        )

    def __call__(self, epoch: datetime) -> EarthOrientationState:
        return self.at(epoch)
