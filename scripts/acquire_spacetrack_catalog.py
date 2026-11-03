#!/usr/bin/env python3
"""Acquire Space-Track GP records for catalog identification only.

This script deliberately does not convert GP/OMM mean elements into Cartesian
states and does not invoke SGP4. Its output is a provenance-tracked object
catalog for matching IDs and classifying payloads, debris, and rocket bodies.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import sys
import time
from collections import Counter
from datetime import datetime, timezone
from http.cookiejar import CookieJar
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import HTTPCookieProcessor, Request, build_opener

BASE_URL = "https://www.space-track.org"
GP_PATH = "/basicspacedata/query/class/gp/EPOCH/%3Enow-10/DECAY_DATE/null-val/format/json"
CACHE_TTL_SECONDS = 3600
USER_AGENT = "ORION-AHOP-research/0.1 (academic research; catalog-only acquisition)"
CSV_FIELDS = (
    "NORAD_CAT_ID", "OBJECT_NAME", "OBJECT_ID", "OBJECT_TYPE",
    "COUNTRY_CODE", "LAUNCH_DATE", "DECAY_DATE", "OPS_STATUS_CODE",
    "EPOCH", "CENTER_NAME", "REF_FRAME", "TIME_SYSTEM",
    "MEAN_ELEMENT_THEORY", "MEAN_MOTION", "ECCENTRICITY", "INCLINATION",
    "RA_OF_ASC_NODE", "ARG_OF_PERICENTER", "MEAN_ANOMALY", "BSTAR",
    "MEAN_MOTION_DOT", "MEAN_MOTION_DDOT", "RCS_SIZE",
)


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def load_cached_response(cache_path: Path) -> tuple[list[dict] | None, str | None]:
    if not cache_path.exists():
        return None, None
    try:
        saved = json.loads(cache_path.read_text(encoding="utf-8"))
        fetched_at = datetime.fromisoformat(saved["fetched_at_utc"])
        age = (utc_now() - fetched_at).total_seconds()
        records = saved["records"]
        if age < 0 or age >= CACHE_TTL_SECONDS or not isinstance(records, list):
            return None, None
        return records, saved["fetched_at_utc"]
    except (OSError, ValueError, KeyError, TypeError):
        return None, None


def spacetrack_opener():
    return build_opener(HTTPCookieProcessor(CookieJar()))


def request_json(opener, url: str) -> list[dict]:
    request = Request(url, headers={"User-Agent": USER_AGENT, "Accept": "application/json"})
    try:
        with opener.open(request, timeout=120) as response:
            if response.status != 200:
                raise RuntimeError(f"Space-Track returned HTTP {response.status}.")
            body = response.read()
    except HTTPError as exc:
        detail = exc.read(1000).decode("utf-8", "replace")
        raise RuntimeError(f"Space-Track HTTP {exc.code}: {detail}") from exc
    except (URLError, TimeoutError) as exc:
        raise RuntimeError(f"Space-Track request failed: {exc}") from exc
    try:
        records = json.loads(body.decode("utf-8-sig"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise RuntimeError("Space-Track did not return valid JSON. Check credentials and API response.") from exc
    if not isinstance(records, list):
        raise RuntimeError("Unexpected Space-Track response: expected a JSON array.")
    if records and not isinstance(records[0], dict):
        raise RuntimeError("Unexpected Space-Track response: records are not JSON objects.")
    return records


def fetch_gp(identity: str, password: str) -> list[dict]:
    opener = spacetrack_opener()
    login_url = BASE_URL + "/ajaxauth/login"
    payload = urlencode({"identity": identity, "password": password}).encode("utf-8")
    login = Request(
        login_url, data=payload, method="POST",
        headers={"User-Agent": USER_AGENT, "Content-Type": "application/x-www-form-urlencoded"},
    )
    try:
        with opener.open(login, timeout=60) as response:
            login_body = response.read(1000).decode("utf-8", "replace")
            if response.status != 200:
                raise RuntimeError(f"Space-Track login failed with HTTP {response.status}.")
    except HTTPError as exc:
        raise RuntimeError(f"Space-Track login failed with HTTP {exc.code}. Check repository secrets.") from exc
    except (URLError, TimeoutError) as exc:
        raise RuntimeError(f"Space-Track login request failed: {exc}") from exc
    if "Login Failed" in login_body or "Invalid" in login_body:
        raise RuntimeError("Space-Track rejected the credentials. Check SPACETRACK_IDENTITY and SPACETRACK_PASSWORD.")
    return request_json(opener, BASE_URL + GP_PATH)


def clean(value) -> str:
    if value is None:
        return ""
    return str(value).strip()


def normalize(records: list[dict], max_records: int) -> tuple[list[dict], dict]:
    unique = {}
    duplicates = 0
    missing_ids = 0
    for record in records:
        norad_id = clean(record.get("NORAD_CAT_ID") or record.get("NORAD_CATID"))
        if not norad_id:
            missing_ids += 1
            continue
        if norad_id in unique:
            duplicates += 1
            continue
        unique[norad_id] = record

    ordered = list(unique.items())
    retained = ordered[:max_records]
    rows = []
    counts = Counter()
    missing_types = 0
    for norad_id, record in retained:
        object_type = clean(record.get("OBJECT_TYPE")).upper() or "UNCLASSIFIED"
        counts[object_type] += 1
        missing_types += int(object_type == "UNCLASSIFIED")
        row = {field: clean(record.get(field)) for field in CSV_FIELDS}
        row["NORAD_CAT_ID"] = norad_id
        row["OBJECT_TYPE"] = object_type
        rows.append(row)

    report = {
        "provider": "Space-Track.org",
        "product": "GP (General Perturbations) / OMM-compatible JSON",
        "retrieved_at_utc": utc_now().isoformat(),
        "query_path": GP_PATH,
        "records_returned": len(records),
        "records_missing_norad_id": missing_ids,
        "duplicate_norad_ids_excluded": duplicates,
        "unique_norad_ids_available": len(unique),
        "unique_norad_ids_retained": len(rows),
        "records_truncated_after_download": max(0, len(ordered) - len(rows)),
        "unclassified_records": missing_types,
        "object_type_counts": dict(sorted(counts.items())),
        "mean_element_theory_counts": dict(sorted(Counter(
            clean(row["MEAN_ELEMENT_THEORY"]).upper() or "NOT_REPORTED" for row in rows
        ).items())),
        "propagation_eligibility": "NOT_ELIGIBLE_AS_CARTESIAN_INITIAL_STATES",
        "limitations": [
            "GP records are general-perturbation mean elements, commonly based on SGP4 theory.",
            "This catalog is for object identification, classification, and cross-source matching only.",
            "This script does not invoke SGP4 or convert mean elements into Cartesian states.",
            "No Cartesian position/velocity state or covariance is produced by this acquisition.",
            "The query includes on-orbit records with GP epochs in the last 10 days; it is not a historical catalog.",
            "OBJECT_TYPE may be absent for some records; those records are retained as UNCLASSIFIED.",
        ],
    }
    return rows, report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cache-dir", type=Path, default=Path("data/spacetrack-cache"))
    parser.add_argument("--output-dir", type=Path, default=Path("data/spacetrack-acquisition"))
    parser.add_argument("--max-records", type=int, default=50000)
    args = parser.parse_args()
    if not 1 <= args.max_records <= 100000:
        parser.error("--max-records must be between 1 and 100000")

    cache_path = args.cache_dir / "gp_on_orbit_recent.json"
    cached, cached_at = load_cached_response(cache_path)
    cache_used = cached is not None
    if cache_used:
        records = cached
    else:
        identity = os.environ.get("SPACETRACK_IDENTITY", "").strip()
        password = os.environ.get("SPACETRACK_PASSWORD", "")
        if not identity or not password:
            raise RuntimeError(
                "Missing credentials. Add SPACETRACK_IDENTITY and SPACETRACK_PASSWORD "
                "as GitHub Actions repository secrets."
            )
        records = fetch_gp(identity, password)
        fetched_at = utc_now().isoformat()
        args.cache_dir.mkdir(parents=True, exist_ok=True)
        cache_path.write_text(
            json.dumps({"fetched_at_utc": fetched_at, "records": records}, separators=(",", ":")),
            encoding="utf-8",
        )
        cached_at = fetched_at

    rows, report = normalize(records, args.max_records)
    if not rows:
        raise RuntimeError("Space-Track returned no usable records with NORAD catalog IDs.")
    args.output_dir.mkdir(parents=True, exist_ok=True)
    csv_path = args.output_dir / "spacetrack_object_catalog.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=CSV_FIELDS)
        writer.writeheader()
        writer.writerows(rows)

    raw_path = args.output_dir / "spacetrack_gp_raw.json"
    raw_path.write_text(json.dumps(records, indent=2), encoding="utf-8")
    report["cache_used"] = cache_used
    report["source_response_fetched_at_utc"] = cached_at
    report["catalog_csv"] = str(csv_path)
    report["raw_response_json"] = str(raw_path)
    report_path = args.output_dir / "spacetrack_acquisition_report.json"
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except RuntimeError as exc:
        print(f"ACQUISITION FAILED: {exc}", file=sys.stderr)
        raise SystemExit(1)
