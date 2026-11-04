# Planet Labs hardware-ID matching report

Source: https://ephemerides.planet-labs.com/18SPCS_matches_v1.txt

Planet describes this as a **best-guess** association between Planet hardware
IDs (HWIDs) and 18th Space Control Squadron catalog identifiers. The source
states that cross-tagging can make some associations inconsistent. It reports
up to three best TLE matches and says an RMS error below 5 km indicates a
"good" match.

The parser retains the source's identity fields, match candidates, flags, RMS,
and temporary/supplemental identifiers. It labels a row `CANDIDATE_ONLY`
only when the object is officially catalogued, the expected-name flag is true,
exactly one TLE match is listed, that match equals the official CATID, and the
reported RMS is numeric and below 5 km. All other rows are `MANUAL_REVIEW`.

Even a candidate is not an authoritative join. Verify it against a dated copy
of the relevant catalog and its identity history before use. No IDs are
assigned to Planet Cartesian state records by this parser.

## Limitations and intended use

- This is a dated best-guess crosswalk, not a guaranteed identity key.
- CATIDs may be temporary or supplemental during launch/early operations.
- A good TLE-match RMS is not the same as verified identity or a precise
  current ephemeris.
- The report does not establish that a Space-Track row and Planet state refer
  to the same object at the same epoch.
- Never use name similarity alone to join records.
- Keep HWID and catalog ID separate, with source provenance, report epoch,
  RMS, and review disposition.

Use this file to create a reviewable candidate crosswalk only. Do not merge
Planet state vectors into the Space-Track catalog or conjunction pipeline
until identity, epoch, frame, and state provenance have been independently
verified.
