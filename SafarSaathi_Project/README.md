# SafarSaathi — verified ML research prototype

Phase 2 integration (2026-10-30): the existing React/Vite frontend now reads actual
backend data, runs supported model/scenario actions and generates JSON reports.
CSS, assets, branding and navigation are preserved. Live operational panels remain
explicit demonstrations; optimization and PDF export are unavailable. See the
[frontend integration report](integration_docs/FRONTEND_API_INTEGRATION_REPORT.md),
[current runbook](integration_docs/RUNBOOK.md),
[API contract](integration_docs/API_CONTRACT.md), and
[page status](integration_docs/FRONTEND_INTEGRATION_STATUS.md).

Six persisted models support real inference: review classification, historical
annual tourism, monthly foreign-tourist arrivals, and experimental flood-scene
water segmentation, plus North Indian Ocean archived tropical-count and India
national modeled-PM2.5 forecasts. The new forecasts have narrow, experimental
targets. India-wide multi-disaster warnings and destination ecological-stress
prediction remain disabled because appropriate observed outcome panels are absent.
Historical national environmental and 36-State/UT visit indicators are available
separately and are not trained stress predictions.

The final quality audit preserves all four original model versions and earlier evidence.
Tourism is **TRAINED_BUT_EXPERIMENTAL**: the original source has 25 annual India
counts from 1995–2019; a separate monthly FTA model uses 72 observations through
December 2024. These are different target definitions. Forecasts
start from the last observation, not the current year. No current 2026 or
Uttarakhand destination-demand accuracy is claimed.

## Start and inspect

Use Python with the libraries in `requirements.txt` installed and Node.js with
the frontend dependencies from its package lock. The verified runtime versions
are recorded in model metadata and the verification reports.

From `SafarSaathi_Project`:

```powershell
$env:PYTHONPATH = 'src'
python -m safarsaathi_ml.cli models
python -m safarsaathi_ml.cli validate-artifacts
python -m safarsaathi_ml.cli evaluate --model tourism_demand
python -m safarsaathi_ml.cli predict --model tourism_demand --destination IND --horizon 3
python -m safarsaathi_ml.cli serve --port 8000
```

In `frontend`, `npm run dev` starts Vite on its default port 5173. The production build command is
`npm run build`; `npm run preview -- --host 127.0.0.1 --port 4173 --strictPort`
serves it locally. The backend listens at `http://127.0.0.1:8000`;
the centralized client defaults to that URL. VITE_SAFARSAATHI_API_URL configures it at Vite startup/build time.

Read [ML_MODELS.md](ML_MODELS.md) for API schemas, model evaluation, tests,
source attribution, training restrictions and release reproducibility.
The consolidated [model cards](docs/MODEL_CARDS.md), [data provenance](docs/DATA_PROVENANCE.md),
and [remaining limitations](docs/REMAINING_LIMITATIONS.md) document the six models,
source reuse, blocked capabilities, and evidence needed to unblock them.

## Final evidence

The current versioned directory is
`release/final_master_20261025_04/`:

- `FINAL_VERIFICATION_REPORT.md` and `verification_report.json`.
- `cyclone_count_evaluation_replay.json` and `pm25_evaluation_replay.json`: saved evaluation replays.
- `disaster_data_readiness.json` and `destination_stress_data_readiness.json`.
- `source_manifests.json`, `source_investigation.json` and `raw_checksums.json`.
- `release_validation.json`: extracted-copy inference and ZIP checks.
- `SafarSaathi_Final.zip`: the new release; earlier ZIPs remain preserved.

Exact Python, Node and browser counts are recorded in the new release report.
Isolated installed Chrome executes real form, navigation, error and mobile
journeys; packaged final screenshots are in browser_visual. External Tailwind/fonts remain an
offline-styling limitation. The approved STURM archive stays outside the ZIP.

Read [the India scope guide](docs/INDIA_SCOPE_MODELS.md) for new CLI/API schemas,
source definitions, training reproduction and troubleshooting. The prior four-model
release is preserved in `release/final_working_20261025_02/`.

The review classifier was not retrained. No raw datasets, original evaluation
results, model versions, legacy archive files or earlier releases were replaced.

## Launch the current backend

From `SafarSaathi_Project`:

```powershell
python -m pip install -r requirements.txt
$env:PYTHONPATH = 'src'
python -m safarsaathi_ml.cli serve --port 8000
```

The frontend's `dev` script launches only Vite; run the backend separately.
In a second terminal from the project root:

```powershell
Set-Location frontend
$env:SAFARSAATHI_VITE_CACHE = '../integration_docs/phase2_runtime/dev-cache'
npm run dev -- --host 127.0.0.1 --port 5173 --strictPort --configLoader runner
```

Open `http://127.0.0.1:5173`. `npm test` now runs the built-in Node API/adapter
tests; set SAFARSAATHI_TEST_API to the local backend URL to include real requests.
`npm run build -- --configLoader runner` and `npm run lint` were verified. The
runbook explains redirecting build output outside frontend, supported inputs,
unavailable capabilities and exact test evidence. Backend tests use
`python -m pytest tests -q`; all six saved pipelines remain unchanged.
