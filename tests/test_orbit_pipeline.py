from datetime import datetime, timezone

import pytest

from orion_ahop.propagators.orbit_pipeline import propagate_omm_to_gcrs


EPOCH = datetime(2024, 1, 1, tzinfo=timezone.utc)

# ISS-like GP/OMM fields used only to exercise the software path.
FIELDS = {
    "OBJECT_NAME": "ISS (ZARYA)",
    "OBJECT_ID": "1998-067A",
    "EPOCH": "2024-01-01T00:00:00.000000",
    "MEAN_MOTION": "15.50000000",
    "ECCENTRICITY": "0.0005000",
    "INCLINATION": "51.6400",
    "RA_OF_ASC_NODE": "10.0000",
    "ARG_OF_PERICENTER": "20.0000",
    "MEAN_ANOMALY": "30.0000",
    "MEAN_MOTION_DOT": "0.00001000",
    "MEAN_MOTION_DDOT": "0.00000000",
    "BSTAR": "0.00010000",
    "EPHEMERIS_TYPE": "0",
    "CLASSIFICATION_TYPE": "U",
    "NORAD_CAT_ID": "25544",
    "ELEMENT_SET_NO": "999",
    "REV_AT_EPOCH": "1",
    "MEAN_ELEMENT_THEORY": "SGP4",
}


def test_omm_to_gcrs_pipeline_returns_gcrs_state():
    state = propagate_omm_to_gcrs(FIELDS, EPOCH)
    assert state.frame == "GCRS"
    assert state.source_format == "OMM"
    assert state.metadata["state_source"] == "SGP4"
    assert len(state.position_km) == 3
    assert len(state.velocity_km_s) == 3


def test_omm_to_gcrs_requires_timezone_aware_target_epoch():
    with pytest.raises(ValueError, match="timezone-aware"):
        propagate_omm_to_gcrs(FIELDS, datetime(2024, 1, 1))
