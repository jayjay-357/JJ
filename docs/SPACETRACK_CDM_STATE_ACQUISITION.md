# Space-Track CDM Cartesian-State Acquisition

This acquisition path retrieves public Space-Track `CDMPublic` records and extracts the two object state vectors reported at each conjunction's time of closest approach (TCA).

## Why CDMs

A CDM contains each object's Cartesian position and velocity, a TCA epoch, object designator/type, and a reference-frame label. This is materially different from Space-Track GP/OMM mean elements. This workflow does not invoke SGP4 and does not derive Cartesian states from TLE/GP mean elements.

## Run

GitHub Actions → **Acquire Space-Track CDM Cartesian states** → **Run workflow**.

The repository must have the Actions secrets `SPACETRACK_IDENTITY` and `SPACETRACK_PASSWORD` configured. The default query window starts 2018-01-01 and ends on 2026-11-04; change the dates in the workflow form if needed. Queries are split into calendar-month windows.

## Outputs

- `spacetrack_cdm_public_raw.jsonl`: raw CDM records, one JSON object per line.
- `spacetrack_cdm_object_states.csv`: one latest-TCA state per numeric catalog designator.
- `spacetrack_cdm_acquisition_report.json`: counts, frame coverage, and readiness totals.

Position and velocity are normalized to km and km/s. ITRF/ITRS states are transformed to GCRS with Astropy using IERS Earth-orientation data when available. GCRS inputs are retained. Other frames, non-Earth-centred records, invalid vectors, and non-numeric designators are excluded or left unnormalized as appropriate.

## Scientific limits

1. A CDM state is a single Cartesian sample at TCA, not a continuous ephemeris or a catalog-wide orbit history.
2. The latest retrieved TCA sample is selected for each object. The objects therefore have different epochs.
3. CDMPublic data are conjunction-biased. They do not represent a random or complete census of all tracked objects or all debris.
4. The reported 10,000-object target is met only if the report shows at least 10,000 unique numeric designators with `READY_GCRS` status. A high raw CDM count is not sufficient.
5. A GCRS-ready state is syntactically suitable for the current Cowell input interface, but this alone does not establish orbit-determination accuracy, LEO membership, or force-model validity.
6. The current DSST adapter is not yet a validated end-to-end propagator. Do not claim that the states have passed DSST propagation until that engine is implemented and independently tested.
7. Covariance is not exported by this first dataset pipeline. Do not calculate new collision probabilities from these state vectors alone.
8. Source data terms and Space-Track rate limits must be respected. The workflow queries by month and should not be repeatedly launched to poll for data.

The authoritative TraCSS CDM specification documents state-vector units and reference frames, including ITRF for CCSDS/Space-Track-style products and EME2000 for the TraCSS-specific JSON format. The Space-Track public CDM schema should be checked against the actual returned records before treating any field mapping as final.
