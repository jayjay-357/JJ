"""Convert supported CCSDS messages into propagation-ready records."""
from __future__ import annotations
from datetime import datetime
from orion_ahop.models import CCSDSMessage, OrbitalState
from orion_ahop.validation import validate_message, CompatibilityError


def _parse_epoch(value: str) -> datetime:
    normalized = value.strip().replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(normalized)
    except ValueError as exc:
        raise ValueError(f"Unsupported CCSDS epoch value: {value!r}") from exc


def combined_fields(message: CCSDSMessage) -> dict[str, str]:
    """Return metadata and data fields in one mapping (data takes precedence)."""
    return {**message.metadata, **message.data}


def opm_to_state(message: CCSDSMessage) -> OrbitalState:
    if message.message_type != "OPM":
        raise CompatibilityError("opm_to_state requires an OPM message.")
    errors = validate_message(message)
    if errors:
        raise CompatibilityError("; ".join(errors))
    fields = combined_fields(message)
    return OrbitalState(
        epoch=_parse_epoch(fields["EPOCH"]),
        frame=fields["REF_FRAME"],
        position_km=(float(fields["X"]), float(fields["Y"]), float(fields["Z"])),
        velocity_km_s=(float(fields["X_DOT"]), float(fields["Y_DOT"]), float(fields["Z_DOT"])),
        source_format="OPM",
        metadata={"center_name": fields.get("CENTER_NAME", "EARTH"),
                  "time_system": fields.get("TIME_SYSTEM", "UTC")},
    )
