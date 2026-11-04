import pytest
from orion_ahop.ingestion.planet_matching import parse_planet_matching_text

SAMPLE = """# Planet Labs matching report
# hw_id planet_name 18spcs_name catid rms_km matches correct_name catalogued catid_9digit catid_supplemental
24ae Flock_4be-28 FLOCK_4BE_28 60519 2.4 60519 True True - -
24bd Flock_4q-2 FLOCK_4Q_2 58320 15.2 58320 True True - -
24d4 Flock_4g-19 - - - - False False 799601304 71304
24e0 Flock_multi FLOCK_MULTI 60000 1.2 60000/60001 True True - -
24f0 Flock_hist FLOCK_HIST 60484 hist 60484 True True - -
"""

def test_conservative_match_screening():
    records = parse_planet_matching_text(SAMPLE)
    assert len(records) == 5
    assert records[0].hardware_id == "24ae"
    assert records[0].catalog_id == "60519"
    assert records[0].disposition == "CANDIDATE_ONLY"
    assert records[1].disposition == "MANUAL_REVIEW"
    assert "not below 5 km" in records[1].reason
    assert records[2].catalog_id is None
    assert records[2].catid_9digit == "799601304"
    assert records[2].disposition == "MANUAL_REVIEW"
    assert len(records[3].match_ids) == 2
    assert records[3].disposition == "MANUAL_REVIEW"
    assert records[4].rms_km is None
    assert records[4].disposition == "MANUAL_REVIEW"

def test_rejects_duplicate_hardware_ids():
    duplicate = SAMPLE + "24ae Another Name NAME 60519 2.4 60519 True True - -\n"
    with pytest.raises(ValueError, match="Duplicate Planet hardware ID"):
        parse_planet_matching_text(duplicate)

def test_rejects_wrong_column_count():
    with pytest.raises(ValueError, match="10 columns"):
        parse_planet_matching_text("24ae name name 123 1.0 123 True True -")

def test_rejects_invalid_boolean_flag():
    with pytest.raises(ValueError, match="boolean flag"):
        parse_planet_matching_text("24ae name name 123 1.0 123 yes True - -")

def test_rejects_empty_report():
    with pytest.raises(ValueError, match="no data rows"):
        parse_planet_matching_text("# no records")
