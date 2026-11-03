# ORION-AHOP Cowell Numerical Engine

## Scope of this implementation milestone

The numerical engine integrates an Earth-centred Cartesian state using Cowell's formulation:

\[
\dot{\mathbf r}=\mathbf v, \qquad
\dot{\mathbf v}=\mathbf a(\mathbf r,\mathbf v,t).
\]

The integrator is SciPy's adaptive DOP853 method. The configured acceleration is the sum of central Earth gravity and selected perturbations.

## Implemented force contributions

- Central Earth gravity.
- Earth J2 zonal perturbation.
- Atmospheric drag with Earth co-rotation and a configurable exponential density approximation.
- Solar radiation pressure with a cylindrical Earth-umbra approximation.
- Differential third-body gravity through caller-supplied ephemeris callbacks.

All positions are kilometres, velocities kilometres per second, gravitational parameters km^3/s^2, and returned accelerations km/s^2. Atmospheric density is kg/m^3 and area-to-mass ratio is m^2/kg.

## Important scientific limitations

1. The exponential atmosphere is a simplified model. It is not NRLMSISE-00, JB2008, or another validated operational thermosphere model. Realistic drag studies need a suitable density model, space-weather inputs, and validated object ballistic coefficients.
2. The drag model assumes a co-rotating atmosphere and omits winds and detailed Earth-orientation effects.
3. SRP uses caller-provided geocentric Sun ephemerides, fixed reflectivity and area-to-mass parameters, and a cylindrical umbra. Penumbra and attitude-dependent projected area are not modelled.
4. Third-body effects are only as accurate as the supplied ephemerides and frame consistency.
5. J2 assumes an Earth-equatorial inertial frame. The software does not yet perform TEME/GCRF/ITRF transformations or Earth-orientation/time-scale conversions.
6. DOP853 controls numerical integration error, not force-model error, initial-state uncertainty, or uncertainty in physical parameters.
7. This milestone does not yet implement covariance propagation, validated collision probability, or operational conjunction assessment.

## Numerical controls

- Method: DOP853.
- Relative tolerance: configurable, default 1e-10.
- Position absolute tolerance: configurable, default 1e-9 km.
- Velocity absolute tolerance: configurable, default 1e-12 km/s.
- Maximum integration step: configurable, default 300 s.
- Output sampling interval: configurable, default 60 s.

Output sampling interval and integration maximum step are distinct. The solver may take smaller internal steps to satisfy its error controls.

## Example

```python
from datetime import datetime, timezone
from orion_ahop.propagators.force_models import ForceModelConfig
from orion_ahop.propagators.numerical_engine import propagate_cowell

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

Drag, SRP, and third-body forces must only be enabled when their required physical parameters and ephemerides are supplied and documented.
