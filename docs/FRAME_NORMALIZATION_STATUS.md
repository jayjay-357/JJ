# ORION-X frame-normalization status

## Current frame contracts

| Source or engine | Frame/time contract | Current handling |
|---|---|---|
| Space-Track GP catalog | TEME / UTC, SGP4 mean elements | Catalog identification only; not a Cartesian initial state |
| Planet `planet.states` | J2000 position/velocity; epoch seconds from J2000 TT | TT is converted to UTC; J2000 label is preserved |
| Cowell numerical engine | Earth-centred GCRS Cartesian state | Rejects any frame other than GCRS |
| OEM KVN loader | Earth-centred, explicit `REF_FRAME`, UTC | Preserves the declared frame; does not transform it |

## Why Planet states are not yet sent to Cowell

Planet's public state-vector description identifies the coordinate frame as
"J2000" and the epoch scale as TT. It does not, in that file-format description,
spell out the exact frame realization and origin convention needed to choose a
defensible transformation into the Cowell engine's GCRS state contract.

J2000/EME2000 and GCRS/ICRS are closely related but should not be silently
treated as interchangeable in a precision propagation pipeline. A guessed
rotation or an inappropriate full coordinate transform could introduce a
systematic state error. The ingestion layer therefore preserves the source
frame as `J2000`, and the Cowell engine's existing GCRS-only guard prevents
accidental propagation in the wrong frame.

## Safe next action

Obtain an authoritative Planet definition of the state-vector frame and origin,
or a Planet OEM product with explicit CCSDS metadata (`CENTER_NAME`,
`REF_FRAME`, `TIME_SYSTEM`). Once that convention is confirmed, implement a
dedicated six-component state transformation, including velocity handling,
and validate it against an independent reference or provider-supplied OEM
state at the same epoch.

Do not use the Space-Track TEME catalog fields as a substitute for Cartesian
states. Do not call SGP4 in the new Cowell/DSST route. The legacy OMM/SGP4
pipeline remains separate and is not part of this direct Cartesian path.

## Validation boundary

The successful Planet ingestion test proves parsing, unit conversion, and TT
to UTC conversion for the provider's state-vector product. The HWID crosswalk
audit corroborates selected identities against a dated Space-Track snapshot.
Neither result validates a J2000-to-GCRS transformation, Cowell propagation
accuracy, DSST propagation, conjunction screening, or collision probability.
