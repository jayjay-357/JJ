"""End-to-end SGP4-to-GCRS-to-Cowell orbital propagation pipeline."""
from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timezone

from orion_ahop.models import CCSDSMessage, OrbitalState
from orion_ahop.propagators.frame_transforms import teme_to_gcrs
from orion_ahop.propagators.force_models import ForceModelConfig
from orion_ahop.propagators.numerical_engine import PropagationResult, propagate_cowell
from orion_ahop.propagators.sgp4_engine import propagate_omm


def propagate_omm_to_gcrs(
    message_or_fields: CCSDSMessage | dict[str, str],
    target_epoch: datetime,
) -> OrbitalState:
    """Propagate an OMM/GP record with SGP4 and convert its TEME state to GCRS."""
    if target_epoch.tzinfo is None or target_epoch.utcoffset() is None:
        raise ValueError("target_epoch must be timezone-aware.")
    position, velocity = propagate_omm(message_or_fields, target_epoch)
    teme_state = OrbitalState(
        epoch=target_epoch.astimezone(timezone.utc),
        frame="TEME",
        position_km=position,
        velocity_km_s=velocity,
        source_format="OMM",
        metadata={"state_source": "SGP4"},
    )
    return teme_to_gcrs(teme_state)


def propagate_omm_to_cowell(
    message_or_fields: CCSDSMessage | dict[str, str],
    target_epoch: datetime,
    duration_s: float,
    force_model: ForceModelConfig | None = None,
    **cowell_kwargs,
) -> PropagationResult:
    """Run the complete OMM/GP -> SGP4 -> GCRS -> Cowell path."""
    gcrs_state = propagate_omm_to_gcrs(message_or_fields, target_epoch)
    config = force_model
    if config is not None:
        config = replace(config)
    return propagate_cowell(
        gcrs_state.position_km,
        gcrs_state.velocity_km_s,
        gcrs_state.epoch,
        duration_s,
        force_model=config,
        frame="GCRS",
        **cowell_kwargs,
    )
