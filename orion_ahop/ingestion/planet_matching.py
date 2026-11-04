"""Conservative parser for Planet Labs' 18 SPCS HWID/CATID matching report."""
from __future__ import annotations
from dataclasses import dataclass
import math
import re

@dataclass(frozen=True)
class PlanetCatalogMatch:
    hardware_id: str
    name_fields: str
    catalog_id: str | None
    rms_values_km: tuple[float | None, ...]
    match_ids: tuple[str, ...]
    correct_name_flags: tuple[bool, ...]
    catalogued: bool
    catid_9digit: str | None
    catid_supplemental: str | None
    disposition: str
    reason: str

def _optional_number(value: str) -> float | None:
    try:
        number = float(value)
    except ValueError:
        return None
    return number if math.isfinite(number) else None

def _optional_text(value: str) -> str | None:
    return None if value in {"", "-"} else value

def _is_rms_list(value: str) -> bool:
    parts = value.split("/")
    return bool(parts) and all(part in {"-", ""} or part.lower() == "hist" or _optional_number(part) is not None for part in parts)

def _is_match_list(value: str) -> bool:
    return value == "-" or (bool(value) and all(re.fullmatch(r"[A-Za-z0-9_-]+", part) for part in value.split("/")))

def _is_flag_list(value: str) -> bool:
    return bool(value) and all(part.lower() in {"true", "false"} for part in value.split("/"))

def parse_planet_matching_text(text: str) -> list[PlanetCatalogMatch]:
    """Parse report rows while retaining slash-separated best-match arrays.

    The two spacecraft-name fields can contain spaces, so their exact split is
    intentionally not guessed. CANDIDATE_ONLY is a report-level screen only.
    """
    records: list[PlanetCatalogMatch] = []
    seen: set[str] = set()
    for line_number, original in enumerate(text.splitlines(), start=1):
        line = original.strip()
        if not line or line.startswith("#"):
            continue
        fields = line.split()
        if len(fields) < 10:
            raise ValueError(f"Matching report row {line_number} has too few fields: {fields!r}")
        hwid = fields[0]
        if hwid in seen:
            raise ValueError(f"Duplicate Planet hardware ID {hwid!r} on line {line_number}.")
        # Find CATID followed by the report's aligned RMS, TLE-match and
        # correct-name arrays. The names before CATID are free text.
        column_index = None
        for index in range(2, len(fields) - 6):
            if (_is_rms_list(fields[index + 1])
                and _is_match_list(fields[index + 2])
                and _is_flag_list(fields[index + 3])
                and fields[index + 4].lower() in {"true", "false"}):
                column_index = index
                break
        if column_index is None:
            raise ValueError(f"Could not identify matching-report columns on line {line_number}: {fields!r}")
        catid = fields[column_index]
        rms_raw = fields[column_index + 1]
        matches_raw = fields[column_index + 2]
        flags_raw = fields[column_index + 3]
        catalogued_raw = fields[column_index + 4]
        catid9, supplemental = fields[column_index + 5:column_index + 7]
        if len(fields) != column_index + 7:
            raise ValueError(f"Unexpected trailing fields on matching report line {line_number}: {fields!r}")
        rms_values = tuple(_optional_number(value) for value in rms_raw.split("/"))
        match_ids = tuple() if matches_raw == "-" else tuple(matches_raw.split("/"))
        correct_flags = tuple(value.lower() == "true" for value in flags_raw.split("/"))
        catalogued = catalogued_raw.lower() == "true"
        catalog_id = _optional_text(catid)
        reasons: list[str] = []
        if not catalogued: reasons.append("not officially catalogued")
        if len(correct_flags) != 1 or not correct_flags[0]:
            reasons.append("expected-name check is false or ambiguous")
        if catalog_id is None: reasons.append("no official CATID")
        if len(rms_values) != 1 or rms_values[0] is None:
            reasons.append("RMS is historical, missing, or has multiple candidates")
        elif rms_values[0] >= 5.0:
            reasons.append("RMS is not below 5 km")
        if len(match_ids) != 1:
            reasons.append("multiple or missing TLE match candidates")
        elif catalog_id is not None and match_ids[0] != catalog_id:
            reasons.append("TLE match ID differs from official CATID")
        eligible = (
            catalogued and len(correct_flags) == 1 and correct_flags[0]
            and catalog_id is not None and len(rms_values) == 1
            and rms_values[0] is not None and rms_values[0] < 5.0
            and len(match_ids) == 1 and match_ids[0] == catalog_id
        )
        records.append(PlanetCatalogMatch(
            hardware_id=hwid,
            name_fields=" ".join(fields[1:column_index]),
            catalog_id=catalog_id,
            rms_values_km=rms_values,
            match_ids=match_ids,
            correct_name_flags=correct_flags,
            catalogued=catalogued,
            catid_9digit=_optional_text(catid9),
            catid_supplemental=_optional_text(supplemental),
            disposition="CANDIDATE_ONLY" if eligible else "MANUAL_REVIEW",
            reason=("Meets conservative report-level screening; independently verify against the dated source catalog before joining."
                    if eligible else "; ".join(reasons) or "Insufficient evidence for automatic association."),
        ))
        seen.add(hwid)
    if not records:
        raise ValueError("Planet matching report contains no data rows.")
    return records
