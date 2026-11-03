# ORION-AHOP algorithm overview

## 1. Input and compatibility

The parser identifies supported CCSDS KVN message types. Validation checks required fields. Compatibility is determined by the representation and declared mean-element theory, not by the file extension alone:

- OMM with GP/SGP4 mean elements: SGP4 route.
- OPM with Cartesian state: numerical propagation route, subject to valid epoch, frame, units, and force model.
- OEM: supplied ephemeris/reference route; not silently reinitialized as a new orbit.

## 2. Adaptive priority

Normalized indicators are combined:

`S = (w_U U + w_D D + w_C C) / (sum of weights for available indicators)`

Missing indicators are excluded and remaining weights renormalized. The score allocates effort; it is not collision probability. The stateful controller escalates immediately and de-escalates one level at a time after a minimum dwell interval to reduce rapid switching. Weights, thresholds, and dwell time are provisional.

## 3. Propagation and conjunction screening

The SGP4 adapter propagates GP/SGP4 OMM records. The Cartesian RK4 implementation is an educational two-body baseline. The conjunction module screens synchronized trajectories in a shared frame and refines the minimum sampled separation with a bounded constant-relative-velocity approximation.

## 4. Risk estimation boundary

The ORION-QARC package currently provides a classical Monte Carlo reference for a user-defined event predicate, including a 2-D Gaussian encounter-plane disk event helper. A production probability-of-collision workflow still needs validated covariance propagation, encounter-plane construction, hard-body geometry, numerical integration/importance sampling, and independent validation. Quantum amplitude estimation is not implemented in this milestone.

## 5. Validation

Use unit tests, known conjunction cases, time-step convergence, sensitivity studies, and comparison with a trusted reference. Do not describe a screening distance or adaptive score as a collision probability.
