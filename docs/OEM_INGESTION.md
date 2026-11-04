# CCSDS OEM KVN ingestion

## Purpose

The OEM loader reads Cartesian ephemeris records from CCSDS Orbit Ephemeris
Message (OEM) files and normalizes them into ORION-AHOP canonical units:
position in km, velocity in km/s, and timezone-aware UTC epochs.

## Supported subset

- CCSDS OEM KVN text format with a version header.
- One or more metadata/data segments.
- Earth-centred segments only.
- Explicit reference frame, UTC time system, start and stop epochs.
- Cartesian rows containing epoch, X, Y, Z, VX, VY, VZ.
- Position units KM or M; velocity units KM/S or M/S. If omitted, conventional
  defaults KM and KM/S are used.
- States are retained in their declared reference frame. No frame transformation
  is performed.

## Explicitly unsupported

- OEM XML.
- Non-UTC time systems such as TAI, TT, or TDB.
- Non-Earth centres.
- Covariance blocks and uncertainty propagation.
- Interpolation, extrapolation, and orbit propagation.
- Optional fields outside the implemented KVN subset.

## Validation

validate_oem_segment checks metadata, vector dimensions, finite components,
non-zero position and velocity, time ordering, duplicate epochs, declared time
coverage, frame consistency, and Earth-centred/UTC constraints.

A successful validation does not establish ephemeris accuracy, independence,
or suitability as ground truth. It does not verify object identity against
Space-Track, transform frames, or provide covariance.

## Usage

Import load_oem_kvn_file and validate_oem_segment from
orion_ahop.ingestion.oem. Parse the file, validate each returned segment, and
only pass valid states to a downstream frame-aware propagation pipeline.
