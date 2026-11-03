"""SGP4 adapter for supported GP/SGP4 OMM records."""
from datetime import datetime, timezone
from sgp4.api import Satrec, jday
from sgp4.omm import initialize

def propagate_omm(data: dict[str, str], target_epoch: datetime):
    theory = data.get("MEAN_ELEMENT_THEORY", "SGP4").upper()
    if theory not in {"SGP4", "GP"}:
        raise ValueError(f"Unsupported mean-element theory: {theory}")
    satellite = Satrec()
    initialize(satellite, data)
    epoch = target_epoch.astimezone(timezone.utc) if target_epoch.tzinfo else target_epoch.replace(tzinfo=timezone.utc)
    jd, fr = jday(epoch.year, epoch.month, epoch.day, epoch.hour, epoch.minute,
                  epoch.second + epoch.microsecond / 1_000_000)
    error, position, velocity = satellite.sgp4(jd, fr)
    if error:
        raise RuntimeError(f"SGP4 error code: {error}")
    return tuple(position), tuple(velocity)
