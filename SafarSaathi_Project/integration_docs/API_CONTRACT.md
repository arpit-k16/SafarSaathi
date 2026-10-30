# Backend API contract

Base URL: `http://127.0.0.1:8000`. JSON request/response bodies. The existing stdlib HTTP backend is retained. No authentication, database, raw-file upload, training-on-request or live external service is added. This service is for local use and binds only to loopback.

## Current frontend contract — Phase 2

The React frontend now consumes the routes below through src/services/api/client.js and resources.js. VITE_SAFARSAATHI_API_URL configures the base URL; the default is http://127.0.0.1:8000. Navigation remains activeTab state. Actual current bindings and partial/demo sections are documented in FRONTEND_INTEGRATION_STATUS.md. Phase 1's absent-client findings remain historical in PROJECT_AUDIT.md and FINAL_REPORT.md.

## Existing routes, preserved

| Method and route | Request schema | Successful response schema / meaning |
|---|---|---|
| GET /health | No body | `{status:"ok",trained_models:int,training_on_request:false,service:string,api_schema_version:string}`. Count is registered artifacts, not live operational models. |
| GET /models | No body | Array of `{model_id,task,trained_at,metrics,limitations,model_version,quality_status}`. Recorded metrics are not newly measured on GET. |
| GET /models/{id} | Exact registry ID | Registered metadata object, with private paths/source fields removed recursively. Unknown ID: 404. Optional metadata fields differ by model; missing schemas/versions are not fabricated. |
| GET /capabilities | No body | Four parent capability objects with `inference_available`, `status`, scope, limitations and optional scoped/monthly forecasts. Broad risk/stress remain unavailable even when their narrow scoped forecast is available. |
| GET /system/summary | No body | `{models:array,evaluation:object\|null,dataset_inventory:object\|null,operational_data_status:"unavailable",operational_data_note:string}`; historical release summary may be stale. Use /datasets for current file stats. Private paths are removed. |
| GET /stress/indicator-metadata | No body | `{status,geographies,years,formulae,missing_data_rule,limitations,geography_years}` from checksum-validated snapshot. |
| POST /reviews/classify | `{model_id:string,reviews:string[1..100]}`; each string nonempty | `{model_id,predictions:string[],status:"ok",model_version,limitations}`; one POSITIVE/NEGATIVE source-label prediction per input. Only review-classification model IDs supported. |
| POST /tourism/forecast | Exactly `{destination:"IND",horizon:int[1..3]}` | `{model_id,model_version,destination,status,latest_observed_year,units,forecast_origin_year,horizon,quality_status,is_forecast:true,forecasts:[{year,horizon,prediction}],limitations}`. Annual national arrivals, origin 2019. |
| POST /tourism/monthly-forecast | Exactly `{destination:"IND",horizon:int[1..6]}` | `{model_id,model_version,destination,status,quality_status,latest_observed_date,forecast_origin,horizon,units,is_forecast:true,target_definition,forecasts:[{date,horizon,prediction}],limitations}`. Origin 2024-12. |
| POST /disaster/cyclone-count | Exactly `{geography:"NI",horizon:int[1..12]}` | Scoped experimental response `{model_id,model_version,status,quality_status,geography,units,target_definition,latest_observed_date,forecast_origin,horizon,forecasts:[{date,horizon,prediction}],limitations}`. NI basin archive counts, not warnings; this legacy response has no is_forecast field. |
| POST /environment/pm25-forecast | Exactly `{geography:"IND",horizon:1}` | Same scoped response; annual modeled national exposure. Origin 2023. |
| POST /flood/segment | Exactly `{image:number[128][128][2],metadata:{source_format:"STURM-S1-preprocessed",geo_tags:object}}` | `{model_id,model_version,status,quality_status,dimensions:[128,128],mask:binary[128][128],confidence_map:number[128][128],threshold,input_metadata,class_mapping,limitations}`. Finite pixel values with absolute value <=10; geo_tags keys only 33550,33922,34264,34735,34736,34737 (strings), metadata JSON <=10,000 characters. No raw Sentinel TIFF/JP2 upload or conversion. |
| POST /stress/indicators | Exactly `{geography:string,year:int}` from metadata's geography_years | `{status,observation:object,formulae,missing_data_rule,limitations,prediction:false,trained_model:false}`. Historical observed/reported/estimated source indicators; null missing values are retained. |
| POST /disaster/predict | Object; no valid predictor schema yet | 503 `{status:"not_trained",model_id,detail}`. Broad multi-hazard prediction unavailable. |
| POST /stress/predict | Object; no valid predictor schema yet | 503 `{status:"not_trained",model_id,detail}`. Validated destination stress predictor unavailable. |

Boolean horizons and extra forecast/scoped fields are rejected. Existing task-specific validation, feature order and preprocessing are retained, including restrictive flood metadata rules in `flood_baseline.segment` and pixel validation in `image_features`. Full saved schema/metrics are in model metadata and existing model cards; no new predictive model is substituted.

## New read-only adapters

