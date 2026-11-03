# ORION-AHOP

**ORION-AHOP** is the orbital-propagation foundation of ORION-X. The selected primary propagation formulation is Cowell's Cartesian numerical method, integrated with an adaptive DOP853 solver and configurable perturbing-force models.

## Current implementation

- Limited CCSDS KVN ingestion scaffold for OMM, OPM, and OEM.
- Canonical orbital-state and metadata models.
- Input validation and compatibility checks.
- Adaptive DOP853 integration of Cowell's equations for Cartesian initial states.
- Central Earth gravity and configurable J2 perturbation.
- Optional atmospheric drag using a configurable exponential-density approximation.
- Optional solar radiation pressure using a caller-supplied Sun ephemeris and cylindrical-umbra approximation.
- Optional differential third-body gravity using caller-supplied ephemerides.
- Numerical tests for force contributions, solver output, and two-body energy conservation.
- Classical Monte Carlo reference interface for later collision-event experiments.

## Important implementation boundaries

This is a research prototype, not an operational collision-avoidance service. The KVN parser supports a deliberately limited subset of CCSDS messages; it is not a complete CCSDS implementation. XML is not implemented. OEM is retained as supplied ephemeris/reference data and is not yet interpolated into Cowell initial conditions.

The Cowell engine currently accepts Cartesian initial states in an Earth-centred inertial frame. Frame transformations, time-scale conversions, validated operational atmospheric-density models, high-degree Earth gravity, object attitude modelling, covariance propagation, conjunction assessment, and the ORION-QARC quantum circuit remain future implementation tasks. The existing OMM/SGP4 compatibility adapter is retained as a data-initialization component pending a validated TEME-to-inertial state-conversion workflow; it is not the selected long-term propagation engine.

The exponential atmosphere and cylindrical SRP shadow are simplified research approximations. Enabling drag, SRP, or third-body forces requires documented physical parameters and consistent ephemerides. DOP853 controls numerical integration error; it does not remove errors in the force model or initial orbit.

## Install

Python 3.10+ is recommended.

```bash
python -m venv .venv
# Windows: .venv\\Scripts\\activate
# macOS/Linux: source .venv/bin/activate
pip install -e ".[dev]"
```

## Tests

```bash
pytest
```

## Current numerical example

```python
from datetime import datetime, timezone
from orion_ahop.propagators import ForceModelConfig, propagate_cowell

result = propagate_cowell(
    position_km=(7000.0, 0.0, 0.0),
    velocity_km_s=(0.0, 7.5, 0.0),
    epoch=datetime(2026, 1, 1, tzinfo=timezone.utc),
    duration_s=86400.0,
    force_model=ForceModelConfig(include_j2=True),
)

if not result.success:
    raise RuntimeError(result.message)
```

## Research integrity

No accuracy or performance advantage is claimed until the engine is tested against an independent reference trajectory. Record data provenance, software versions, coordinate frames, time systems, force-model assumptions, physical parameters, solver tolerances, and evaluation settings in every experiment.
