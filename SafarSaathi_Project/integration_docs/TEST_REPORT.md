> Historical Phase 1 report (2026-10-29). For the current connected frontend, final 153-pass backend suite, 9-pass frontend suite, build/lint and browser evidence, see FRONTEND_API_INTEGRATION_REPORT.md and phase2_* evidence files.

# Test report — 2026-10-29

## Executed and passed

The full backend suite was executed with local loopback permissions:

```powershell
$env:PYTHONPATH = 'src'
python -m pytest tests -q --basetemp .pytest_tmp_integration_verified_20261029 --junitxml=integration_docs/backend_tests.xml
```

**152 passed, 1 skipped, 0 failures in 55.36 seconds.** Evidence: backend_tests.log and backend_tests.xml. The one skip is the stale frontend-client test: `frontend/tests/api.test.js` does not exist in the current protected frontend. Its backend test now explicitly skips with this reason instead of pretending a client was tested. No actual frontend integration test passed or is claimed.

The 33 added cases cover real historical data/metadata loading, actual file stats and pagination, geographic query vs grid coordinates, satellite metadata, source absence/malformed geospatial JSON, scenario conservation/zero-capacity/finite-number constraints, artifact-cache integrity, private-path redaction, new GET/POST schemas and status codes, wrong methods, invalid/duplicate queries, unsupported optimizer, report calculations, restricted CORS and safe source failures. The pre-existing 120 cases cover artifact/loading failures, inference/forecast replay, observed source validation, request formats, registry integrity, flood formats and historical indicators. No fixtures were written into the raw dataset collection or protected frontend.

Additional executed commands:

| Check | Result | Evidence |
|---|---|---|
| `python -m safarsaathi_ml.cli validate-artifacts` | All six active registry artifacts loaded; review sample prediction, annual/monthly/scoped evaluation replay, valid flood inference format | artifact_validation.json |
| `python scripts/smoke_integration.py` | Fresh CLI subprocess started on an ephemeral loopback port; 26 actual HTTP requests returned expected codes; child process stopped | startup_smoke.json, startup_server.log |
| `python scripts/verify_frontend_unchanged.py` | All 475 original files match SHA-256 and size; current count 475; zero added, removed or modified | frontend_sha256_original.json, frontend_verification.json |
| Current catalog read | 1,035 local files across 16 root/category groups; 29 weather locations and 12 raw Sentinel scenes | dataset_inventory.json, DATASET_INTEGRATION.md |

Smoke routes: GET /health, /models, /models/tourism_demand_forecaster, /capabilities, /system/summary, /integration/status, /tourism/history, /datasets?limit=2, /destinations, /destinations/rishikesh, /map/layers, /satellite/metadata, /stress/indicator-metadata; POST /reviews/classify, /tourism/forecast, /tourism/monthly-forecast, /disaster/cyclone-count, /environment/pm25-forecast, /stress/indicators, /flood/segment, /scenarios/simulate, /reports/generate, /disaster/predict (expected 503), /stress/predict (expected 503), /optimization/solve (expected 501), and invalid /scenarios/simulate (expected 422). The schema-valid zero flood tile tests inference mechanics; it is not real-scene flood-analysis evidence.

## Environment limitations and known issues

An initial sandbox run produced **65 passed, 54 skipped, 1 failed** in 61.01 seconds. The failure and most skips were due to WinError 10013 blocking loopback sockets; see baseline_tests.log/xml. The subsequent complete suite and CLI smoke used permitted loopback access and passed as above. No external service, cloud credential, sensor, live satellite feed, npm installation, frontend build or browser journey was tested. No multi-gigabyte raw collection checksum audit was rerun. Current file stats are not hash verification of every dataset.

One third-party pytz DeprecationWarning refers to datetime.utcfromtimestamp; it did not affect results. Exact runtime versions are in runtime_versions.json. There is no .git checkout, so Git status/diff cannot establish a commit baseline or user-change provenance. The frontend hash manifest and explicit file-change list are the available preservation evidence.

## Unimplemented / blocked

- End-to-end frontend API consumption: blocked by absent client hooks and the read-only frontend rule. All current pages remain demonstration/local data.
- Real-time digital twin, sensor/occupancy/road state, operational dispatch, multi-hazard warnings and validated destination stress: absent feeds/labels/models.
- Optimization: no cost/benefit inputs, objective or GA/PSO implementation; honest 501, no plans generated.
- Reports: JSON only, with actual registry/file stats and recomputed hypothetical capacity scenarios. PDF and persistent report storage are not implemented.
- Raw Sentinel preprocessing/analysis, InSAR/NDVI/GLOF, local community text ingestion and current destination demand are not implemented.

Model artifacts remain experimental in scope. Loading and executing them successfully does not establish real-time forecasting accuracy or operational safety.
