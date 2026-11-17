# SafarSaathi web console

The production frontend. It exposes every backend route (see `GET /integration/status` → `web_console`):

| Page | What it does | Endpoints |
|---|---|---|
| Overview | Headline figures, live capability status, research findings | `/health` `/capabilities` `/tourism/history` `/research/status` |
| Tourism demand | Annual + monthly arrival history, run both forecast models, recorded accuracy | `/tourism/history` `/tourism/forecast` `/tourism/monthly-forecast` |
| Destinations and climate | Map of 29 NASA POWER points, monthly climatology, rainfall by year, extremes | `/map/layers` `/destinations/{id}` `/destinations/{id}/climate` |
| Cyclone archive | Held-out performance chart, 1–12 month count forecast, broad-model status | `/models/{id}` `/disaster/cyclone-count` `/disaster/predict` |
| Flood segmentation | Load sample/upload tile, view VV/VH bands, water mask + confidence map | `/flood/segment` `/capabilities` |
| Environment and pressure | Indicator lookup, national trend, State/UT ranking, PM2.5 forecast, stress-model status | `/stress/*` `/environment/pm25-forecast` |
| Satellite archive | Sentinel-1/2 scene catalogue | `/satellite/metadata` |
| Review insights | Batch review classification with model metrics | `/models` `/reviews/classify` |
| Capacity scenarios | Presets, form, baseline-vs-scenario charts, session history | `/scenarios/simulate` |
| Allocation optimizer | Editable site table, GA/PSO, convergence, GA vs PSO comparison | `/optimization/*` |
| Model center | Registry, per-model metadata/metrics/schema/provenance, capability readiness | `/models` `/models/{id}` `/capabilities` |
| Data hub | Inventory by group, category filter, pagination | `/datasets` |
| Reports | Backend-recomputed evidence report with scenario/optimisation; JSON download, print to PDF | `/reports/generate` |
| System and API | Health, data-source origin, endpoint coverage, request console for every route | all |

## Run locally

```powershell
# terminal 1 — backend (from SafarSaathi_Project)
$env:PYTHONPATH = 'src'
uvicorn safarsaathi_ml.asgi:app --port 8000

# terminal 2 — console (from SafarSaathi_Project/web)
npm install
npm run dev        # http://localhost:5173, /api is proxied to :8000
```

Or build once and let the backend serve it: `npm run build`, then open http://127.0.0.1:8000.

`npm test` runs client/validation tests; set `SAFARSAATHI_TEST_API=http://127.0.0.1:8000` to include live calls.

## API URL

Leave `VITE_SAFARSAATHI_API_URL` empty when the backend serves the console (Docker/Render) or in dev.
Set it to the API's HTTPS URL only when hosting the console separately (e.g. Vercel), and add that
site's origin to the backend's `SAFARSAATHI_CORS_ORIGINS`.

Map tiles: © OpenStreetMap contributors © CARTO. Sample flood tile: STURM-Flood, CC BY 4.0.
