# Frontend API integration report — 2026-10-30

## Delivered application

The existing React interface now consumes the existing Python backend. Real data/results were verified **in the UI**, including all six model inference paths, capacity scenarios and JSON reports. No new frontend framework, map library, UI template, database or dependency was added. Existing design assets, CSS, fonts, palette, sidebar/navigation, card/table grids, SVG map schematics and transitions remain in place. Necessary content, input controls and source/error labels changed for truthful integration.

## 1. Architecture discovered and checkpoint

React/React DOM 19.3.1, Vite 8.3.5 installed, plain JSX/local state and `activeTab` navigation. No router/store/API client existed. Dedicated landing/overview/twin/disaster/what-if components coexist with AuxiliaryView, which originally supplied static data for other tabs. Both maps are custom SVG schematics; no GIS library was replaced.

No Git checkout exists. Before edits, all 475 frontend files were copied to `phase2_frontend_backup_20261030_082633/frontend/`, and `frontend_phase2_original.json` recorded hashes. Final verification: **11 authorized original files modified, 9 new integration/test/example files, no original files removed, no unexpected changes**. Every CSS file, asset, lockfile, installed dependency, main entry and unrelated component remains byte-for-byte unchanged. Backup still matches all 475 initial hashes. Evidence: phase2_frontend_verification.json. `git diff --no-index` against backup source was reviewed; phase2_frontend_diff.patch records source differences. It is not a commit-based diff.

## 2. Actual endpoints discovered

Read existing http_api.py, integration_api.py, model pipelines and Phase 1 audit/API/runbook/report. Reused GET health/models/model metadata/capabilities, history, destination/map metadata, satellite metadata, paginated datasets and indicator metadata. Reused POST annual/monthly arrivals, scoped cyclone/PM2.5, review classification, STURM segmentation, historical indicators, capacity scenarios, JSON reports and the explicit optimization availability boundary. Exact schemas are in API_CONTRACT.md. No inference/model/raw data logic was replaced.

Backend edits are limited to updating the stale `/integration/status` implementation metadata and its assertion to describe the browser-verified scope. This status is not a live client-connection heartbeat or proof that missing capabilities exist.

## 3. API client and response/state adapters

- `src/services/api/client.js`: public configurable VITE_SAFARSAATHI_API_URL, loopback default, AbortController timeout (20 seconds), JSON parsing, typed network/timeout/format/HTTP/unavailable errors, credential omission and rejection of credentials embedded in API URLs.
- `resources.js`: central endpoint functions. Components/hooks call these functions rather than scattering fetch logic. Inference, scenarios/reports and availability checks execute only on explicit user actions. POSTs are never automatically retried.
- `adapters.js`: honest number/KPI formatting, explicit bounded scenario input conversion, and finite/ranged longitude/latitude screen projection. No mock fallback replaces a failed response.
- `useApi.js`: keyed 60-second read cache/pending-request deduplication, manual retry, loading/error states, stale component response protection and duplicate-action guards. Unmounted actions do not publish results or create download URLs.
- `ApiState.jsx`: reusable loading/error/empty states with visible validation/unavailable/timeout distinctions; shared tables and limitations retain existing visual tokens.
- `IntegrationDetails.jsx`: response-backed tables/forms inside the existing AuxiliaryView panels. Real session scenario state resides in App and is passed into What-If, Results, Disaster Mode and Reports. Reload clears this session; no persistence service is implied.

## 4–6. Connected, partial and demo pages

FRONTEND_INTEGRATION_STATUS.md maps every existing tab using the required status vocabulary. Tourism history/forecasts, Simulation Results, Data Hub, Model Center, Review Insights, Satellite metadata/benchmark inference and JSON Reports are CONNECTED for their stated scope. Overview, static geographic views, historical stress indicators/scoped risk, What-If's limited supported controls, Disaster Mode and Help are PARTIALLY CONNECTED. Optimizer/explanation, notifications and persisted settings are NOT IMPLEMENTED. Landing remains a static DEMO DATA/product preview.

Overview's existing cards now show historical annual arrivals, source locations, actual local files, model count and historical monthly FTA; its existing gold SVG curve plots the last twelve actual monthly observations. Counts are compact-formatted when needed; exact history remains in Tourism Intelligence. Demonstration operational map/alert sections are explicitly labeled. Random tourist-count fluctuations and arbitrary frontend stress/delay calculations were removed.

## 7–8. Models connected and unavailable

The browser displayed actual responses from:

| Pipeline | Observed UI result / scope |
|---|---|
| Annual arrivals | User-run IND historical forecast, origin 2019, 2020 estimate 18,571,916.67 arrivals. |
| Monthly FTA | User-run IND forecast, origin 2024-12, 2025-01 estimate 1,060,621 arrivals/month. |
| Review classifier | Submitted sample hotel text returned POSITIVE with actual model ID/limitations. |
| Cyclone archive count | NI-basin forecast, origin 2024-12, 2025-01 estimate about 0.18 eligible archive IDs/month. Not landfalls or warning probability. |
| PM2.5 | National modeled-exposure forecast, origin 2023, 2024 estimate about 52.63 µg/m³. Not current/local air quality. |
| STURM segmentation | Selected existing supported preprocessed tile (`data/interim/flood_ui_example/image.json`), returned 128×128 mask, threshold 0.3 and 4,507 reference-positive pixels. Returned mask renders in the satellite panel. This validates inference mechanics on a benchmark-format input, not raw-scene/live flood accuracy. |

