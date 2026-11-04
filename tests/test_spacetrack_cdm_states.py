from scripts.acquire_spacetrack_cdm_states import extract_object


def test_extracts_gcrs_cdm_state_and_converts_units():
    row = {
        "CDM_ID": "example-cdm",
        "CREATED": "2026-01-01T00:00:00",
        "TCA": "2026-01-01T00:05:00",
        "ORBIT_CENTER": "EARTH",
        "SAT1_OBJECT_DESIGNATOR": "12345",
        "SAT1_OBJECT_NAME": "TEST OBJECT",
        "SAT1_OBJECT_TYPE": "DEBRIS",
        "SAT1_REF_FRAME": "GCRS",
        "SAT1_X": "7000000", "SAT1_X_UNIT": "m",
        "SAT1_Y": "0", "SAT1_Y_UNIT": "m",
        "SAT1_Z": "0", "SAT1_Z_UNIT": "m",
        "SAT1_X_DOT": "0", "SAT1_X_DOT_UNIT": "m/s",
        "SAT1_Y_DOT": "7500", "SAT1_Y_DOT_UNIT": "m/s",
        "SAT1_Z_DOT": "0", "SAT1_Z_DOT_UNIT": "m/s",
    }

    state = extract_object(row, "SAT1")

    assert state is not None
    assert state["norad_cat_id"] == "12345"
    assert state["object_type"] == "DEBRIS"
    assert state["epoch_utc"] == "2026-01-01T00:05:00+00:00"
    assert state["normalized_frame"] == "GCRS"
    assert state["propagation_status"] == "READY_GCRS"
    assert state["x_km"] == 7000.0
    assert state["vy_km_s"] == 7.5


def test_rejects_non_earth_centered_cdm_state():
    row = {
        "TCA": "2026-01-01T00:05:00",
        "ORBIT_CENTER": "SUN",
        "SAT1_OBJECT_DESIGNATOR": "12345",
        "SAT1_REF_FRAME": "GCRS",
    }

    assert extract_object(row, "SAT1") is None


def test_rejects_invalid_catalog_designator():
    row = {
        "TCA": "2026-01-01T00:05:00",
        "ORBIT_CENTER": "EARTH",
        "SAT1_OBJECT_DESIGNATOR": "UNKNOWN",
        "SAT1_REF_FRAME": "GCRS",
    }

    assert extract_object(row, "SAT1") is None
