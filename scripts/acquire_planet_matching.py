"""Acquire and audit Planet Labs' public HWID-to-18SPCS matching report."""
from __future__ import annotations
import argparse
import csv
import json
from pathlib import Path
import re
from urllib.request import Request, urlopen

from orion_ahop.ingestion.planet_matching import parse_planet_matching_text

SOURCE_URL = "https://ephemerides.planet-labs.com/18SPCS_matches_v1.txt"

def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", default="planet_matching_output")
    parser.add_argument("--url", default=SOURCE_URL)
    args = parser.parse_args()
    request = Request(args.url, headers={"User-Agent": "ORION-X-research/1.0"})
    with urlopen(request, timeout=60) as response:
        raw = response.read().decode("utf-8")
    records = parse_planet_matching_text(raw)
    output = Path(args.output_dir)
    output.mkdir(parents=True, exist_ok=True)
    (output / "18SPCS_matches_v1.txt").write_text(raw, encoding="utf-8")
    columns = list(records[0].__dataclass_fields__)
    with (output / "planet_hwid_catalog_crosswalk_review.csv").open(
        "w", newline="", encoding="utf-8"
    ) as stream:
        writer = csv.DictWriter(stream, fieldnames=columns)
        writer.writeheader()
        for record in records:
            row = {key: getattr(record, key) for key in columns}
            row["match_ids"] = "/".join(record.match_ids)
            row["rms_values_km"] = "/".join("hist_or_missing" if value is None else str(value) for value in record.rms_values_km)
            row["correct_name_flags"] = "/".join(str(value).lower() for value in record.correct_name_flags)
            writer.writerow(row)
    epoch_match = re.search(r"^# Epoch:\s*(.+?)\s*$", raw, flags=re.MULTILINE)
    counts = {
        disposition: sum(record.disposition == disposition for record in records)
        for disposition in ("CANDIDATE_ONLY", "MANUAL_REVIEW")
    }
    summary = {
        "provider": "Planet Labs / 18th Space Control Squadron matching report",
        "source_url": args.url,
        "report_epoch": epoch_match.group(1) if epoch_match else None,
        "records_parsed": len(records),
        "disposition_counts": counts,
        "automatic_identity_joins_performed": 0,
        "norad_ids_assigned_to_planet_states": 0,
        "matching_policy": "CANDIDATE_ONLY requires catalogued=true, correct_name=true, one match, match ID equal to CATID, and numeric RMS < 5 km.",
        "limitations": [
            "The source describes matches as best-guess and warns about cross-tagging.",
            "CANDIDATE_ONLY is a review queue label, not an authoritative identity assertion.",
            "Manual verification against a dated catalog and identity history is required before any join.",
            "Hardware IDs and catalog IDs remain separate identifiers.",
            "This crosswalk does not establish common epoch, reference frame, or ephemeris accuracy.",
        ],
    }
    (output / "planet_matching_acquisition_report.json").write_text(
        json.dumps(summary, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(summary, indent=2))

if __name__ == "__main__":
    main()
