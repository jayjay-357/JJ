"""Acquire and normalize Planet Labs' publicly published state-vector file."""
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from urllib.request import Request, urlopen

from orion_ahop.ingestion.planet_states import parse_planet_states_text

SOURCE_URL = "https://ephemerides.planet-labs.com/planet.states"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", default="planet_states_output")
    parser.add_argument("--url", default=SOURCE_URL)
    args = parser.parse_args()
    request = Request(args.url, headers={"User-Agent": "ORION-X-research/1.0"})
    with urlopen(request, timeout=60) as response:
        raw = response.read().decode("utf-8")
    records = parse_planet_states_text(raw)
    output = Path(args.output_dir)
    output.mkdir(parents=True, exist_ok=True)
    (output / "planet.states").write_text(raw, encoding="utf-8")
    with (output / "planet_states_cartesian.csv").open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=[
            "hardware_id", "epoch_utc", "frame", "x_km", "y_km", "z_km",
            "vx_km_s", "vy_km_s", "vz_km_s", "drag_ballistic_coefficient_kg_m2",
            "srp_ballistic_coefficient_kg_m2",
        ])
        writer.writeheader()
        for record in records:
            state = record.state
            writer.writerow({
                "hardware_id": record.hardware_id,
                "epoch_utc": state.epoch.isoformat(),
                "frame": state.frame,
                "x_km": state.position_km[0], "y_km": state.position_km[1],
                "z_km": state.position_km[2], "vx_km_s": state.velocity_km_s[0],
                "vy_km_s": state.velocity_km_s[1], "vz_km_s": state.velocity_km_s[2],
                "drag_ballistic_coefficient_kg_m2": record.drag_ballistic_coefficient_kg_m2,
                "srp_ballistic_coefficient_kg_m2": record.srp_ballistic_coefficient_kg_m2,
            })
    summary = {
        "provider": "Planet Labs",
        "source_url": args.url,
        "records_parsed": len(records),
        "unique_hardware_ids": len({r.hardware_id for r in records}),
        "reference_frame": "J2000",
        "input_time_system": "TT",
        "output_time_system": "UTC",
        "position_units_output": "km",
        "velocity_units_output": "km/s",
        "norad_ids_assigned": 0,
        "covariance_loaded": False,
        "sgp4_used": False,
        "limitations": [
            "Planet's published state vectors cover its operational satellites, not the full debris population.",
            "Hardware IDs are not automatically mapped to NORAD catalog IDs.",
            "Each row is a state at one epoch, not a time series or complete OEM trajectory.",
            "The file does not provide covariance in this state-vector product.",
            "J2000 is preserved as supplied; no frame transformation is performed.",
            "Non-finite ballistic coefficient values are represented as null while raw values remain in the source file.",
            "Planet's published data is licensed CC BY-NC 4.0; observe attribution and non-commercial restrictions.",
        ],
    }
    (output / "planet_states_acquisition_report.json").write_text(
        json.dumps(summary, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
