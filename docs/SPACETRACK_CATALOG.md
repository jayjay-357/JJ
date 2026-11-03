# Space-Track catalog acquisition

## Purpose and scope

The Space-Track acquisition workflow retrieves the recent on-orbit GP catalog for object identification, classification, and cross-source matching only. It is deliberately separate from propagation-state ingestion.

The query requests the latest GP record for each on-orbit object with an epoch in the previous 10 days:

`/basicspacedata/query/class/gp/EPOCH/%3Enow-10/DECAY_DATE/null-val/format/json`

The JSON representation is an encoding of the same GP/OMM mean-element product; changing XML to JSON does not turn it into a Cartesian ephemeris.

## Run

1. Add two repository Actions secrets:
   - `SPACETRACK_IDENTITY`: the email used for the Space-Track account.
   - `SPACETRACK_PASSWORD`: the account password.
2. Open **Actions → Acquire Space-Track object catalog → Run workflow**.
3. Select the maximum number of unique NORAD IDs to retain.
4. Download the generated workflow artifact.

The workflow checks out `work/orion-ahop-earth-orientation`. Results are uploaded as an Actions artifact and are not committed to Git.

## Outputs

- `spacetrack_object_catalog.csv`: normalized catalog fields and object classification.
- `spacetrack_gp_raw.json`: original provider response for provenance.
- `spacetrack_acquisition_report.json`: retrieval time, record counts, duplicates, missing IDs, truncation, object-type counts, mean-element-theory counts, and explicit limitations.

Raw responses are cached for up to one hour to respect the Space-Track GP retrieval frequency. The workflow is manual-only; do not repeatedly dispatch it to poll for updates.

## Scientific boundary

Space-Track GP records are General Perturbations mean elements, commonly tagged with `MEAN_ELEMENT_THEORY=SGP4`. They are not Cartesian position/velocity states. This workflow does not call SGP4, does not convert GP mean elements into Cartesian states, and does not send these records to Cowell or DSST.

Use NORAD IDs and metadata to match records against independently acquired Cartesian OPM states or reference OEM/OCM ephemerides. If an object has no independently validated Cartesian state, mark it as catalog-identified but not propagation-ready. Do not count it as successfully propagated.

## API policy and security

Space-Track requires an account and session-based authentication. Credentials are read only from GitHub Actions secrets; never put them in source code, workflow files, artifacts, logs, or chat. The workflow makes one GP catalog query when its one-hour cache is stale. Follow the current [Space-Track API usage guidelines](https://www.space-track.org/documentation), including its GP retrieval frequency and request-rate limits. Do not use multiple accounts to bypass limits.
