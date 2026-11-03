"""Input inspection orchestration."""
from pathlib import Path
from orion_ahop.ingestion.ccsds_kvn import parse_kvn_file
from orion_ahop.validation import validate_message, propagation_path

def inspect_file(path: str | Path):
    message = parse_kvn_file(path)
    errors = validate_message(message)
    return {"message_type": message.message_type, "object_id": message.data.get("OBJECT_ID"),
            "compatibility_path": None if errors else propagation_path(message),
            "valid": not errors, "errors": errors, "metadata": message.metadata}
