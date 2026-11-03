#!/usr/bin/env python3
"""Fetch one provenance-tracked CelesTrak GP/SATCAT query as CSV."""
import argparse
import csv
import hashlib
import io
import json
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

GP = "https://celestrak.org/NORAD/elements/gp.php"
SATCAT = "https://celestrak.org/satcat/records.php"
CACHE_AGE = 7200
UA = "ORION-AHOP-research/0.1 (GitHub Actions; academic research)"


def now():
    return datetime.now(timezone.utc)


def request_csv(url):
    req = Request(url, headers={"User-Agent": UA, "Accept": "text/csv"})
    try:
        with urlopen(req, timeout=90) as response:
            if response.status != 200:
                raise RuntimeError(f"CelesTrak HTTP {response.status}; stopping without retry.")
            body = response.read()
    except HTTPError as exc:
        detail = exc.read(1000).decode("utf-8", "replace")
        raise RuntimeError(f"CelesTrak HTTP {exc.code}; stopping without retry: {detail}") from exc
    except (URLError, TimeoutError) as exc:
        raise RuntimeError(f"CelesTrak request failed; stopping without retry: {exc}") from exc
    text = body.decode("utf-8-sig")
    if not text.strip():
        raise RuntimeError("CelesTrak returned an empty response.")
    return text


def cached_csv(url, path):
    if path.exists():
        try:
            saved = json.loads(path.read_text(encoding="utf-8"))
            stamp = datetime.fromisoformat(saved["fetched_at"])
            age = (now() - stamp).total_seconds()
            if 0 <= age < CACHE_AGE:
                return saved["csv"], saved["fetched_at"], True
        except (ValueError, KeyError, OSError, TypeError):
            pass
    text = request_csv(url)
    stamp = now().isoformat()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"fetched_at": stamp, "csv": text}), encoding="utf-8")
    return text, stamp, False


def rows_from(text, label):
    try:
        rows = list(csv.DictReader(io.StringIO(text)))
    except csv.Error as exc:
        raise RuntimeError(f"Invalid {label} CSV: {exc}") from exc
    if not rows:
        raise RuntimeError(f"{label} query returned no records.")
    return [{k.strip(): (v or "").strip() for k, v in row.items() if k} for row in rows]


def val(row, *keys):
    return next((row.get(k, "") for k in keys if row.get(k, "")), "")


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--query-type", choices=("GROUP", "NAME", "CATNR"), required=True)
    p.add_argument("--query-value", required=True)
    p.add_argument("--max-records", type=int, default=300)
    p.add_argument("--cache-dir", type=Path, default=Path("data/celestrak-cache"))
    p.add_argument("--output-dir", type=Path, default=Path("data/celestrak-acquisition"))
    a = p.parse_args()
    value = a.query_value.strip()
    if not value or not 1 <= a.max_records <= 20000:
        p.error("query value must be nonempty and max-records must be 1..20000")
    if a.query_type == "CATNR" and not value.isdigit():
        p.error("CATNR must contain digits only")

    query = {a.query_type: value}
    gp_url = GP + "?" + urlencode({**query, "FORMAT": "CSV"})
    sat_url = SATCAT + "?" + urlencode({**query, "FORMAT": "CSV", "ONORBIT": "1", "MAX": str(a.max_records)})
    key = hashlib.sha256(f"{a.query_type}:{value}".encode()).hexdigest()[:16]
    gp_text, gp_stamp, gp_hit = cached_csv(gp_url, a.cache_dir / f"{key}-gp.json")
    sat_text, sat_stamp, sat_hit = cached_csv(sat_url, a.cache_dir / f"{key}-satcat.json")
    gp_rows = rows_from(gp_text, "GP")
    sat_rows = rows_from(sat_text, "SATCAT") 
    gp_rows = gp_rows[:a.max_records]
    sat_by_id = {val(r, "NORAD_CAT_ID", "NORAD_CATID"): r for r in sat_rows if val(r, "NORAD_CAT_ID", "NORAD_CATID")}

    output = []
    types = Counter()
    missing = 0
    for gp in gp_rows:
        ident = val(gp, "NORAD_CAT_ID", "NORAD_CATID")
        if not ident:
            continue
        sat = sat_by_id.get(ident, {})
        kind = val(sat, "OBJECT_TYPE") or "UNCLASSIFIED"
        types[kind] += 1
        missing += int(not bool(sat))
        output.append({
            "NORAD_CAT_ID": ident,
            "OBJECT_NAME": val(gp, "OBJECT_NAME", "SATNAME") or val(sat, "OBJECT_NAME"),
            "OBJECT_ID": val(gp, "OBJECT_ID") or val(sat, "OBJECT_ID"),
            "OBJECT_TYPE": kind,
            "EPOCH": val(gp, "EPOCH"),
            "MEAN_MOTION": val(gp, "MEAN_MOTION"),
            "ECCENTRICITY": val(gp, "ECCENTRICITY"),
            "INCLINATION": val(gp, "INCLINATION"),
            "RA_OF_ASC_NODE": val(gp, "RA_OF_ASC_NODE"),
            "ARG_OF_PERICENTER": val(gp, "ARG_OF_PERICENTER"),
            "MEAN_ANOMALY": val(gp, "MEAN_ANOMALY"),
            "BSTAR": val(gp, "BSTAR"),
            "MEAN_MOTION_DOT": val(gp, "MEAN_MOTION_DOT"),
            "MEAN_MOTION_DDOT": val(gp, "MEAN_MOTION_DDOT"),
            "OPS_STATUS_CODE": val(sat, "OPS_STATUS_CODE"),
            "LAUNCH_DATE": val(sat, "LAUNCH_DATE"),
            "DECAY_DATE": val(sat, "DECAY_DATE"),
        })
    if not output:
        raise RuntimeError("No usable GP records with NORAD catalog IDs were returned.")

    a.output_dir.mkdir(parents=True, exist_ok=True)
    csv_path = a.output_dir / "orion_celestrak_sample.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(output[0]))
        writer.writeheader()
        writer.writerows(output)

    report = {
        "provider": "CelesTrak",
        "query": query,
        "retrieved_at_utc": now().isoformat(),
        "gp_url": gp_url,
        "satcat_url": sat_url,
        "gp_retrieved_at_utc": gp_stamp,
        "satcat_retrieved_at_utc": sat_stamp,
        "gp_cache_used": gp_hit,
        "satcat_cache_used": sat_hit,
        "gp_rows_returned": len(rows_from(gp_text, "GP")),
        "gp_rows_retained": len(gp_rows),
        "satcat_rows_returned": len(sat_rows),
        "joined_rows": len(output),
        "missing_satcat_match": missing,
        "object_type_counts": dict(sorted(types.items())),
        "max_records": a.max_records,
        "limitations": [
            "Query-defined sample only; not a complete orbital catalog.",
            "GP records are truncated after download, so the provider response itself may be larger.",
            "SATCAT object type is not the same as current operational status.",
            "GP mean elements are intended for SGP4, not direct Cowell Cartesian initialization.",
            "No covariance is acquired here; collision probability remains unquantified without valid covariance.",
        ],
        "catalog_file": str(csv_path),
    }
    (a.output_dir / "acquisition_report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    try:
        main()
    except RuntimeError as exc:
        print(f"ACQUISITION FAILED: {exc}", file=sys.stderr)
        raise SystemExit(1)
