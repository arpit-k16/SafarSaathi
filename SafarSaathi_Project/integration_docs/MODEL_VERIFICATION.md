# Model verification

All six active registered artifacts were loaded and task-specific validation/inference was executed. `artifact_validation.json` is the actual command output; `startup_smoke.json` records HTTP responses from a fresh CLI process. No model was retrained or silently substituted. Unregistered older NLP versions remain on disk.

| Model | Actual artifact | Recorded version | Executed verification |
|---|---|---|---|
| nlp-20261024T182952Z | `models/nlp/nlp-20261024T182952Z/pipeline.joblib` | Not separately recorded; registry ID includes timestamp | Artifact reload and sample prediction |
| tourism_demand_forecaster | `models/tourism_demand/20261025T111230951433Z/pipeline.joblib` | 20261025T111230951433Z | Artifact reload, saved evaluation replay and valid inference |
| tourism_monthly_fta_forecaster | `models/tourism_monthly_fta/20261025T120954676478Z/pipeline.joblib` | 20261025T120954676478Z | Artifact reload, saved evaluation replay and valid inference |
| flood_segmentation_model | `models/flood_segmentation/20261025T125258870059Z/pipeline.joblib` | 20261025T125258870059Z | Artifact reload and sample prediction |
| north_indian_cyclone_count_forecaster | `models/cyclone_count/20261025T132148112617Z/pipeline.joblib` | 20261025T132148112617Z | Artifact reload, saved evaluation replay and valid inference |
| india_pm25_exposure_forecaster | `models/pm25/20261025T132148214483Z/pipeline.joblib` | 20261025T132148214483Z | Artifact reload, saved evaluation replay and valid inference |

Original input feature order/types and preprocessing are retained in the pipeline and feature_schema.json/metadata files; API_CONTRACT.md documents supported HTTP schemas. Review TF-IDF preprocessing is inside the persisted pipeline. Annual/scoped lag and monthly features are derived by their existing inference classes; arbitrary feature arrays are not accepted. No model accuracy/version/training date was invented. Full measured historical metrics remain in metadata, docs/MODEL_CARDS.md and the validation evidence.

Scope limits: annual arrivals end 2019; monthly FTA ends 2024-12; cyclone counts are basin-level archive IDs; PM2.5 is national modeled exposure ending 2023. These are historical extrapolations, not current 2026 local measurements. Forecast implementations include simple selected baselines as well as fitted estimators; six artifacts do not mean six neural networks.

Flood verification includes schema-valid zero-tile inference and existing synthetic/format tests; no new full raw-image processing or scientific holdout evaluation was run. Its persisted held-out precision is low (see original card); benchmark reference water is not a live emergency flood warning. NLP sample inference does not revalidate accuracy on a new local corpus.

Broad India multi-hazard warning and destination ecological stress: MODEL NOT AVAILABLE because labels/coverage are insufficient. Intervention optimizer: NOT IMPLEMENTED. No capabilities were invented to fill these gaps.

The artifact cache reuses deserialized pipelines, while verifying current file bytes/pins before every cache hit. A regression test confirms repeated loads deserialize once and corrupted bytes still fail.
