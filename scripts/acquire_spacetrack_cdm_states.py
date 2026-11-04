"""Acquire Cartesian state samples from Space-Track public CDMs.

CDM states are event-time samples (at TCA), not continuous ephemerides.
This script preserves each source frame and never invokes SGP4 or converts
mean elements into Cartesian states.
"""
from __future__ import annotations

import argparse
import csv
import json
import os
import sys
import time
import numpy as np
from astropy import units as u
from astropy.coordinates import CartesianDifferential, CartesianRepresentation, GCRS, ITRS
from astropy.time import Time
from astropy.utils import iers
from datetime import date, datetime, timedelta, timezone
from http.cookiejar import CookieJar
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import HTTPCookieProcessor, Request, build_opener

BASE = "https://www.space-track.org"
FIELDS = (
    "CDM_ID", "CREATED", "TCA", "ORBIT_CENTER",
    "SAT1_OBJECT_DESIGNATOR", "SAT1_OBJECT_NAME", "SAT1_OBJECT_TYPE",
    "SAT1_REF_FRAME", "SAT1_X", "SAT1_X_UNIT", "SAT1_Y", "SAT1_Y_UNIT",
    "SAT1_Z", "SAT1_Z_UNIT", "SAT1_X_DOT", "SAT1_X_DOT_UNIT",
    "SAT1_Y_DOT", "SAT1_Y_DOT_UNIT", "SAT1_Z_DOT", "SAT1_Z_DOT_UNIT",
    "SAT2_OBJECT_DESIGNATOR", "SAT2_OBJECT_NAME", "SAT2_OBJECT_TYPE",
    "SAT2_REF_FRAME", "SAT2_X", "SAT2_X_UNIT", "SAT2_Y", "SAT2_Y_UNIT",
    "SAT2_Z", "SAT2_Z_UNIT", "SAT2_X_DOT", "SAT2_X_DOT_UNIT",
    "SAT2_Y_DOT", "SAT2_Y_DOT_UNIT", "SAT2_Z_DOT", "SAT2_Z_DOT_UNIT",
)
OUT_FIELDS = (
    "norad_cat_id", "object_name", "object_type", "epoch_utc", "cdm_id",
    "source_created_utc", "orbit_center", "source_frame",
    "x_km", "y_km", "z_km", "vx_km_s", "vy_km_s", "vz_km_s",
    "state_epoch_semantics", "source", "normalized_frame", "frame_transform", "propagation_status",
)


def _parse_epoch(value: str) -> datetime:
    text = value.strip().replace("Z", "+00:00")
    parsed = datetime.fromisoformat(text)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _number(row: dict, key: str) -> float:
    value = float(row[key])
    if not (value == value and abs(value) != float("inf")):
        raise ValueError(f"non-finite {key}")
    return value


def _to_km(value: float, unit: str) -> float:
    normalized = unit.strip().lower().replace(" ", "")
    if normalized in {"km", "kilometer", "kilometers"}:
        return value
    if normalized in {"m", "meter", "meters"}:
        return value / 1000.0
    raise ValueError(f"unsupported position unit: {unit!r}")


def _to_km_s(value: float, unit: str) -> float:
    normalized = unit.strip().lower().replace(" ", "")
    if normalized in {"km/s", "km/sec", "kilometer/second"}:
        return value
    if normalized in {"m/s", "m/sec", "meter/second"}:
        return value / 1000.0
    raise ValueError(f"unsupported velocity unit: {unit!r}")


