# Independent orbital-state ingestion

## Purpose

The independent-state pipeline supplies initial Cartesian states to numerical
propagators without deriving them from Space-Track GP/OMM mean elements. The
Space-Track catalog remains an object-identification and classification source.

## Current implementation milestone

`orion_ahop.ingestion.keplerian` converts explicitly supplied Earth-centred,
elliptic **osculating** Keplerian elements at a known epoch into Cartesian
position (km) and velocity (km/s). It solves Kepler's equation and applies the
perifocal-to-inertial rotation. It does not propagate the orbit and does not
call SGP4.

The caller must provide:
- semi-major axis in km;
- eccentricity;
- inclination, RAAN, argument of perigee, and mean anomaly in degrees;
- a timezone-aware epoch;
- an explicit inertial reference-frame label;
- source provenance and, where available, an object identifier.

## Important input restrictions

1. Do not pass Space-Track GP/OMM mean elements to this converter. They are
   marked with SGP4 mean-element theory and are not osculating elements.
2. The converter currently supports Earth-centred elliptic orbits only.
3. The source must explicitly establish that the supplied elements are
   osculating and define their frame, epoch, and time system. A frame label
   supplied by the caller is preserved; this module does not transform frames.
4. The module does not infer UTC from an epoch whose time scale is unspecified.
   Resolve the source time scale before constructing the timezone-aware epoch.
5. The two-body conversion is an initial-state conversion, not an accuracy
   validation. Perturbations and orbit determination errors remain outside
   this conversion.

## ESA Space Debris: The Origin dataset

The ESA Kelvins documentation describes its element columns as epoch days from
JD2000, semi-major axis (km), eccentricity, inclination (degrees), mean anomaly
(degrees), argument of perigee (degrees), and RAAN (degrees), in EME2000.
Its challenge description identifies the debris sample as GEO. It can be used
as a non-LEO conversion test source after the exact epoch time-scale convention
is established; it must not be presented as LEO validation data.

## Next integration steps

- Add a source-specific ESA file parser only after its epoch time scale and
  file conventions have been verified against the archive.
- Add independent reference checks for converted states.
- Implement Cartesian-state loaders with explicit units, frame, epoch, and
  provenance (for example, an OEM/ephemeris reader).
- Connect validated states to Cowell and a separately validated DSST adapter.
- Keep source coverage, matched-object counts, and propagation-eligible counts
  separate. Do not extrapolate one source's coverage to the entire catalog.
