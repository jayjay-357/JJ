# ORION-X Processed Orbital Dataset

This directory contains processed outputs from the ORION-X orbital-data acquisition step.

## Dataset snapshot

- Reference date: 2026-11-03 UTC
- GP orbital records: 69,790 unique NORAD catalog IDs
- SATCAT records: 71,228 unique NORAD catalog IDs
- GP records matched to SATCAT: 68,635
- GP records without a SATCAT match: 1,155
- Recognized GP/SATCAT object-type disagreements: 36

## Preliminary classification

| Object class | Count |
|---|---:|
| Debris | 34,565 |
| Satellite / payload | 27,295 |
| Rocket body | 6,617 |
| Unknown | 1,313 |

## Preliminary LEO subsets

- Recent, non-decayed LEO candidates: 28,310
- Recent, non-decayed LEO-crossing candidates: 1,703

These are screening subsets, not validated conjunction-assessment inputs.

## Source data

- Space-Track GP orbital elements
- Space-Track SATCAT object catalog

The original source files should be retained separately and unchanged. Record their retrieval timestamps and account/API query details in the research log.

## Important scientific limitations

1. GP/TLE mean elements are intended for SGP4. They must not be treated directly as precise osculating elements for Cowell propagation.
2. The 30-day epoch cutoff is a preliminary freshness filter, not proof of orbit accuracy.
3. Twenty future-dated epochs were flagged for review.
4. Object classification and operational status are different. A payload is not automatically an active satellite.
5. The catalog is a merged snapshot, not a validated conjunction-assessment catalog. Covariance, frame/time consistency, and orbit quality still need validation.

## Large CSV files

The CSV outputs are intentionally not committed in this initial GitHub update because the master catalog is approximately 41 MB and the other CSVs are also large. Git LFS tracking is configured separately; the actual LFS objects must still be uploaded from a Git client with Git LFS enabled. Do not treat this README or the acquisition report as a substitute for the CSV data files.
