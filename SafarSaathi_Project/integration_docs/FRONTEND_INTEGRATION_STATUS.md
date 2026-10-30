# Frontend integration status — Phase 2, 2026-10-30

Minimal frontend integration edits are now explicitly authorized. The UI consumes real backend responses through the centralized client. Statuses below describe the browser-verified scope, not unsupported live operations. Runtime request failures show BACKEND UNAVAILABLE/error states without mock substitution. /integration/status records implementation/browser-verification metadata, not a live client heartbeat.

| Existing page | Status | Actual UI connection and limitations |
|---|---|---|
| Landing | DEMO DATA | Original product/corridor preview, branding and navigation retained. Static/demo labels visible; unsupported telemetry/certification metrics no longer presented as verified measurements. No health heartbeat claimed. |
| Overview | PARTIALLY CONNECTED | Existing five cards show real national annual arrivals, source-location count, actual local-file count, registered artifact count and monthly FTA. Existing curve plots the last twelve actual monthly observations. Road/alert/dispatch schematic sections remain DEMO DATA; no live occupancy/stress. |
| Destination Twin | PARTIALLY CONNECTED | Existing rail/map/detail layout reads 29 locations and map metadata. Selectable source-coordinate inset uses an independent native lon/lat frame, not registered to demo roads/contours. Query and returned grid coordinates remain separate. No live infrastructure, capacities or GPS. |
| Tourism Intelligence | CONNECTED | Real annual/monthly national history, explicit origin/units/source and user-run annual/monthly forecasts displayed from model responses. No current destination demand claim. |
| Crowd & Destination Stress | PARTIALLY CONNECTED | Supported geography/year selector, actual historical indicators and separately scoped experimental PM2.5 forecast. STRESS MODEL NOT IMPLEMENTED. No arbitrary composite score. |
| Risk & Resilience | PARTIALLY CONNECTED | Actual capabilities and user-run NI-basin archived cyclone-count forecast. No geographic exposure overlay, current hazard observation or multi-hazard warning. |
| Disaster Mode | PARTIALLY CONNECTED | Actual last submitted session capacity scenario. Existing emergency panels remain DEMO DATA. Persistent SIMULATION MODE — NOT A LIVE EMERGENCY ALERT. Checkboxes/toasts do not dispatch commands. |
| Live Geospatial Map | PARTIALLY CONNECTED | Actual static point coordinates/coverage in the existing analysis shell. No live sensors or operational georeferenced road/hazard layers. |
| What-If Simulator | PARTIALLY CONNECTED | Actual capacity API submission, processing/error states and returned baseline/outcomes/assumptions. Explicit baseline/capacity/available-percent inputs and existing tourist surge are modeled. Original rainfall/highway/accommodation/fleet controls remain visibly unmodeled demo context. |
| Simulation Results | CONNECTED | Exact successful session response, submitted parameters, baseline/scenario outcomes and limitations. Empty state in a fresh session. No affected geographic outputs or server-side persistence. |
| Intervention Optimizer | NOT IMPLEMENTED | Explicit availability check calls the real endpoint and displays unavailable/501. OPTIMIZATION ENGINE NOT AVAILABLE. No fake plans/convergence. |
| Optimization Explanation | NOT IMPLEMENTED | Same honest availability boundary; no optimizer or plans to explain. |
| Satellite Intelligence | CONNECTED | Actual twelve-scene metadata, parsed acquisition timestamps, source/license/availability. Explicit supported STURM-preprocessed JSON tile input runs actual benchmark segmentation and renders its mask. No raw-scene conversion, live flood detection, InSAR/NDVI/GLOF or emergency warning. |
| AI Model Center | CONNECTED | Six registry entries, scoped capabilities and selectable saved metadata/schema/evaluation metrics. Missing metadata is not invented; loading is not accuracy validation. |
| Tourist & Community Insights | CONNECTED | Registered binary review classifier, explicit text submission and source-label predictions/provenance. No destination corpus or multilingual validation implied. |
| Data Hub | CONNECTED | Server-paginated actual filenames/formats/sizes, declared source/license/coverage and explicit unknowns. File existence is not ingestion, hash verification or a live connector. |
| Reports & Briefs | CONNECTED | Actual JSON generation/display/download with optional backend-recomputed scenario. PDF EXPORT COMING SOON. No fake PDF or persistent report archive. |
| Notifications | NOT IMPLEMENTED | Existing shell retained; no live-feed service. |
| Settings | NOT IMPLEMENTED | Existing shell retained; no backend persistence or authentication bypass. |
| Help & Architecture | PARTIALLY CONNECTED | Actual health/schema/artifact-count fields. Local architecture and absent operational/certification scope stated honestly. |

All CONNECTED claims were verified through actual browser interaction. See FRONTEND_API_INTEGRATION_REPORT.md and phase2_browser_checks.json. Phase 1 reports/manifests remain historical evidence; they are not current connection claims.
