from datetime import timezone
import pytest

from orion_ahop.ingestion.oem import parse_oem_kvn_text, validate_oem_segment, load_oem_kvn_file

OEM = """CCSDS_OEM_VERS = 2.0
CREATION_DATE = 2026-01-01T00:00:00
ORIGINATOR = ORION-X TEST
META_START
OBJECT_NAME = TEST SATELLITE
OBJECT_ID = 2026-001A
CENTER_NAME = EARTH
REF_FRAME = EME2000
TIME_SYSTEM = UTC
START_TIME = 2026-01-01T00:00:00
STOP_TIME = 2026-01-01T00:02:00
META_STOP
2026-01-01T00:00:00 7000 0 0 0 7.5 1
2026-01-01T00:01:00 6990 450 60 -0.5 7.49 1
2026-01-01T00:02:00 6970 900 120 -1.0 7.45 1
"""


def test_parse_oem_states_and_metadata():
    segment = parse_oem_kvn_text(OEM)[0]
    assert len(segment.states) == 3
    assert segment.states[0].frame == "EME2000"
    assert segment.states[0].epoch.tzinfo == timezone.utc
    assert segment.states[0].position_km == (7000.0, 0.0, 0.0)
    assert segment.states[0].velocity_km_s == (0.0, 7.5, 1.0)
    assert segment.states[0].source_format == "OEM"


def test_validate_oem_segment_success():
    result = validate_oem_segment(parse_oem_kvn_text(OEM)[0])
    assert result.valid
    assert result.errors == ()
    assert result.warnings


def test_converts_declared_metre_units():
    text = OEM.replace("REF_FRAME = EME2000", "REF_FRAME = EME2000\nDISTANCE_UNITS = M\nVELOCITY_UNITS = M/S")
    text = text.replace("7000 0 0 0 7.5 1", "7000000 0 0 0 7500 1000")
    text = text.replace("6990 450 60 -0.5 7.49 1", "6990000 450000 60000 -500 7490 1000")
    text = text.replace("6970 900 120 -1.0 7.45 1", "6970000 900000 120000 -1000 7450 1000")
    state = parse_oem_kvn_text(text)[0].states[0]
    assert state.position_km == (7000.0, 0.0, 0.0)
    assert state.velocity_km_s == (0.0, 7.5, 1.0)


def test_rejects_non_utc_time_system():
    with pytest.raises(ValueError, match="only UTC"):
        parse_oem_kvn_text(OEM.replace("TIME_SYSTEM = UTC", "TIME_SYSTEM = TAI"))


def test_rejects_non_earth_center():
    with pytest.raises(ValueError, match="Earth-centred"):
        parse_oem_kvn_text(OEM.replace("CENTER_NAME = EARTH", "CENTER_NAME = MARS"))


def test_rejects_malformed_state_row():
    with pytest.raises(ValueError, match="six components"):
        parse_oem_kvn_text(OEM.replace("7000 0 0 0 7.5 1", "7000 0 0 7.5 1"))


def test_rejects_duplicate_epochs():
    text = OEM.replace("2026-01-01T00:01:00 6990 450 60 -0.5 7.49 1", "2026-01-01T00:00:00 6990 450 60 -0.5 7.49 1")
    result = validate_oem_segment(parse_oem_kvn_text(text)[0])
    assert not result.valid
    assert any("Duplicate epoch" in error for error in result.errors)


def test_loads_file(tmp_path):
    path = tmp_path / "sample.oem"
    path.write_text(OEM, encoding="utf-8")
    assert len(load_oem_kvn_file(path)[0].states) == 3
