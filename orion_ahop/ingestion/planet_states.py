"""Parser for Planet Labs' public Cartesian state-vector text product.

Planet documents epochs as seconds since J2000 in Terrestrial Time (TT),
positions in J2000 metres, and velocities in J2000 metres/second.
Astropy performs the TT-to-UTC conversion; no SGP4 is involved.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import math
from pathlib import Path

from astropy.time import Time, TimeDelta

from orion_ahop.models import OrbitalState

J2000_TT = Time("2000-01-01T12:00:00", scale="tt")


@dataclass(frozen=True)
class PlanetStateRecord:
    hardware_id: str
    state: OrbitalState
    drag_ballistic_coefficient_kg_m2: float | None
    srp_ballistic_coefficient_kg_m2: float | None
    raw_drag_coefficient: str
    raw_srp_coefficient: str


def _optional_finite_float(value: str) -> float | None:
    try:
        parsed = float(value)
    except ValueError as exc:
        raise ValueError(f"Invalid ballistic coefficient {value!r}.") from exc
    return parsed if math.isfinite(parsed) else None


def parse_planet_states_text(text: str) -> list[PlanetStateRecord]:
    """Parse HWID, TT epoch, J2000 position/velocity, and ballistic coefficients."""
    records: list[PlanetStateRecord] = []
    seen_ids: set[str] = set()
    for line_number, original in enumerate(text.splitlines(), start=1):
        line = original.strip()
        if not line or line.startswith("#"):
            continue
        fields = line.split()
        if len(fields) != 10:
            raise ValueError(
                f"Planet state row {line_number} must contain exactly 10 columns; got {len(fields)}."
            )
        hardware_id = fields[0].strip()
        if not hardware_id:
            raise ValueError(f"Missing hardware ID on line {line_number}.")
        if hardware_id in seen_ids:
            raise ValueError(f"Duplicate hardware ID {hardware_id!r} on line {line_number}.")
        try:
            seconds_since_j2000_tt = float(fields[1])
            components_m = [float(value) for value in fields[2:8]]
        except ValueError as exc:
            raise ValueError(f"Invalid epoch or Cartesian component on line {line_number}.") from exc
        if not math.isfinite(seconds_since_j2000_tt):
            raise ValueError(f"Non-finite TT epoch on line {line_number}.")
        if not all(math.isfinite(value) for value in components_m):
            raise ValueError(f"Non-finite Cartesian component on line {line_number}.")
        try:
            epoch = (J2000_TT + TimeDelta(seconds_since_j2000_tt, format="sec")).utc.to_datetime(
                timezone=timezone.utc
            )
        except Exception as exc:
            raise ValueError(f"Could not convert TT epoch on line {line_number} to UTC.") from exc
        position_km = tuple(value / 1000.0 for value in components_m[:3])
        velocity_km_s = tuple(value / 1000.0 for value in components_m[3:])
        if math.sqrt(sum(value * value for value in position_km)) == 0:
            raise ValueError(f"Zero position vector on line {line_number}.")
        if math.sqrt(sum(value * value for value in velocity_km_s)) == 0:
            raise ValueError(f"Zero velocity vector on line {line_number}.")
        drag_raw, srp_raw = fields[8], fields[9]
        state = OrbitalState(
            epoch=epoch,
            frame="J2000",
            position_km=position_km,
            velocity_km_s=velocity_km_s,
            source_format="PLANET_STATES",
            metadata={
                "source": "Planet Labs public orbital ephemerides",
                "hardware_id": hardware_id,
                "input_time_system": "TT",
                "input_epoch_definition": "seconds since 2000-01-01T12:00:00 TT",
                "output_time_system": "UTC",
                "input_position_units": "m",
                "input_velocity_units": "m/s",
                "output_position_units": "km",
                "output_velocity_units": "km/s",
                "reference_frame": "J2000",
                "sgp4_used": False,
                "norad_id": None,
                "covariance_available": False,
            },
        )
        records.append(PlanetStateRecord(
            hardware_id=hardware_id,
            state=state,
            drag_ballistic_coefficient_kg_m2=_optional_finite_float(drag_raw),
            srp_ballistic_coefficient_kg_m2=_optional_finite_float(srp_raw),
            raw_drag_coefficient=drag_raw,
            raw_srp_coefficient=srp_raw,
        ))
        seen_ids.add(hardware_id)
    if not records:
        raise ValueError("Planet state file contains no records.")
    return records


def load_planet_states_file(path: str | Path) -> list[PlanetStateRecord]:
    return parse_planet_states_text(Path(path).read_text(encoding="utf-8"))
