"""Conservative parser for Planet Labs' 18 SPCS HWID/CATID matching report."""
from __future__ import annotations
from dataclasses import dataclass
import math

@dataclass(frozen=True)
class PlanetCatalogMatch:
    hardware_id: str
    name_fields: str
    catalog_id: str | None
    rms_km: float | None
    match_ids: tuple[str, ...]
    correct_name: bool
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

def parse_planet_matching_text(text: str) -> list[PlanetCatalogMatch]:
    """Parse the whitespace-delimited report into reviewable crosswalk rows.

    CANDIDATE_ONLY is a conservative report-level screen, never an
    authoritative identity assertion or an automatic catalog join.
    """
    records: list[PlanetCatalogMatch] = []
    seen: set[str] = set()
    for line_number, original in enumerate(text.splitlines(), start=1):
        line = original.strip()
        if not line or line.startswith("#"):
            continue
        fields = line.split()
        if len(fields) < 10:
            raise ValueError(f"Matching report row {line_number} must contain at least 10 fields; got {len(fields)}.")
        # The two name columns may contain spaces. Parse the stable seven
        # rightmost fields and retain the intervening names without guessing
        # where one free-text name ends and the other begins.
        hwid = fields[0]
        name_fields = " ".join(fields[1:-7])
        catid, rms_raw, matches_raw, correct_raw, catalogued_raw, catid9, supplemental = fields[-7:]
        if hwid in seen:
            raise ValueError(f"Duplicate Planet hardware ID {hwid!r} on line {line_number}.")
        if correct_raw.lower() not in {"true", "false"} or catalogued_raw.lower() not in {"true", "false"}:
            raise ValueError(f"Invalid boolean flag on matching report line {line_number}.")
        correct_name = correct_raw.lower() == "true"
        catalogued = catalogued_raw.lower() == "true"
        catalog_id = _optional_text(catid)
        rms = _optional_number(rms_raw)
        match_ids = tuple(value for value in matches_raw.split("/") if value and value != "-")
        reasons: list[str] = []
        if not catalogued: reasons.append("not officially catalogued")
        if not correct_name: reasons.append("expected-name check failed")
        if catalog_id is None: reasons.append("no official CATID")
        if rms is None: reasons.append("no numeric RMS (possibly historical match)")
        elif rms >= 5.0: reasons.append("RMS is not below 5 km")
        if len(match_ids) != 1: reasons.append("zero or multiple TLE match candidates")
        elif catalog_id is not None and match_ids[0] != catalog_id:
            reasons.append("TLE match ID differs from official CATID")
        eligible = (catalogued and correct_name and catalog_id is not None and rms is not None
                    and rms < 5.0 and len(match_ids) == 1 and match_ids[0] == catalog_id)
        records.append(PlanetCatalogMatch(
            hardware_id=hwid, name_fields=name_fields,
            catalog_id=catalog_id, rms_km=rms, match_ids=match_ids,
            correct_name=correct_name, catalogued=catalogued,
            catid_9digit=_optional_text(catid9), catid_supplemental=_optional_text(supplemental),
            disposition="CANDIDATE_ONLY" if eligible else "MANUAL_REVIEW",
            reason=("Meets conservative report-level screening; independently verify against the dated source catalog before joining."
                    if eligible else "; ".join(reasons) or "Insufficient evidence for automatic association."),
        ))
        seen.add(hwid)
    if not records:
        raise ValueError("Planet matching report contains no data rows.")
    return records
