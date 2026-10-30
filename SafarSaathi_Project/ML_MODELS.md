# SafarSaathi ML guide

## Latest India-scope release

Current evidence: `release/india_scope_20261025_03/`. Six saved models now load:
the four preserved models below plus the separately named
`north_indian_cyclone_count_forecaster` and `india_pm25_exposure_forecaster`.
Both new models are TRAINED_BUT_EXPERIMENTAL. They predict archived tropical
counts in one ocean basin and modeled national PM2.5 exposure respectively.
They do not replace the untrained India-wide multi-disaster or destination-stress
tasks. The historical indicator view covers national years 2011–2024 and all 36
State/UT visit returns for 2023–2024, with source estimation/revision flags.

See [INDIA_SCOPE_MODELS.md](docs/INDIA_SCOPE_MODELS.md) for exact targets,
observations, leakage rules, source terms, API contracts and reproducibility.
Original raw data, registry entries/artifacts, legacy archive and earlier
releases remain preserved. Earlier sections below describe those earlier models.

## Previous completion update — preserved four-model release

The current release is `release/final_working_20261025_02/`. The historical
annual and review sections below retain their original definitions and scores.
Two additional models are registered separately; original entries are preserved.

Monthly FTA uses 72 observations (2019-01 through 2024-12) extracted from four
official local Ministry PDFs: Tourism Statistics 2022/2023 and Data Compendium
2024/2025. All monthly sums match printed annual totals and overlaps agree.
FTA excludes NRI arrivals and is not spliced into annual ITA. Provenance is in
`data/processed/tourism_monthly_fta/20261025/provenance.json` locally and
`docs/monthly_fta_provenance.json` in the ZIP. PDF scripts need optional pypdf.
Publication availability does not establish a new open-data license.

Initial training is 2019–2021; only 2022 validation selects among persistence,
drift, historical mean, seasonal-naive and ridge at 1/3/6-month horizons.
Expanding tests in 2023–2024 use past prefixes only. Selected persistence has
MAE 100187.42/185913.86/266021.74 arrivals (24/22/19 forecasts). Full methods,
year folds, RMSE/MASE/WAPE are saved. MASE's pandemic-era denominator needs
caution. Predictions start January 2025; no current-2026 accuracy is claimed.