| Method and route | Request schema | Response schema |
|---|---|---|
| GET /integration/status | No query/body | `{frontend_connected:true,pages:{[tabId]:status},verification_date:string,reason:string}`. Each tab is listed with CONNECTED, PARTIALLY CONNECTED, DEMO DATA or NOT IMPLEMENTED for its verified scope. This is implementation metadata, not a live browser heartbeat. |
| GET /datasets | Optional query `offset` nonnegative integer (default 0), `limit` integer 1..200 (default 100), `category` exact category string; no duplicates/other keys | `{status:"LOCAL_INVENTORY",generated_utc,total:int,offset:int,limit:int,groups:{[root/category]:{files:int,size_bytes:int}},files:DatasetFile[],limitations:string[]}`. Pagination returns [] beyond end. Unknown category returns zero matching files. |
| GET /tourism/history | No query/body | `{status:"HISTORICAL_ONLY",destination:"IND",is_forecast:false,series:[{frequency,units,source:object,observations:[{year,arrivals}]},{frequency,units,source:object,observations:[{date,arrivals}]}],limitations:string[]}`. Annual and monthly definitions are kept separate. Both source series must validate or endpoint returns 503. |
| GET /destinations | No query/body | `{status:"STATIC_SOURCE_LOCATIONS",destinations:Location[],limitations:string[]}`. These are 29 named weather query/grid points. |
| GET /destinations/{id} | Lowercase slug from /destinations | `{status:"STATIC_SOURCE_LOCATION",destination:Location,limitations:string[]}` or 404. No arbitrary file path is accepted. |
| GET /map/layers | No query/body | `{type:"FeatureCollection",status:"STATIC_SOURCE_LOCATIONS",live:false,coordinate_metadata:string,features:[{type:"Feature",id,geometry,properties}],limitations:string[]}`. Only source grid-point metadata, no operational roads/hazards. |
| GET /satellite/metadata | No query/body | `{status:"RAW_IMAGERY_METADATA_ONLY",scenes:[{mission,product_id,files:int,size_bytes:int,acquisition_from_product_id:string\|null,geographic_coverage:string\|null,source:string\|null,license:string\|null}],flood_analysis_available_for_these_scenes:false,limitations:string[]}`. Acquisition is parsed from the product ID and labeled as such. |

`DatasetFile`: `{root,relative_path,filename,category,format:string|null,size_bytes:int,modified_utc,source:string|null,coverage_start:string|null,coverage_end:string|null,geographic_coverage:string|null,license:string|null,declared_sha256:string|null,declared_size_matches:boolean|null,checksum_verified_this_request:false,availability:"LOCAL_FILE",remote_connection_tested:false}`. All paths are relative catalog identifiers. Manifest checksums/coverage/licenses are declared metadata, not new verification. Unmanifested project files return null provenance fields. There are no download endpoints and raw review text is not exposed.

`Location`: `{id,name,geometry:{type:"Point",coordinates:number[2..3]},query_coordinates:{latitude,longitude},coverage_start,coverage_end,parameters:object,source_file:basename,source:"NASA POWER archived reanalysis",live:false}`. Source query and returned grid coordinates differ; both are preserved. Native source JSON provides no EPSG declaration. Coordinate ranges/finiteness are validated; no reprojection is performed.

## Capacity scenarios and reports

POST `/scenarios/simulate` accepts **exactly**:

```json
{"baseline_visitors":100,"capacity":120,"demand_change_percent":50,"available_capacity_percent":50}
```

All values must be finite numbers (booleans rejected). Bounds: baseline_visitors 0..1e9; capacity 1..1e9; demand_change_percent -100..1000; available_capacity_percent 0..100. Both demand and capacity must use the same user-selected period and visitor-place units. Values are explicit hypothetical assumptions, never loaded from fixed UI telemetry.

Response: `{status:"HYPOTHETICAL_CAPACITY_ACCOUNTING",parameters:object,model_version:"capacity-accounting-v1",baseline:Outcome,scenario:Outcome,delta_unserved_visitors:number,units:string,is_prediction:false,assumptions:string[],limitations:string[]}`.

`Outcome`: `{visitors:number,available_capacity:number,served_visitors:number,unserved_visitors:number,utilization_ratio:number|null}`.

Demand = baseline_visitors × (1 + change/100); available capacity = capacity × availability/100; served = min(demand, capacity); unserved = max(0, demand − capacity). Baseline has zero demand change and full capacity. Utilization is null at zero available capacity. No rainfall/stress, evacuation, queue-time or road-risk model is claimed. Phase 2 uses this exact schema and removes the original arbitrary weighted stress/delay outputs. Rainfall, road, accommodation-preset and fleet controls are retained only as explicitly unmodeled context.

POST `/reports/generate`: `{}` or `{scenario:<complete scenario request>}` only. Returns `{report_type:"safarsaathi_evidence_json",generated_utc,models:array,dataset_inventory:object,scenario:ScenarioResponse|null,sources:string[],limitations:string[]}`. It reads current registry/file stats and recomputes any scenario; client-supplied conclusions/results are rejected. This is a JSON report, not a PDF, persisted report archive or emergency brief. If required data is missing it returns 503 rather than an invented report.

POST `/optimization/solve`: `{}` is the only availability request supported. Returns 501 `{status:"NOT_IMPLEMENTED",detail,requirements:string[]}`. Extra inputs return 422. No intervention costs, benefit model, decision variables or calibrated objective are available, so GA/PSO solutions are not fabricated.

## Errors, methods and CORS

Errors consistently contain `{detail:string}`; unavailable responses may also include `status`/`model_id`. Codes: 400 malformed JSON/nonfinite JSON constants, 404 unknown route/model/location, 405 wrong method, 411 no Content-Length, 413 >1,000,000-byte request, 415 non-JSON POST, 422 invalid input, 501 absent optimizer, 503 missing/corrupt artifacts or required data, 500 unexpected failure. OPTIONS returns 204. New query errors are 422. Existing unknown query suffixes on legacy routes are unsupported (404).

Allowed origins are exactly localhost or 127.0.0.1 on ports 5173 (default dev), 4173 (preview), 3000 (existing explicit-port compatibility). No wildcard or credentials flag. The service is loopback only; CORS is not authentication. Sanitized warning/error logs contain failure categories, never reviews/request bodies or exception traces/secret paths. An external deployment would require separately configured authentication, origin policy and operational hardening.
