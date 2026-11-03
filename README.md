# ORION-AHOP

**ORION-AHOP** is the orbital-propagation foundation of ORION-X. The selected primary propagation formulation is Cowell's Cartesian numerical method, integrated with an adaptive DOP853 solver and configurable perturbing-force models.

## Current implementation

- Limited CCSDS KVN ingestion scaffold for OMM, OPM, and OEM.
- Canonical orbital-state and metadata models.
- Input validation and compatibility checks.
- Adaptive DOP853 integration of Cowell's equations for GCRS Cartesian initial states.
- Astropy TEME-to-GCRS position/velocity transformation for SGP4 states (covariance transformation is not yet implemented).
- IERS-corrected celestial-intermediate-pole direction and a documented first-order rigid-Earth spin vector for GCRS J2 and atmospheric-drag calculations.
- Central Earth gravity and configurable J2 perturbation.
- Optional atmospheric drag using a configurable exponential-density approximation.
- Optional solar radiation pressure using a caller-supplied Sun ephemeris and cylindrical-umbra approximation.
- Optional differential third-body gravity using caller-supplied ephemerides.
- Numerical tests for force contributions, solver output, and two-body energy conservation.
- Classical Monte Carlo reference interface for later collision-event experiments.

## Important implementation boundaries

This is a research prototype, not an operational collision-avoidance service. The KVN parser supports a deliberately limited subset of CCSDS messages; it is not a complete CCSDS implementation. XML is not implemented. OEM is retained as supplied ephemeris/reference data and is not yet interpolated into Cowell initial conditions.

The Cowell engine accepts GCRS Cartesian initial states. SGP4 outputs TEME states, which must be converted with `teme_to_gcrs` before Cowell propagation. The transformation rejects covariance inputs until a full 6x6 covariance Jacobian is implemented. Cowell automatically uses local IERS data for the Earth pole when J2 or drag is enabled; it disables automatic network refresh and rejects epochs outside the available celestial-pole-correction range. The spin vector is a first-order approximation using nominal Earth rotation directed along the corrected celestial intermediate pole. It does not include length-of-day corrections, polar-motion rates, or sub-daily variations. Validated operational atmospheric-density models, high-degree Earth gravity, object attitude modelling, covariance propagation, conjunction assessment, and the ORION-QARC quantum circuit remain future implementation tasks.

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
    frame="GCRS",
)

if not result.success:
    raise RuntimeError(result.message)
```

## Research integrity

No accuracy or performance advantage is claimed until the engine is tested against an independent reference trajectory. Record data provenance, software versions, coordinate frames, time systems, force-model assumptions, physical parameters, solver tolerances, and evaluation settings in every experiment.


## CelesTrak data acquisition

A manual GitHub Actions workflow is available at **Actions → Acquire CelesTrak orbital sample → Run workflow**. It retrieves GP orbital elements and matching SATCAT metadata from the official CelesTrak endpoints, joins records by NORAD catalog ID, and uploads a CSV sample plus a JSON provenance report as a workflow artifact.

Inputs:
- `GROUP`: a documented CelesTrak group such as `STATIONS`, `FENGYUN-1C-DEB`, or `COSMOS-2251-DEB`.
- `NAME`: a documented object-name substring, such as `R/B`.
- `CATNR`: one NORAD catalog number.

The output is a query-defined sample, not a complete catalog. The maximum-record setting truncates the GP response after download and therefore does not reduce the size of the provider response. The workflow caches responses and reuses them for up to two hours, sends a descriptive User-Agent, and stops on provider errors without automatic retry. Do not repeatedly rerun the workflow to poll for updates.

SATCAT object type is recorded separately from operational status. GP mean elements are inputs for SGP4, not direct Cowell Cartesian initial states. This acquisition does not provide covariance; collision probability must remain unquantified unless valid covariance is obtained separately. Review `acquisition_report.json` before using the sample in an experiment.
