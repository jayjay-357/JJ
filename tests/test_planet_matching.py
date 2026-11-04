import pytest
from orion_ahop.ingestion.planet_matching import parse_planet_matching_text

SAMPLE = """# Planet Labs matching report
24ae Flock 4be-28 24ae FLOCK 4BE 28 60519 2.4 60519 True True - -
24bd Flock 4q-2 24bd FLOCK 4Q 2 58320 15.2 58320 True True - -
24d4 Flock 4g-19 - - - - False False 799601304 71304
24e0 Flock multi FLOCK MULTI 60000 1.2 60000/60001 True/False True - -
24f0 Flock hist FLOCK HIST 60484 hist 60484 True True - -
24d8 Flock 4h-7 24d8 FLOCK 4H 7 66710 0.297/39.341/49.786 66710/67273/66735 True/False/False True - -
"""

def test_conservative_match_screening():
    records = parse_planet_matching_text(SAMPLE)
    assert len(records) == 6
    assert records[0].hardware_id == "24ae"
    assert records[0].catalog_id == "60519"
    assert records[0].rms_values_km == (2.4,)
    assert records[0].disposition == "CANDIDATE_ONLY"
    assert records[1].disposition == "MANUAL_REVIEW"
    assert "not below 5 km" in records[1].reason
    assert records[2].catalog_id is None
    assert records[2].catid_9digit == "799601304"
    assert records[2].disposition == "MANUAL_REVIEW"
    assert len(records[3].match_ids) == 2
    assert records[3].disposition == "MANUAL_REVIEW"
    assert records[4].rms_values_km == (None,)
    assert records[4].disposition == "MANUAL_REVIEW"
    assert len(records[5].rms_values_km) == 3
    assert records[5].correct_name_flags == (True, False, False)
    assert records[5].disposition == "MANUAL_REVIEW"

def test_rejects_duplicate_hardware_ids():
    duplicate = SAMPLE + "24ae Another_Name NAME 60519 2.4 60519 True True - -\n"
    with pytest.raises(ValueError, match="Duplicate Planet hardware ID"):
        parse_planet_matching_text(duplicate)

def test_rejects_wrong_column_count():
    with pytest.raises(ValueError, match="too few fields"):
        parse_planet_matching_text("24ae name name 123 1.0 123 True True -")

def test_rejects_unrecognized_matching_columns():
    with pytest.raises(ValueError, match="Could not identify"):
        parse_planet_matching_text("24ae name name 123 1.0 123 yes True - -")

def test_rejects_empty_report():
    with pytest.raises(ValueError, match="no data rows"):
        parse_planet_matching_text("# no records")