Model Center reads actual registry entries, recorded feature requirements/targets/metrics and scoped capabilities. Artifact loading is not presented as accuracy validation. No model was retrained, replaced or assigned invented metrics. `phase2_artifact_validation.json` independently records successful task-specific validation of all six. Broad stress/hazard predictors and optimization remain absent. UI exposes historical indicators or explicit unavailable status instead of arbitrary scores or fake GA/PSO results.

## 9. Geospatial integration

Destination Twin reads 29 locations and the existing FeatureCollection. Rail selection and accessible inset markers update the existing detail panel. Rishikesh displayed source grid longitude 78.292/latitude 30.109 and separately requested longitude 78.29162/latitude 30.10865. Geographic order, range and finiteness are tested; missing/invalid points are omitted, not invented. Source-native geometry/date/parameter metadata are retained; no EPSG code is declared by these sources and no reprojection is claimed.

The actual-coordinate inset has its own explicitly labeled coordinate frame. It is **not registered to the schematic roads/terrain** underneath. Existing layer toggles continue to control illustrative layers; these are labeled DEMO DATA, with no live GPS/IoT/satellite/infrastructure synchronization. The location rail scrolls to accommodate the real 29 records without stretching the original three-column workspace. Live Geospatial Map displays actual static point records; operational road/hazard/exposure layers remain unavailable.

## 10. Scenarios, reports and errors

What-If retains every original control. Added explicit hypothetical baseline visitors, visitor capacity and available-capacity percentage; existing surge supplies demand_change_percent. Rainfall/highway/accommodation/fleet are clearly marked unmodeled context; no invented conversion weights, stress score, delay or geographic impact is generated. Backend baseline/scenario responses drive the result cards, utilization bar, shared result table, assumptions and limitations.

Browser example: 100 baseline visitors, 120 capacity, +5% demand and 50% availability returned 105 demand, 60 capacity/served, 45 unserved. The same result appeared in Results and Disaster Mode. Invalid capacity zero produced a visible validation error; zero available capacity returned null utilization displayed as undefined. Fresh-session Results shows an empty state. No save/persistence endpoint exists; the UI states that results last until reload.

Reports use actual registry/file stats and optionally backend-recomputed scenario inputs. Actual JSON download succeeded and the downloaded file was parsed/validated with six model entries (`phase2_downloaded_report.json`). PDF EXPORT COMING SOON is explicit; no fake PDF button exists.

Stopped only the backend process created for this task to test an outage. Live Geospatial Map showed API UNAVAILABLE, no fake replacement values; navigation/session results remained usable. After restarting the backend, actual data loaded again. Client tests separately cover timeout, invalid JSON, 422/501/503 responses, network failures, no automatic POST retries, input constraints and deduplication.

## 11. Executed tests

| Check | Final result | Evidence |
|---|---|---|
| Complete Python suite | **153 passed, zero skipped, zero failed**, 67.97s | phase2_backend_tests.log/xml |
| Frontend Node suite with real localhost API | **9 passed, zero skipped, zero failed** | phase2_frontend_tests.log |
| Final integration-status adapter subset | 33 passed | phase2_status_tests.log |
| Saved-artifact validation | Six pipelines pass | phase2_artifact_validation.json |
| Actual browser journeys | Connected pages/actions, all six model outputs, pagination, real report download, invalid/empty/error/loading behavior, shared session results, navigation and desktop/mobile comparison verified | phase2_browser_checks.json; phase2_visual/*.jpg |
| Preservation/hash audit | Pass: exact backup, no removals, no unexpected changes | phase2_frontend_verification.json |

The former skipped Python frontend-client test now runs `frontend/tests/api.test.js` against its real ephemeral backend and passes. Browser observations were actual UI interactions, not a fabricated automated Playwright test count. One third-party pytz deprecation warning remains in Python tests. No external service/live feed or new scientific model evaluation is claimed.

## 12. Build and visual status

`npm run build -- --configLoader runner` **passed**, with Vite output and cache redirected to `integration_docs/phase2_runtime/`. `npm run lint` **passed without warnings**. Installed packages were reused; no install/update was needed. Existing dist/cache directories were neither deleted nor overwritten. Supporting isolated runner is `scripts/frontend_runner.mjs`.

Desktop 1440×960 comparison confirmed identical original/integrated CSS signatures: sidebar 288px, background rgb(12,14,19), main background rgb(17,19,25), Space Grotesk / Plus Jakarta Sans / Inter font stack. CSS/assets and original SVG schematic geometry remain unchanged. Data, content, added form controls and truthful labels necessarily differ; **pixel-for-pixel visual identity is not claimed**. Before/after screenshots are retained.

## 13. Known issues and limits

- Original fixed 288px sidebar/header offset crowds the content on 390px screens; original page already overflows (measured original document width 578px). This navigation layout was retained under the no-redesign directive. New tables scroll within their panels, but full mobile navigation remediation is separate work. Desktop pages are usable; mobile perfection is not claimed.
- Tailwind CDN/fonts remain the original external styling dependencies. Offline styling is not newly solved.
- Static source-coordinate inset is not a georeferenced operational map. No geographic result is invented for capacity scenarios.
- No live telemetry, local capacity observations, emergency dispatch, optimization, PDF export, server scenario/report persistence or local review corpus. Narrow historical models remain experimental.
- Data/history endpoints and dependencies may fail if local files are removed; explicit UI errors remain visible. No production authentication/security deployment or external connector was added.

## 14. Run the complete application

See RUNBOOK.md for exact PowerShell commands, configurable URL, isolated outputs, dependencies and verification. Start Python API on 127.0.0.1:8000 and Vite on 127.0.0.1:5173 separately. The frontend dev script does not launch Python. Phase 1 reports remain historical; phase2_* evidence and current status/runbook describe the connected implementation.
