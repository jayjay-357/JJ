# Planet Labs Cartesian state-vector ingestion

## Source and semantics

Source: https://ephemerides.planet-labs.com/planet.states

Planet documents this file as one row per satellite with a hardware ID, epoch
in seconds since J2000 Terrestrial Time (TT), position in the J2000 frame in
metres, velocity in the J2000 frame in metres/second, and drag/SRP ballistic
coefficients in kg/m².

The parser uses Astropy to convert the TT epoch to UTC and converts the six
Cartesian components to km and km/s. It does not call SGP4. The frame label
J2000 is retained without transformation.

## Critical scope limits

- These are Planet Labs satellites, not a representative debris catalogue.
- A row is one Cartesian state at one epoch, not a time series or full OEM.
- Hardware IDs are not NORAD IDs. No cross-catalog match is assumed.
- This product does not provide covariance in the parsed state-vector rows.
- J2000 states must be transformed consistently before combining with states
  in another frame.
- Planet publishes this data under CC BY-NC 4.0. Attribute Planet Labs and
  respect the non-commercial license terms.

## Acquire

Run `python scripts/acquire_planet_states.py`. The script downloads the live
public file, parses it, and writes the raw source, normalized CSV, and a JSON
acquisition report. GitHub Actions also uploads these outputs as an artifact.

## Research use

This source is suitable for a real-data Cartesian ingestion and propagation
pipeline test on Planet-operated satellites. It does not validate debris
coverage, collision probability, or the complete ORION-X risk pipeline.
