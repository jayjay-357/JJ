import json
from pathlib import Path

from scripts.acquire_spacetrack_catalog import (
    CACHE_TTL_SECONDS,
    load_cached_response,
    normalize,
)


def test_normalize_deduplicates_and_classifies_without_cartesian_conversion():
    records = [
        {"NORAD_CAT_ID": "00001", "OBJECT_NAME": "TEST PAYLOAD", "OBJECT_TYPE": "PAYLOAD",
         "MEAN_ELEMENT_THEORY": "SGP4", "EPOCH": "2026-11-03T00:00:00"},
        {"NORAD_CAT_ID": "00002", "OBJECT_NAME": "TEST DEBRIS", "OBJECT_TYPE": "DEBRIS",
         "MEAN_ELEMENT_THEORY": "SGP4"},
        {"NORAD_CAT_ID": "00003", "OBJECT_NAME": "TEST R/B", "OBJECT_TYPE": "ROCKET BODY",
         "MEAN_ELEMENT_THEORY": "SGP4"},
        {"NORAD_CAT_ID": "00001", "OBJECT_NAME": "DUPLICATE", "OBJECT_TYPE": "PAYLOAD"},
        {"OBJECT_NAME": "NO NORAD ID"},
    ]

    rows, report = normalize(records, max_records=10)

    assert [row["NORAD_CAT_ID"] for row in rows] == ["00001", "00002", "00003"]
    assert report["records_returned"] == 5
    assert report["records_missing_norad_id"] == 1
    assert report["duplicate_norad_ids_excluded"] == 1
    assert report["object_type_counts"] == {
        "DEBRIS": 1, "PAYLOAD": 1, "ROCKET BODY": 1
    }
    assert report["propagation_eligibility"] == "NOT_ELIGIBLE_AS_CARTESIAN_INITIAL_STATES"
    assert all("X" not in row and "X_DOT" not in row for row in rows)


def test_normalize_labels_missing_object_type_as_unclassified():
    rows, report = normalize([{"NORAD_CAT_ID": "12345"}], max_records=10)
    assert rows[0]["OBJECT_TYPE"] == "UNCLASSIFIED"
    assert report["unclassified_records"] == 1


def test_normalize_reports_truncation_after_unique_deduplication():
    records = [{"NORAD_CAT_ID": str(i), "OBJECT_TYPE": "DEBRIS"} for i in range(4)]
    rows, report = normalize(records, max_records=2)
    assert len(rows) == 2
    assert report["unique_norad_ids_available"] == 4
    assert report["records_truncated_after_download"] == 2


def test_cache_accepts_fresh_response_and_rejects_stale(tmp_path: Path, monkeypatch):
    from datetime import datetime, timezone

    now = datetime(2026, 11, 3, 12, 0, tzinfo=timezone.utc)
    monkeypatch.setattr("scripts.acquire_spacetrack_catalog.utc_now", lambda: now)
    path = tmp_path / "cache.json"
    path.write_text(json.dumps({
        "fetched_at_utc": now.isoformat(),
        "records": [{"NORAD_CAT_ID": "1"}],
    }))
    records, fetched_at = load_cached_response(path)
    assert records == [{"NORAD_CAT_ID": "1"}]
    assert fetched_at == now.isoformat()

    old = now.timestamp() - CACHE_TTL_SECONDS - 1
    path.write_text(json.dumps({
        "fetched_at_utc": datetime.fromtimestamp(old, timezone.utc).isoformat(),
        "records": [{"NORAD_CAT_ID": "1"}],
    }))
    records, fetched_at = load_cached_response(path)
    assert records is None
    assert fetched_at is None