The user-approved [STURM-Flood benchmark](https://zenodo.org/records/12748983)
(CC BY 4.0; attribute dataset creators and DOI 10.5281/zenodo.12748983) is
3,985,215,183 bytes, publisher MD5 `0e4172e74a4cf2e4c608c14d1588d1d9`.
It is stored in `data/external/sturm_flood/12748983/`, checksum verified, and
read without full extraction. No publisher code or pretrained weights are used.
The binary target follows publisher mask >0: reference-positive water/flood
extent, which does not distinguish permanent water from temporary inundation.
Image/reference offsets are limited to 24 hours; dimensions/geospatial tags
are checked. Country/event splits precede sampling of at most six tiles/event.
Validation uses two countries; test uses four countries/seven events. CPU
logistic and gradient boosting candidates and thresholds are selected on
validation IoU only. Both-class confusion metrics and per-scene scores are saved.
This bounded benchmark does not validate Uttarakhand or raw GRD/dB input.

POST `/tourism/monthly-forecast` accepts destination IND, integer horizon 1–6.
POST `/flood/segment` accepts exactly `image` (finite delivered STURM-preprocessed
128×128×2 array) and `metadata` containing `source_format: "STURM-S1-preprocessed"`
and whitelisted `geo_tags`. It returns mask, score map, threshold, version and
limits. Scores are not calibrated flood probabilities. The Model Center uploads
JSON and displays the actual mask. Local `segment_geotiff(project,input,output)`
preserves geospatial tags and refuses overwrite; HTTP accepts no file paths.

```powershell
$env:PYTHONPATH = 'src'
$env:OMP_NUM_THREADS = '2'
python -m safarsaathi_ml.cli evaluate --model tourism_monthly_fta
python -m safarsaathi_ml.cli predict --model tourism_monthly_fta --destination IND --horizon 3
python -m safarsaathi_ml.cli predict --model flood_segmentation --input-json data/interim/flood_ui_example/image.json
```

Disaster risk still needs a complete district/time outcome panel with verified
negative windows; positive-only catalogues do not supply one. Destination
stress needs observed time-aligned crowding/occupancy/capacity outcomes. Both
remain disabled with explicit 503 responses. No fabricated labels are used.

Current release commands are `python -m safarsaathi_ml.completion_release verify`
then `finalize` and `package` for the prepared directory only; outputs refuse overwrite.
Future audits need a new directory and snapshot. Installed Playwright/Chrome
run `frontend/scripts/browser_checks.mjs`; set PLAYWRIGHT_MODULE_PATH if needed
and SAFARSAATHI_BROWSER_OUTPUT to a fresh directory. It launches isolated local
services, verifies the URL and tests navigation/forms/error/disconnection/mobile
journeys. browser_final_rerun contains final evidence. The old browser blocker is
resolved. ZIP validation reloads all four models without raw data. The approved
archive is excluded. Windows API ports now bind exclusively and health includes
a service/schema fingerprint.

## Supported models and scope

The existing review classifier predicts source-defined POSITIVE/NEGATIVE hotel
review labels. It uses a saved TF-IDF/logistic-regression pipeline. Fresh
read-only evaluation reproduced accuracy 0.8500199441563622, macro F1
0.8495165408050799 and weighted F1 0.8499435657168573 on the documented
stratified 80/20 split (seed 20261024, 10025/2507 rows). These scores do not
establish performance for every destination, language or domain.

Tourism uses World Bank/UN Tourism ST.INT.ARVL for India. The local source
`../SafarSaathi_Datasets/raw/worldbank_un_tourism/API_ST.INT.ARVL_India_1995-2025.json`
has 25 observed annual counts from 1995–2019. The 2020–2025 entries are null.
No missing target is imputed. The forecast origin is the last observed year;
horizons 1–3 extrapolate 2020–2022, not current 2026 demand. Units are
international tourist arrivals per calendar year. Geographic coverage is India
national total, not individual Uttarakhand destinations.

The original split remains train 1995–2009, validation 2010–2014 and test
2015–2019. The stored evaluation drift estimator is fixed through 2014, while
the stored inference estimator fits through 2019. The latest comparison refits
persistence, drift, historical mean and ridge using only past prefixes at each
origin, against identical targets/horizons. No test-based replacement was
selected; both registered models and their old evaluation files are unchanged.

## Forecast quality

| Method | One-year MAE | One-year RMSE | MASE | WAPE fraction |
|---|---:|---:|---:|---:|
| Persistence | 961400.0 | 1132018.9927735312 | 3.510589462702139 | 0.06105367439733787 |
| Expanding drift | 590721.0665002428 | 704106.9047150855 | 2.157040931404121 | 0.03751372129577075 |
| Historical mean | 10465447.076039901 | 10524135.497044334 | 38.21498671480402 | 0.6646078616633158 |
| Expanding ridge | 1304853.0219010152 | 1565684.3243049963 | 4.764721519722017 | 0.08286464690610253 |
| Registered fixed drift | 578589.4736842103 | 710022.7072955804 | 2.1127419487686345 | 0.036743304905390954 |

One-year origins are 2014–2018 (5 forecasts); two-year origins 2014–2017
(4 forecasts); three-year origins 2014–2016 (3 forecasts). All horizon scores,
validation-only results and absolute/relative differences are in the final
`tourism_baseline_comparison.json`.

MASE uses MAE divided by **273857.14285714284**, the mean absolute annual change
in the unchanged 1995–2009 training block. The denominator is the same for every
method and horizon. MASE above 1 is compatible with beating test-period
persistence: the historical training changes were smaller. WAPE is a fraction;
individual zero actuals are valid, but an all-zero denominator returns null.
A zero MASE scale also returns null. Seasonal-naive is NOT_APPLICABLE because no
defensible seasonal period is established in these annual totals.

The saved forecaster is **TRAINED_BUT_EXPERIMENTAL**. It has no calibrated
intervals, pandemic/post-pandemic outcomes, held-out destinations or current
operational accuracy. The large 2014 level change and revised-source vintages
need investigation. Local Ministry DOC/PDF publications may contain newer
tourism statistics; audited extraction and target-definition reconciliation are
required before merging them into this series.

## Original data gaps (flood resolved by the approved external benchmark)

- Disaster risk: need observed event IDs, dates, locations and confirmed outcome
  windows. A proposed task is flood onset by Uttarakhand district during the
  next 7 days; the complete district/time panel and pre-cutoff features are
  absent. UNDRR HIP records are definitions, not observed disaster labels.
- Flood segmentation: need observed binary masks matched to imagery in
  acquisition time, CRS, transform and footprint, with documented event/scene
  separation before patches. Satellite/cloud/SCL imagery is not a flood label.
- Destination stress: need a measured destination/time crowding or capacity-
  utilization target with units, capacity observations and sampling coverage.
  Static POIs and national arrival counts cannot establish destination stress.

Disaster and stress readiness/schema checks remain, controls are disabled, and endpoints
return explicit not-trained statuses. Flood is supported as described above. No invented labels, heuristic predictions
or supervised learners were substituted. Follow official alerts and emergency
guidance; the application is not an official warning system.

## Run saved inference

Use Python with `requirements.txt` libraries and compatible serialized-artifact
versions. Verified versions are in model metadata and `review_evaluation.json`.
Only load trusted bundled joblib artifacts. Inference does not require raw files.

From `SafarSaathi_Project`:

```powershell
$env:PYTHONPATH = 'src'
python -m safarsaathi_ml.cli models
python -m safarsaathi_ml.cli validate-artifacts
python -m safarsaathi_ml.cli evaluate --model tourism_demand
python -m safarsaathi_ml.cli predict --model tourism_demand --destination IND --horizon 3
python -m safarsaathi_ml.cli serve --port 8000
```

Backend startup never trains. In another terminal, from `frontend`:

```powershell
npm run build
npm run preview -- --host 127.0.0.1 --port 4173 --strictPort
```

Open the local preview and select AI Model Center. The development alternative
`npm run dev` is configured on port 3000. The default API is
`http://127.0.0.1:8000`; `VITE_SAFARSAATHI_API_URL` overrides it at Vite
startup/build time.

Existing API endpoints remain: GET `/health`, `/models`, `/models/{id}`,
`/system/summary`; POST `/reviews/classify`. Review JSON requires a known
`model_id` and 1–100 nonempty strings in `reviews`. New capabilities:
GET `/capabilities`; POST `/tourism/forecast` with
`{"destination":"IND","horizon":1}`. Forecast responses preserve existing
fields and add explicit origin, requested horizon and experimental quality
status. Review responses include model version and limitations.

POST `/disaster/predict` and `/stress/predict` return 503
not-trained responses. No client artifact/image paths are loaded. Requests are
bounded to 1 MB and require JSON content type. Invalid schemas return 422,
malformed JSON 400, unknown IDs 404, oversized bodies 413, wrong content types
415, wrong methods 405, unavailable artifacts/registry 503 and unexpected
internal failures 500. Errors contain safe JSON messages.

Local CORS permits localhost/127.0.0.1 ports 3000, 5173 and 4173. The service is a
local research backend, not an authenticated public deployment. Demonstration
pages are labeled; their maps, telemetry, scenario formulas and architecture
cards are not live model outputs.

## Training and preservation

The tested command `python -m safarsaathi_ml.cli train --model tourism_demand`
refuses to overwrite the registered model. Disaster/stress training exits 2
with the missing-evidence reason; flood training now refuses to overwrite its
registered artifact. New work requires actual labels
and a separate experiment/version. Do not delete a registry entry to run an
audit. The legacy `pipeline run` / `cli run` trains reviews, and
`archive_audit` writes the protected legacy manifest; neither is part of this
quality workflow.

A supplemental `models/artifact_integrity.json` pins both artifacts against the
prior verified ZIP without modifying their registry entries. Existing registry
locking/atomic writes remain; traversal, Windows alternate-stream paths,
duplicate IDs and unverified persistence flags are rejected.

## Historical verification workflow (previous release)

The full quality audit writes exclusively to a new versioned release directory:

```powershell
$env:PYTHONPATH = 'src'
python -m safarsaathi_ml.final_quality prepare
python -m safarsaathi_ml.final_quality verify
python -m safarsaathi_ml.final_quality package
```

These stages were executed for `final_ml_quality_20261025_01`. They preserve
earlier evidence and refuse to overwrite outputs. For a future run, pass the
same new `--release-name UNIQUE_NAME` to each stage. Packaging requires a
truthful `browser_verification.json` disposition in that new directory; it
cannot fabricate a browser pass.

The verification stage runs the full Python suite, saved evaluation/reload,
fresh-process API startup and external HTTP requests, production build,
frontend API-client tests, training-refusal checks and the streaming raw
checksum verifier. Fault injection uses isolated copies. Raw collection,
legacy archive, model/evaluation files, registry and prior releases are checked
against a pre-audit snapshot.

Additional final frontend tests were run with a real backend:

```powershell
$env:SAFARSAATHI_TEST_API = 'http://127.0.0.1:8000'
node --test --test-reporter=tap tests/api.test.js tests/routes.test.js
```

Run that command from `frontend`. It tests the actual API client and server
rendering of all eight page components plus the shell. It does not validate
browser clicks/navigation, appearance or responsive layout. `npm test` runs
these tests too; without the integration URL, the optional live-HTTP test skips.

Previous evidence is in `release/final_ml_quality_20261025_01/`.
`verification_report.json` records executed commands, outputs and counts;
`release_validation.json` records ZIP/content hashes and inference from a
fresh extracted copy with no sibling raw dataset directory. The ZIP includes
source, tests, config, docs, package lock, reports and both required model
artifacts. It excludes raw collections/reviews, the legacy archive, secrets,
node_modules, environments and caches. Previous releases remain intact.

Previous browser visual testing was BLOCKED because Computer Use could not verify the
current Chrome URL and ended browser control. No other browser-control route
was attempted during that earlier audit. The completion update above resolves this. External Tailwind/font resources remain an offline-style
dependency. These limitations are explicit in the final report.

## Attribution

Source: World Bank Open Data — World Development Indicators. Tourism indicators
are compiled by the World Bank from UN Tourism (formerly UNWTO) source data.
World Bank data: CC BY 4.0. See `docs/DATA_LICENSES_AND_ATTRIBUTION.md` for
source and review licensing. No raw collection was uploaded.
