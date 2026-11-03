"""Limited CCSDS KVN parser for OMM, OPM, and OEM."""
from pathlib import Path
from orion_ahop.models import CCSDSMessage

def parse_kvn_text(text: str) -> CCSDSMessage:
    metadata: dict[str, str] = {}
    data: dict[str, str] = {}
    in_data = False
    for original in text.splitlines():
        line = original.strip()
        if not line or line.startswith("#"):
            continue
        if line == "META_START":
            in_data = False
            continue
        if line == "META_STOP":
            in_data = True
            continue
        if "=" not in line:
            continue
        key, value = (part.strip() for part in line.split("=", 1))
        if key:
            (data if in_data else metadata)[key] = value
    if "CCSDS_OMM_VERS" in metadata:
        kind = "OMM"
    elif "CCSDS_OPM_VERS" in metadata:
        kind = "OPM"
    elif "CCSDS_OEM_VERS" in metadata:
        kind = "OEM"
    else:
        raise ValueError("Could not identify CCSDS message type from version field.")
    return CCSDSMessage(kind, metadata, data, text)

def parse_kvn_file(path: str | Path) -> CCSDSMessage:
    return parse_kvn_text(Path(path).read_text(encoding="utf-8"))
