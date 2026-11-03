from datetime import datetime, timedelta, timezone
import importlib.util
import json
from pathlib import Path

MODULE_PATH = Path(__file__).resolve().parents[1] / "scripts" / "acquire_celestrak.py"
SPEC = importlib.util.spec_from_file_location("acquire_celestrak", MODULE_PATH)
acquisition = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(acquisition)


def test_rows_from_parses_csv_and_strips_values():
    rows = acquisition.rows_from("NORAD_CAT_ID, OBJECT_NAME\\n25544, ISS \\n", "fixture")
    assert rows == [{"NORAD_CAT_ID": "25544", "OBJECT_NAME": "ISS"}]


def test_val_returns_first_available_field():
    assert acquisition.val({"NORAD_CATID": "25544"}, "NORAD_CAT_ID", "NORAD_CATID") == "25544"


def test_cached_csv_uses_fresh_cache(tmp_path, monkeypatch):
    path = tmp_path / "cached.json"
    stamp = datetime.now(timezone.utc).isoformat()
    path.write_text(json.dumps({"fetched_at": stamp, "csv": "a,b\\n1,2\\n"}), encoding="utf-8")

    def unexpected_request(_url):
        raise AssertionError("fresh cache should avoid a network request")

    monkeypatch.setattr(acquisition, "request_csv", unexpected_request)
    text, fetched_at, cache_hit = acquisition.cached_csv("https://example.invalid", path)
    assert text == "a,b\\n1,2\\n"
    assert fetched_at == stamp
    assert cache_hit is True


def test_cached_csv_refetches_expired_cache(tmp_path, monkeypatch):
    path = tmp_path / "cached.json"
    old_stamp = (datetime.now(timezone.utc) - timedelta(hours=3)).isoformat()
    path.write_text(json.dumps({"fetched_at": old_stamp, "csv": "old"}), encoding="utf-8")
    monkeypatch.setattr(acquisition, "request_csv", lambda _url: "new,data\\n1,2\\n")
    text, _stamp, cache_hit = acquisition.cached_csv("https://example.invalid", path)
    assert text == "new,data\\n1,2\\n"
    assert cache_hit is False
