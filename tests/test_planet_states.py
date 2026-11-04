import pytest
from astropy.time import Time

from orion_ahop.ingestion.planet_states import parse_planet_states_text

SAMPLE = """# Planet Labs state-vector sample
24ae 839558749.184000 -4235445.0655 5173394.9538 1236503.8116 -122.7654 1701.5508 -7467.5952 29.27249 inf
24bd 839573155.184000 -4201952.4731 4144838.5482 3356700.0416 -1890.4588 3430.8185 -6585.5646 63.32987 inf
"""


def test_parse_planet_state_and_units():
    records = parse_planet_states_text(SAMPLE)
    assert len(records) == 2
    first = records[0]
    assert first.hardware_id == "24ae"
    assert first.state.frame == "J2000"
    assert first.state.source_format == "PLANET_STATES"
    assert first.state.position_km[0] == pytest.approx(-4235.4450655)
    assert first.state.velocity_km_s[0] == pytest.approx(-0.1227654)
    assert first.drag_ballistic_coefficient_kg_m2 == pytest.approx(29.27249)
    assert first.srp_ballistic_coefficient_kg_m2 is None
    assert first.raw_srp_coefficient == "inf"
    assert first.state.metadata["sgp4_used"] is False
    assert first.state.metadata["norad_id"] is None


def test_tt_epoch_is_converted_to_utc():
    record = parse_planet_states_text(SAMPLE)[0]
    expected = (Time("2000-01-01T12:00:00", scale="tt") +
                (839558749.184000 * __import__("astropy").units.s)).utc.to_datetime()
    assert abs((record.state.epoch.replace(tzinfo=None) - expected).total_seconds()) < 1e-5


def test_rejects_duplicate_hardware_ids():
    duplicate = SAMPLE + SAMPLE.splitlines()[1] + "\n"
    with pytest.raises(ValueError, match="Duplicate hardware ID"):
        parse_planet_states_text(duplicate)


def test_rejects_wrong_column_count():
    with pytest.raises(ValueError, match="exactly 10 columns"):
        parse_planet_states_text("24ae 1 2 3 4 5 6 7 8")


def test_rejects_nonfinite_state_components():
    row = "24ae 839558749.184000 nan 2 3 4 5 6 7 8 9"
    with pytest.raises(ValueError, match="Non-finite Cartesian"):
        parse_planet_states_text(row)


def test_rejects_empty_file():
    with pytest.raises(ValueError, match="no records"):
        parse_planet_states_text("# empty")
