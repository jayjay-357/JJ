"""SGP4 adapter for supported GP/SGP4 OMM records."""
from datetime import datetime, timezone
from sgp4.api import Satrec, jday
from sgp4.omm import initialize
from orion_ahop.models import CCSDSMessage


def propagate_omm(message_or_fields: CCSDSMessage | dict[str, str], target_epoch: datetime):
    """Propagate an OMM message or flattened OMM field mapping to target_epoch.

    Position and velocity returned by python-sgp4 are TEME km and km/s.
    This function does not transform them into another reference frame.
    """
    if isinstance(message_or_fields, CCSDSMessage):
        if message_or_fields.message_type != "OMM":
            raise ValueError("propagate_omm requires an OMM message.")
        fields = {**message_or_fields.metadata, **message_or_fields.data}
    else:
        fields = dict(message_or_fields)

    theory = fields.get("MEAN_ELEMENT_THEORY", "SGP4").upper()
    if theory not in {"SGP4", "GP"}:
        raise ValueError(f"Unsupported mean-element theory: {theory}")
    satellite = Satrec()
    initialize(satellite, fields)

    epoch = (target_epoch.astimezone(timezone.utc) if target_epoch.tzinfo
             else target_epoch.replace(tzinfo=timezone.utc))
    jd, fraction = jday(epoch.year, epoch.month, epoch.day, epoch.hour,
                        epoch.minute, epoch.second + epoch.microsecond / 1_000_000)
    error, position, velocity = satellite.sgp4(jd, fraction)
    if error:
        raise RuntimeError(f"SGP4 propagation failed with error code {error}.")
    return tuple(position), tuple(velocity)
