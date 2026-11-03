"""Reference-frame transformations used by the orbital propagators."""
from __future__ import annotations

from datetime import timezone

import numpy as np
from astropy import units as u
from astropy.coordinates import CartesianDifferential, CartesianRepresentation, GCRS, TEME
from astropy.time import Time
from astropy.utils import iers

from orion_ahop.models import OrbitalState


def teme_to_gcrs(state: OrbitalState) -> OrbitalState:
    """Transform a TEME Cartesian state to GCRS at its stated UTC epoch.

    Position and velocity are transformed together using Astropy's TEME
    implementation. Covariance is rejected because a full 6x6 Jacobian
    transformation is not implemented here.
    """
    if not isinstance(state, OrbitalState):
        raise TypeError("state must be an OrbitalState.")
    if state.frame.strip().upper() != "TEME":
        raise ValueError("teme_to_gcrs requires a TEME input state.")
    if state.epoch.tzinfo is None or state.epoch.utcoffset() is None:
        raise ValueError("state epoch must be timezone-aware.")
    if state.covariance is not None:
        raise NotImplementedError(
            "TEME-to-GCRS covariance transformation requires a 6x6 Jacobian."
        )

    position = np.asarray(state.position_km, dtype=float)
    velocity = np.asarray(state.velocity_km_s, dtype=float)
    if position.shape != (3,) or velocity.shape != (3,):
        raise ValueError("Position and velocity must each contain three values.")
    if not np.isfinite(position).all() or not np.isfinite(velocity).all():
        raise ValueError("Position and velocity must be finite.")
    if np.linalg.norm(position) <= 0:
        raise ValueError("Position magnitude must be positive.")

    epoch_utc = state.epoch.astimezone(timezone.utc)
    obstime = Time(epoch_utc, scale="utc")
    representation = CartesianRepresentation(
        position * u.km,
        differentials=CartesianDifferential(velocity * u.km / u.s),
    )
    teme_state = TEME(representation, obstime=obstime)

    # Prevent a coordinate transform from silently downloading EOP data and
    # reject epochs outside the locally available UT1/polar-motion coverage.
    with iers.conf.set_temp("auto_download", False):
        eop_table = iers.earth_orientation_table.get()
        _ut1, ut1_status = eop_table.ut1_utc(obstime, return_status=True)
        _pm_x, _pm_y, pm_status = eop_table.pm_xy(obstime, return_status=True)
        invalid_statuses = (
            iers.TIME_BEFORE_IERS_RANGE,
            iers.TIME_BEYOND_IERS_RANGE,
        )
        ut1_status_value = int(np.asarray(ut1_status).item())
        pm_status_value = int(np.asarray(pm_status).item())
        if ut1_status_value in invalid_statuses or pm_status_value in invalid_statuses:
            raise ValueError(
                "Epoch is outside locally available IERS UT1/polar-motion coverage; "
                "provide a suitable local IERS table."
            )
        gcrs_state = teme_state.transform_to(GCRS(obstime=obstime))

    transformed_position = gcrs_state.cartesian.xyz.to_value(u.km)
    transformed_velocity = gcrs_state.cartesian.differentials["s"].d_xyz.to_value(
        u.km / u.s
    )
    metadata = dict(state.metadata)
    metadata["frame_transform"] = "TEME_TO_GCRS"
    metadata["frame_transform_epoch_utc"] = epoch_utc.isoformat()
    metadata["frame_transform_model"] = "Astropy TEME/GCRS transformation"
    metadata["iers_ut1_status"] = ut1_status_value
    metadata["iers_polar_motion_status"] = pm_status_value

    return OrbitalState(
        epoch=epoch_utc,
        frame="GCRS",
        position_km=tuple(float(value) for value in transformed_position),
        velocity_km_s=tuple(float(value) for value in transformed_velocity),
        covariance=None,
        source_format=state.source_format,
        metadata=metadata,
    )
