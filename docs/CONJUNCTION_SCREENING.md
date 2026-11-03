# Conjunction screening module

The first conjunction module accepts synchronized, already-propagated Cartesian trajectories. Every object must use the same time grid, frame, and units. Positions are in km, velocities in km/s, and time offsets in seconds.

For each unique pair, the module finds the minimum sampled separation. If that sample is inside the configured screening distance, it applies a constant-relative-velocity refinement:

`dt = - (r_rel · v_rel) / (v_rel · v_rel)`

The time offset is bounded to half the smaller adjacent sample interval. The refined miss distance is computed from `r_rel + v_rel * dt`.

## Interpretation and limitations

- The screening distance is a user-configured computational filter, not a collision threshold.
- The refinement assumes locally constant relative velocity.
- Sparse samples, strong curvature, mismatched epochs/frames, or inaccurate input trajectories can miss or misplace conjunctions.
- The module currently does not perform adaptive time stepping, covariance propagation, encounter-plane construction, or probability-of-collision integration.
- A candidate is a geometric close approach only; it is not automatically a collision warning.

Before operational-style claims, validate against known conjunction cases or a trusted reference implementation and perform timestep-convergence tests.
