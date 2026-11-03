# ORION-AHOP

**ORION-AHOP (Adaptive Hybrid Orbital Propagation)** is an experimental research framework for selecting compatible orbital-propagation pathways and allocating computational effort through an adaptive controller.

## Current scope
- Limited CCSDS KVN ingestion scaffold for OMM, OPM, and OEM.
- Canonical orbital-state and metadata models.
- Input validation and compatibility checks.
- Combined adaptive score using uncertainty, data age, and conjunction relevance.
- SGP4 adapter for supported GP/SGP4 mean-element OMM records.
- Educational two-body RK4 propagation baseline for Cartesian states.
- DSST adapter interface (not implemented yet).
- Classical Monte Carlo reference for collision-event experiments.

## Important limitations
This is a research prototype, not an operational collision-avoidance service. The KVN parser supports a deliberately limited subset of CCSDS messages; it is not a complete CCSDS implementation. XML is not implemented. OEM is retained as supplied ephemeris/reference data and is not automatically treated as a new initial state. The numerical integrator currently uses a two-body gravity model and is not high fidelity. DSST and the quantum ORION-QARC estimator are design interfaces only; no DSST solver or quantum circuit is included yet.

The adaptive score allocates computational effort. It does **not** directly represent collision probability and cannot override physical compatibility requirements.

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

## CLI
```bash
orion-ahop inspect data/sample/example_omm.kvn
```

## Adaptive score
For normalized indicators in [0, 1]:
`S = w_U U + w_D D + w_C C`
Weights are non-negative and sum to one. Missing indicators are excluded and remaining weights renormalized. Initial thresholds (0.35 and 0.70) are provisional and require calibration.

## Research integrity
Synthetic sample data is labeled. No performance results are claimed. Record data provenance, software versions, coordinate frames, time systems, force-model assumptions, and evaluation settings in experiments.
