from datetime import datetime
import pytest
from orion_ahop.ingestion.ccsds_kvn import parse_kvn_text
from orion_ahop.ingestion.converters import opm_to_state, combined_fields

def test_opm_to_cartesian_state():
    text = """CCSDS_OPM_VERS = 2.0
META_START
OBJECT_NAME = DEMO
OBJECT_ID = 2026-001A
CENTER_NAME = EARTH
REF_FRAME = GCRF
TIME_SYSTEM = UTC
META_STOP
EPOCH = 2026-01-01T00:00:00.000
X = 7000
Y = 0
Z = 0
X_DOT = 0
Y_DOT = 7.5
Z_DOT = 0
"""
    msg = parse_kvn_text(text)
    state = opm_to_state(msg)
    assert state.epoch == datetime(2026, 1, 1)
    assert state.position_km == (7000.0, 0.0, 0.0)
    assert state.velocity_km_s == (0.0, 7.5, 0.0)
    assert state.frame == "GCRF"

def test_combined_fields_data_overrides_metadata():
    msg = parse_kvn_text("CCSDS_OPM_VERS = 2.0\nMETA_START\nREF_FRAME = TEME\nMETA_STOP\nREF_FRAME = GCRF\n")
    assert combined_fields(msg)["REF_FRAME"] == "GCRF"
