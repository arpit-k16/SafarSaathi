# Phase 2 plan — 2026-10-30

The user now authorizes minimal frontend integration edits while preserving branding, assets, CSS, layout, navigation, controls and animations. No Git checkout exists. Full pre-edit checkpoint: `phase2_frontend_backup_20261030_082633/frontend/`; SHA-256 baseline: `frontend_phase2_original.json` (475 files). Phase 1 evidence remains historical and will not be overwritten.

Discovered React 19/Vite 8, JSX, activeTab navigation and local state; no map library: both maps are custom SVG schematics. Keep those SVGs and use a separately labeled source-coordinate overlay within the same viewport (longitude x, latitude y). Original drawn roads/contours/sensors remain clearly marked DEMO DATA and are not treated as georeferenced evidence. Actual source has no EPSG declaration; do not infer alignment between source points and schematic roads.

Use existing fetch/AbortController browser primitives, a central API client, response adapters, reusable query/loading/error states and application session scenario state. Add VITE_SAFARSAATHI_API_URL support with loopback default; no credentials. Read-only metadata may be cached/deduplicated briefly; inference/reports/scenarios run only on explicit action, with no automatic POST retries. Timeout/invalid JSON/HTTP failures remain visible, never replaced by mock results.

| Existing page | Actual endpoints / implementation |
|---|---|
| Landing | Existing branding/navigation retained; static content is illustrative, no operational claims verified. |
| Overview | /tourism/history, /destinations, /datasets?limit=1, /models, /health; bind existing five KPI cards to historical totals, source locations, local file count and registry count; preserve SVG schematic/demo telemetry sections and label them. |
| Destination Twin | /destinations, /map/layers; bind existing selection rail and detail panel to source names, coordinates, date coverage and parameter metadata. SVG source overlay has its own labeled coordinate frame. Occupancy/resources remain unavailable, not fabricated. |
| Tourism Intelligence | /tourism/history, /tourism/forecast, /tourism/monthly-forecast; show annual/monthly national history, explicit origin/units, user-run forecast. |
| Crowd & Stress | /stress/indicator-metadata, /stress/indicators, /environment/pm25-forecast; historical geography/year selector and indicator rows, separately scoped PM2.5 forecast. STRESS MODEL NOT IMPLEMENTED. |
| Risk & Resilience | /capabilities, /disaster/cyclone-count; historical basin archive-count forecast, scope and limitations. No exposure/live warning endpoint exists. |
| Disaster Mode | Shared actual capacity scenario result from What-If; existing exercise panels stay DEMO DATA; persistent SIMULATION MODE — NOT A LIVE EMERGENCY ALERT. Local checkboxes do not dispatch actions. |
| Live Geospatial Map | /map/layers; static source coordinate rows; no sensor feeds. Preserve navigation and label static scope. |
| What-If | /scenarios/simulate; retain all original controls. Add explicit hypothetical baseline visitors, capacity and available capacity inputs. Tourist surge maps directly to demand_change_percent. Rainfall/highway/fleet controls are retained as unmodeled context, never mapped with invented effects; accommodation presets may set documented user-assumed availability/capacity. Show actual returned baseline/outcomes/assumptions; shared session result only, no fake server save. |
| Simulation Results | Same real session response, parameters and assumptions; empty state if no scenario run. No affected geography is returned. |
| Optimizer / Explanation | /optimization/solve explicit availability boundary (501). OPTIMIZATION ENGINE NOT AVAILABLE; no fake convergence/solutions. |
| Satellite | /satellite/metadata; real scene names, acquisition-from-product-ID, file count/size, provenance. Optional explicit STURM-preprocessed JSON input to /flood/segment; no raw scene conversion or live detection claim. |
| Tourist & Community | /models and /reviews/classify; actual registered review model selection and explicit text inference, source-domain limits. No raw corpus download. |
| Data Hub | /datasets with server pagination; source/license/coverage/null metadata retained. File count does not mean records ingested. |
| AI Model Center | /models, /models/{id}, /capabilities; six actual artifacts, recorded versions/metrics/schema where available and scoped availability. No loading == accuracy claim. |
| Reports | /reports/generate, optional last scenario.parameters; display/download actual JSON. PDF EXPORT COMING SOON. |
| Notifications / Settings / Help | Preserve existing page shells; show unimplemented services and actual health/local architecture information; remove unverified certifications from operational data presentation. |

Testing: built-in Node tests for API/adapters, real API-client round trips, backend regression/loaded artifacts, actual Vite build/lint, browser checks on connected pages/actions/error states/navigation and narrow viewport. Redirect Vite cache/build to a unique directory outside frontend through environment-controlled config while keeping normal commands intact. Preserve lockfile, assets, CSS and existing caches. Compare original asset/config/source changes against the backup and document visual/layout limitations honestly.
