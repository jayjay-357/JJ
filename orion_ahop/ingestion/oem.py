"""Strict CCSDS OEM KVN Cartesian ephemeris loader.

Supports Earth-centred OEM KVN files with UTC epochs and explicit frames.
This is an ingestion layer, not a propagator or frame/time conversion engine.
XML OEM, covariance blocks, and non-UTC time systems are intentionally rejected
until dedicated parsers/converters are implemented and validated.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
import math
import re

from orion_ahop.models import OrbitalState


@dataclass(frozen=True)
class OEMSegment:
    metadata: dict[str, str]
    states: tuple[OrbitalState, ...]


@dataclass(frozen=True)
class StateValidation:
    valid: bool
    errors: tuple[str, ...]
    warnings: tuple[str, ...]


def _parse_epoch(value: str, time_system: str) -> datetime:
    if time_system.upper() != "UTC":
        raise ValueError(f"Unsupported OEM TIME_SYSTEM={time_system!r}; only UTC is currently supported.")
    raw = value.strip()
    if raw.endswith("Z"):
        raw = raw[:-1] + "+00:00"
    try:
        epoch = datetime.fromisoformat(raw)
    except ValueError as exc:
        raise ValueError(f"Invalid OEM epoch {value!r}.") from exc
    if epoch.tzinfo is None:
        epoch = epoch.replace(tzinfo=timezone.utc)
    return epoch.astimezone(timezone.utc)


def _parse_units(metadata: dict[str, str]) -> tuple[float, float, str]:
    distance = metadata.get("DISTANCE_UNITS", "KM").upper()
    if distance == "KM":
        position_scale = 1.0
    elif distance == "M":
        position_scale = 1e-3
    else:
        raise ValueError(f"Unsupported OEM DISTANCE_UNITS={distance!r}.")
    velocity = metadata.get("VELOCITY_UNITS", "KM/S").upper().replace(" ", "")
    if velocity in {"KM/S", "KMSEC"}:
        velocity_scale = 1.0
    elif velocity in {"M/S", "MSEC"}:
        velocity_scale = 1e-3
    else:
        raise ValueError(f"Unsupported OEM VELOCITY_UNITS={velocity!r}.")
    return position_scale, velocity_scale, f"{distance};{velocity}"


def parse_oem_kvn_text(text: str) -> list[OEMSegment]:
    """Parse one or more OEM KVN segments into normalized Cartesian states."""
    lines = text.splitlines()
    if not any(line.strip().startswith("CCSDS_OEM_VERS") for line in lines):
        raise ValueError("Input is not a CCSDS OEM KVN file (missing CCSDS_OEM_VERS).")
    segments: list[OEMSegment] = []
    metadata: dict[str, str] | None = None
    rows: list[OrbitalState] = []
    in_metadata = False
    in_segment_data = False
    header_seen = False

    def finish_segment() -> None:
        nonlocal metadata, rows, in_segment_data
        if metadata is None:
            return
        if not rows:
            raise ValueError("OEM segment contains no Cartesian ephemeris records.")
        segments.append(OEMSegment(dict(metadata), tuple(rows)))
        metadata = None
        rows = []
        in_segment_data = False

    for line_number, original in enumerate(lines, start=1):
        line = original.strip()
        if not line or line.startswith("COMMENT"):
            continue
        if line.startswith("CCSDS_OEM_VERS"):
            if not re.match(r"^CCSDS_OEM_VERS\s*=\s*\d+(\.\d+)?$", line):
                raise ValueError(f"Malformed OEM version header on line {line_number}.")
            header_seen = True
            continue
        if line == "META_START":
            if metadata is not None:
                raise ValueError(f"Nested or unterminated META_START on line {line_number}.")
            metadata = {}
            in_metadata = True
            in_segment_data = False
            continue
        if line == "META_STOP":
            if metadata is None or not in_metadata:
                raise ValueError(f"META_STOP without META_START on line {line_number}.")
            required = ("CENTER_NAME", "REF_FRAME", "TIME_SYSTEM", "START_TIME", "STOP_TIME")
            missing = [key for key in required if not metadata.get(key)]
            if missing:
                raise ValueError("OEM metadata missing required fields: " + ", ".join(missing))
            if metadata["CENTER_NAME"].upper() != "EARTH":
                raise ValueError("Only Earth-centred OEM segments are currently supported.")
            _parse_epoch(metadata["START_TIME"], metadata["TIME_SYSTEM"])
            _parse_epoch(metadata["STOP_TIME"], metadata["TIME_SYSTEM"])
            _parse_units(metadata)
            in_metadata = False
            in_segment_data = True
            continue
        if in_metadata:
            if "=" not in line:
                raise ValueError(f"Malformed OEM metadata on line {line_number}.")
            key, value = (part.strip() for part in line.split("=", 1))
            if key in metadata:
                raise ValueError(f"Duplicate OEM metadata key {key!r} on line {line_number}.")
            metadata[key] = value
            continue
        if in_segment_data:
            if "=" in line:
                key, _ = (part.strip() for part in line.split("=", 1))
                raise ValueError(f"Unexpected key/value field {key!r} in OEM data on line {line_number}.")
            fields = line.split()
            if len(fields) != 7:
                raise ValueError(f"OEM state row on line {line_number} must have epoch and six components.")
            epoch_text, *components = fields
            try:
                epoch = _parse_epoch(epoch_text, metadata["TIME_SYSTEM"])
                values = [float(value) for value in components]
            except (ValueError, TypeError) as exc:
                raise ValueError(f"Invalid OEM state row on line {line_number}: {exc}") from exc
            if not all(math.isfinite(value) for value in values):
                raise ValueError(f"Non-finite OEM state component on line {line_number}.")
            position_scale, velocity_scale, original_units = _parse_units(metadata)
            rows.append(OrbitalState(
                epoch=epoch,
                frame=metadata["REF_FRAME"].strip(),
                position_km=tuple(value * position_scale for value in values[:3]),
                velocity_km_s=tuple(value * velocity_scale for value in values[3:]),
                source_format="OEM",
                metadata={
                    "object_name": metadata.get("OBJECT_NAME"),
                    "object_id": metadata.get("OBJECT_ID"),
                    "center_name": metadata["CENTER_NAME"],
                    "time_system": metadata["TIME_SYSTEM"],
                    "original_units": original_units,
                    "source_format": "CCSDS_OEM_KVN",
                    "covariance_available": False,
                },
            ))
            continue
        if "=" not in line and not line.startswith("CCSDS_"):
            raise ValueError(f"Unexpected OEM content on line {line_number}.")

    if not header_seen:
        raise ValueError("Missing CCSDS OEM version header.")
    if in_metadata:
        raise ValueError("OEM file ended before META_STOP.")
    finish_segment()
    if not segments:
        raise ValueError("OEM file contains no metadata/data segments.")
    return segments


def validate_oem_segment(segment: OEMSegment) -> StateValidation:
    """Check structural and basic physical consistency without claiming accuracy."""
    errors: list[str] = []
    warnings: list[str] = []
    if not segment.states:
        errors.append("Segment has no states.")
        return StateValidation(False, tuple(errors), tuple(warnings))
    metadata = segment.metadata
    try:
        start = _parse_epoch(metadata["START_TIME"], metadata["TIME_SYSTEM"])
        stop = _parse_epoch(metadata["STOP_TIME"], metadata["TIME_SYSTEM"])
        if stop < start:
            errors.append("STOP_TIME precedes START_TIME.")
        if segment.states[0].epoch < start or segment.states[-1].epoch > stop:
            errors.append("State epochs fall outside declared START_TIME/STOP_TIME.")
    except (KeyError, ValueError) as exc:
        errors.append(f"Invalid segment time metadata: {exc}")
    previous: datetime | None = None
    for index, state in enumerate(segment.states):
        if state.frame != metadata.get("REF_FRAME"):
            errors.append(f"State {index} frame does not match segment REF_FRAME.")
        if len(state.position_km) != 3 or len(state.velocity_km_s) != 3:
            errors.append(f"State {index} does not contain three position and velocity components.")
            continue
        values = (*state.position_km, *state.velocity_km_s)
        if not all(math.isfinite(value) for value in values):
            errors.append(f"State {index} contains non-finite components.")
        if math.sqrt(sum(value * value for value in state.position_km)) <= 0:
            errors.append(f"State {index} has zero position magnitude.")
        if math.sqrt(sum(value * value for value in state.velocity_km_s)) <= 0:
            errors.append(f"State {index} has zero velocity magnitude.")
        if previous is not None:
            if state.epoch == previous:
                errors.append(f"Duplicate epoch at state {index}.")
            elif state.epoch < previous:
                errors.append(f"Epoch order decreases at state {index}.")
        previous = state.epoch
    if metadata.get("TIME_SYSTEM", "").upper() != "UTC":
        errors.append("Only UTC time system is currently supported.")
    if metadata.get("CENTER_NAME", "").upper() != "EARTH":
        errors.append("Only Earth-centred segments are currently supported.")
    warnings.append("Validation checks structure and basic consistency, not ephemeris accuracy.")
    warnings.append("No covariance or uncertainty information was loaded.")
    return StateValidation(not errors, tuple(errors), tuple(warnings))


def load_oem_kvn_file(path: str | Path) -> list[OEMSegment]:
    """Read and parse a UTF-8 CCSDS OEM KVN file."""
    return parse_oem_kvn_text(Path(path).read_text(encoding="utf-8"))
