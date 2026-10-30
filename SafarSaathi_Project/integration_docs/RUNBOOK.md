# SafarSaathi local runbook — Phase 2, 2026-10-30

The existing React frontend is now connected for the scopes in FRONTEND_INTEGRATION_STATUS.md. Start the Python API and Vite separately. Original CSS/assets/lockfile/dependencies remain unchanged; frontend integration edits are authorized in Phase 2. Phase 1 reports and original hash manifest are historical evidence, not a current frontend-read-only requirement.

## Backend terminal

From the workspace:

```powershell
Set-Location SafarSaathi_Project
$env:PYTHONPATH = 'src'
python -m safarsaathi_ml.cli serve --port 8000
```

For a fresh environment, install the existing backend requirements first: `python -m pip install -r requirements.txt`. Verified Python 3.14.6, numpy 2.4.6, pandas 2.3.3, scikit-learn 1.9.1, joblib 1.6.0, tifffile 2026.10.15 and pytest 8.4.2. Artifact compatibility depends on the recorded versions. No training or downloads occur on HTTP requests. Binding is loopback only; stop your own server with Ctrl+C.

## Frontend terminal

From the project root in a second PowerShell terminal:

```powershell
Set-Location frontend
$env:VITE_SAFARSAATHI_API_URL = 'http://127.0.0.1:8000'
$env:SAFARSAATHI_VITE_CACHE = '../integration_docs/phase2_runtime/dev-cache'
npm run dev -- --host 127.0.0.1 --port 5173 --strictPort --configLoader runner
```

Open http://127.0.0.1:5173 and launch the existing command deck. Node 24.17.0, React/React DOM 19.3.1, Vite 8.3.5, plugin-react 6.1.2 and oxlint 1.89.0 were used. Existing installed packages were reused. In a fresh checkout without dependencies, `npm ci` installs the lockfile versions; it was not run here and should not be used to overwrite an existing user dependency/cache tree unnecessarily. No new dependencies were added.

VITE_SAFARSAATHI_API_URL is public client configuration, defaults to http://127.0.0.1:8000, and takes effect at Vite startup/build. A `.env.example` is supplied; no real `.env` or credentials were created. Never put secrets in VITE_ variables. Changes require restarting Vite/rebuilding. The API client rejects credentials embedded in URLs. CORS still permits only http localhost/127.0.0.1 at ports 5173, 4173, 3000. It is not authentication or permission for public production deployment.

For verification, `node scripts/frontend_runner.mjs dev` from the project root starts Vite with a cache outside frontend and no bundled-config temp files. The runner accepts an optional frontend root for testing the immutable backup, and `build` mode writes isolated production output. No existing cache/build tree is cleaned.

## Build, lint and frontend tests

From frontend:

```powershell
$env:SAFARSAATHI_VITE_CACHE = '../integration_docs/phase2_runtime/npm-cache'
$env:SAFARSAATHI_VITE_OUT = '../integration_docs/phase2_runtime/npm-build'
npm run build -- --configLoader runner
npm run lint
$env:SAFARSAATHI_TEST_API = 'http://127.0.0.1:8000'
npm test
```

These commands passed. Build output/cache are outside original frontend files. `--configLoader runner` avoids Vite bundled-config temporary files. Existing frontend dist/node_modules/.vite/.vite-temp were not deleted or overwritten. Without SAFARSAATHI_TEST_API, the eight client/adapter unit cases run and the one real-API case is explicitly skipped; with a reachable local API, all nine execute. POST inference is never automatically retried.

To preview the verified production output from frontend:

```powershell
npm run preview -- --host 127.0.0.1 --port 4173 --strictPort --outDir ../integration_docs/phase2_runtime/npm-build --configLoader runner
```

The production build passed; the separate preview command was not exercised. Browser journeys used the actual Vite dev server and local Python backend.

## Backend and preservation checks

From project root:

```powershell
$env:PYTHONPATH = 'src'
python -m pytest tests -q --basetemp .pytest_tmp_phase2_check
python -m safarsaathi_ml.cli validate-artifacts
python scripts/verify_phase2_frontend.py
```

HTTP checks need permitted loopback access. The complete final Python suite passed 153 tests, including the formerly skipped Node API-client round trip. Current model validation passed all six. The Phase 2 preservation checker confirms the exact 475-file backup, only authorized original modifications, no removals, and byte-identical CSS/assets/lockfile/dependencies. `verify_frontend_unchanged.py` checks the older Phase 1 manifest and will intentionally report the now-authorized source edits; do not restore Phase 1 files to satisfy it.

There is no .git checkout. Use the saved manifest/backup and `git diff --no-index` for inspection; never blanket reset or overwrite user work. Detailed source diff, hash audit, test logs, browser observations and before/after screenshots are under integration_docs/phase2_*.

## Data and supported use

Raw archive: sibling SafarSaathi_Datasets/raw; manifest/licenses/checksums in its parent. Extra sources: data/raw_v2 and data/external. Derived monthly FTA: data/processed/tourism_monthly_fta/20261025. Scoped series: data/processed/india_scope_20261025. Historical indicators: outputs/indicators/india_environment_tourism. Models and integrity pins: models/registry.json and models/artifact_integrity.json; relative artifact paths remain unchanged. No raw/model files were modified.

Tourism is historical/national: annual series ends 2019 and monthly FTA ends 2024-12. Scoped cyclone counts and modeled PM2.5 are not local hazard/stress warnings. Review inference is binary source-domain classification. Satellite page lists raw-scene metadata; optional segmentation accepts only supported STURM-preprocessed 128x128x2 JSON arrays with source metadata, maximum JSON body 1 MB, not arbitrary TIFF/JP2/raw scenes. Raw source licenses still apply; no raw review corpus is exposed.

What-If uses explicit hypothetical baseline/capacity/availability plus the existing tourist surge. Other original controls remain unmodeled context. Results are kept in application session memory and shared with Results, Disaster Mode and Reports; reload clears them. No server persistence or geographic impact output exists. Reports download actual JSON; PDF export and intervention optimization are unavailable.

## Troubleshooting and limitations

If the API is offline, the UI shows a visible error; it does not swap in demo results. Start Python, then use Retry or re-enter the view. Read-only queries cache for 60 seconds; explicit POSTs run only on user action. Timeouts/invalid JSON/422/501/503 and invalid form inputs are visible. Metadata/inference errors never authorize inventing predictions.

Port conflicts: choose a free --port or stop only your own known server. Match the configured API URL and permitted frontend origins; do not broaden CORS to a wildcard. Import errors: check PYTHONPATH and installed versions. Missing/corrupt model/source: restore the exact trusted version and verify checksums; do not silently retrain or edit integrity pins. No external connector, database, cloud credential or live sensor was tested/added.

Design: original dark/gold theme, assets and fixed navigation are retained. The existing 288px fixed sidebar constrains 390px mobile layouts and original pages already overflow. This was documented rather than redesigned; new tables have panel-local overflow containment. Original Tailwind CDN/fonts still affect offline rendering. A source-coordinate inset is explicitly independent of schematic roads, not a live georeferenced operational map. Deployment/authentication and mobile navigation redesign remain separate work.