def extract_object(row: dict, prefix: str) -> dict | None:
    designator = str(row.get(f"{prefix}_OBJECT_DESIGNATOR") or "").strip()
    if not designator.isdigit():
        return None
    frame = str(row.get(f"{prefix}_REF_FRAME") or "").strip().upper()
    center = str(row.get("ORBIT_CENTER") or "EARTH").strip().upper()
    if center not in {"EARTH", ""} or not frame:
        return None
    try:
        p = [
            _to_km(_number(row, f"{prefix}_{axis}"), row.get(f"{prefix}_{axis}_UNIT") or "km")
            for axis in ("X", "Y", "Z")
        ]
        v = [
            _to_km_s(_number(row, f"{prefix}_{axis}_DOT"), row.get(f"{prefix}_{axis}_DOT_UNIT") or "km/s")
            for axis in ("X", "Y", "Z")
        ]
        epoch = _parse_epoch(str(row["TCA"]))
        created = _parse_epoch(str(row.get("CREATED") or row["TCA"]))
    except (KeyError, TypeError, ValueError):
        return None
    radius = sum(component * component for component in p) ** 0.5
    speed = sum(component * component for component in v) ** 0.5
    if not (6370.0 < radius < 100000.0 and 0.1 < speed < 20.0):
        return None
    normalized_frame = frame
    transform_name = "NONE"
    status = "FRAME_TRANSFORM_REQUIRED"
    if frame == "GCRS":
        status = "READY_GCRS"
    elif frame in {"ITRF", "ITRS"}:
        try:
            obstime = Time(epoch, scale="utc")
            representation = CartesianRepresentation(
                np.asarray(p) * u.km,
                differentials=CartesianDifferential(np.asarray(v) * u.km / u.s),
            )
            source_state = ITRS(representation, obstime=obstime)
            with iers.conf.set_temp("auto_download", True):
                transformed = source_state.transform_to(GCRS(obstime=obstime))
            p = transformed.cartesian.xyz.to_value(u.km).tolist()
            v = transformed.cartesian.differentials["s"].d_xyz.to_value(u.km / u.s).tolist()
            normalized_frame = "GCRS"
            transform_name = "Astropy ITRS-to-GCRS with IERS Earth-orientation data"
            status = "READY_GCRS"
        except Exception as exc:
            transform_name = f"ITRS_TO_GCRS_FAILED: {type(exc).__name__}: {exc}"
    return {
        "norad_cat_id": designator,
        "object_name": str(row.get(f"{prefix}_OBJECT_NAME") or "").strip(),
        "object_type": str(row.get(f"{prefix}_OBJECT_TYPE") or "UNKNOWN").strip().upper(),
        "epoch_utc": epoch.isoformat(),
        "cdm_id": str(row.get("CDM_ID") or ""),
        "source_created_utc": created.isoformat(),
        "orbit_center": "EARTH",
        "source_frame": frame,
        "x_km": p[0], "y_km": p[1], "z_km": p[2],
        "vx_km_s": v[0], "vy_km_s": v[1], "vz_km_s": v[2],
        "state_epoch_semantics": "CDM state vector at TCA",
        "source": "Space-Track CDMPublic",
        "normalized_frame": normalized_frame,
        "frame_transform": transform_name,
        "propagation_status": status,
    }


class SpaceTrack:
    def __init__(self, identity: str, password: str):
        self.opener = build_opener(HTTPCookieProcessor(CookieJar()))
        body = f"identity={quote(identity)}&password={quote(password)}".encode()
        request = Request(
            f"{BASE}/ajaxauth/login", data=body,
            headers={"Content-Type": "application/x-www-form-urlencoded",
                     "User-Agent": "ORION-X research data acquisition/1.0"},
        )
        with self.opener.open(request, timeout=60) as response:
            response.read()
        self.opener.open(f"{BASE}/basicspacedata/query/class/satcat/limit/1/format/json", timeout=60).read()

    def query(self, start: date, end: date) -> list[dict]:
        interval = f"{start.isoformat()}--{end.isoformat()}"
        url = (
            f"{BASE}/basicspacedata/query/class/cdm_public/"
            f"CREATED/{quote(interval, safe='')}/orderby/CREATED%20asc/format/json"
        )
        for attempt in range(4):
            try:
                request = Request(url, headers={"User-Agent": "ORION-X research data acquisition/1.0"})
                with self.opener.open(request, timeout=180) as response:
                    payload = response.read()
                data = json.loads(payload)
                if not isinstance(data, list):
                    raise RuntimeError("Space-Track CDM response was not a JSON list")
                return data
            except (HTTPError, URLError, TimeoutError, json.JSONDecodeError) as exc:
                if attempt == 3:
                    raise RuntimeError(f"Space-Track query failed for {interval}: {exc}") from exc
                time.sleep(5 * (attempt + 1))
        return []


