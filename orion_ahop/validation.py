"""Input validation and propagation compatibility."""
from orion_ahop.models import CCSDSMessage

class CompatibilityError(ValueError):
    pass

_REQUIRED = {
    "OMM": ("OBJECT_ID", "EPOCH", "MEAN_MOTION", "ECCENTRICITY", "INCLINATION",
            "RA_OF_ASC_NODE", "ARG_OF_PERICENTER", "MEAN_ANOMALY"),
    "OPM": ("EPOCH", "REF_FRAME", "X", "Y", "Z", "X_DOT", "Y_DOT", "Z_DOT"),
    "OEM": ("START_TIME", "STOP_TIME", "CENTER_NAME", "REF_FRAME"),
}

def validate_message(message: CCSDSMessage) -> list[str]:
    if message.message_type not in _REQUIRED:
        return [f"Unsupported message type: {message.message_type}"]
    errors = [f"Missing required {message.message_type} field: {key}"
              for key in _REQUIRED[message.message_type] if key not in message.data]
    if message.message_type == "OMM":
        theory = message.data.get("MEAN_ELEMENT_THEORY", "SGP4").upper()
        if theory not in {"SGP4", "GP"}:
            errors.append(f"OMM mean-element theory {theory!r} is not supported by SGP4.")
    return errors

def propagation_path(message: CCSDSMessage) -> str:
    errors = validate_message(message)
    if errors:
        raise CompatibilityError("; ".join(errors))
    return {"OMM": "SGP4", "OPM": "NUMERICAL", "OEM": "EPHEMERIS_REFERENCE"}[message.message_type]
