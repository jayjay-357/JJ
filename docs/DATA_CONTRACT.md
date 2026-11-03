# ORION-AHOP input and data contract

## Canonical units and metadata

The internal Cartesian state uses position in kilometres and velocity in kilometres per second. Epochs must be explicit, and frames/time systems must be retained. Do not compare two objects until their trajectories have been transformed to a common frame and evaluated on a common time grid.

## Supported first-milestone paths

| Input | Current handling | Important condition |
|---|---|---|
| OMM | SGP4 route | Only GP/SGP4 mean-element records are accepted |
| OPM | Cartesian state conversion | Requires epoch, reference frame, and complete position/velocity |
| OEM | Ephemeris/reference record | Not automatically converted to a new initial state |

The KVN parser is a limited subset. It does not yet support XML, multiple OEM segments, covariance blocks, or every optional CCSDS field.

## Frame and time handling

The parser preserves the declared frame and time-system metadata. It does not perform frame transformations or time-scale conversions. The caller must ensure consistent frames and epochs before conjunction screening. This is a critical precondition, not an optional cleanup step.