def month_windows(start: date, end: date):
    cursor = start
    while cursor <= end:
        next_month = (cursor.replace(day=28) + timedelta(days=4)).replace(day=1)
        window_end = min(end, next_month - timedelta(days=1))
        yield cursor, window_end
        cursor = window_end + timedelta(days=1)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--start-date", default="2018-01-01")
    parser.add_argument("--end-date", default=datetime.now(timezone.utc).date().isoformat())
    parser.add_argument("--output-dir", default="data/spacetrack-cdm-acquisition")
    args = parser.parse_args()

    identity = os.environ.get("SPACETRACK_IDENTITY")
    password = os.environ.get("SPACETRACK_PASSWORD")
    if not identity or not password:
        print("Missing SPACETRACK_IDENTITY or SPACETRACK_PASSWORD.", file=sys.stderr)
        return 2

    start = date.fromisoformat(args.start_date)
    end = date.fromisoformat(args.end_date)
    if start > end:
        parser.error("--start-date must be on or before --end-date")

    output = Path(args.output_dir)
    output.mkdir(parents=True, exist_ok=True)
    client = SpaceTrack(identity, password)
    raw_path = output / "spacetrack_cdm_public_raw.jsonl"
    all_rows = []
    raw_count = 0

    with raw_path.open("w", encoding="utf-8") as raw_file:
        for window_start, window_end in month_windows(start, end):
            rows = client.query(window_start, window_end)
            for row in rows:
                raw_file.write(json.dumps(row, separators=(",", ":")) + "\n")
                raw_count += 1
                for prefix in ("SAT1", "SAT2"):
                    record = extract_object(row, prefix)
                    if record is not None:
                        all_rows.append(record)
            print(
                f"{window_start}..{window_end}: {len(rows)} CDMs; "
                f"{len(all_rows)} valid object-state samples",
                flush=True,
            )

    # One reproducible representative TCA state per catalog object: latest TCA.
    latest = {}
    for record in all_rows:
        key = record["norad_cat_id"]
        if key not in latest or record["epoch_utc"] > latest[key]["epoch_utc"]:
            latest[key] = record
    unique = sorted(latest.values(), key=lambda item: int(item["norad_cat_id"]))

    states_path = output / "spacetrack_cdm_object_states.csv"
    with states_path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=OUT_FIELDS)
        writer.writeheader()
        writer.writerows(unique)

    counts = {}
    frames = {}
    for record in unique:
        counts[record["object_type"]] = counts.get(record["object_type"], 0) + 1
        frames[record["source_frame"]] = frames.get(record["source_frame"], 0) + 1
    report = {
        "source": "Space-Track CDMPublic",
        "query_created_date_range_utc": [start.isoformat(), end.isoformat()],
        "retrieved_at_utc": datetime.now(timezone.utc).isoformat(),
        "raw_cdm_count": raw_count,
        "valid_object_state_samples_before_deduplication": len(all_rows),
        "unique_catalog_objects": len(unique),
        "unique_objects_by_type": counts,
        "unique_objects_by_source_frame": frames,
        "unique_objects_in_current_cowell_frame_gcrs": sum(
            item["normalized_frame"] == "GCRS" for item in unique
        ),
        "unique_objects_ready_for_current_cowell_engine": sum(
            item["propagation_status"] == "READY_GCRS" for item in unique
        ),
        "unique_objects_requiring_frame_transformation_or_review": sum(
            item["propagation_status"] != "READY_GCRS" for item in unique
        ),
        "target_unique_objects": 10000,
        "target_reached_at_catalog_state_level": len(unique) >= 10000,
        "target_reached_at_current_cowell_ready_level": sum(
            item["propagation_status"] == "READY_GCRS" for item in unique
        ) >= 10000,
        "important_limitations": [
            "A CDM state is a single state at time of closest approach, not a continuous ephemeris.",
            "Each object is represented by its latest retrieved TCA state.",
            "ITRF/ITRS states are transformed to GCRS with Astropy and IERS Earth-orientation data when available.",
            "Unsupported frames remain unnormalized and are not counted as Cowell-ready.",
            "No SGP4 is invoked and no GP/TLE mean elements are converted.",
            "A state being syntactically valid does not establish its orbit-determination accuracy.",
            "CDMPublic coverage is conjunction-biased and must not be treated as a representative debris census.",
        ],
    }
    (output / "spacetrack_cdm_acquisition_report.json").write_text(
        json.dumps(report, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
