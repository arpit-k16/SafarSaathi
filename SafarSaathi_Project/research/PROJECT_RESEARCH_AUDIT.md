# Research audit and preservation

The project is a React/Vite frontend with a Python stdlib HTTP API and six saved inference pipelines. There is no Git repository in this checkout; the safe checkpoint is research/_baseline/checkpoint, with 576 original application/model file records and 2,561 dataset stat records. Existing integration documentation was reviewed before implementation. Baseline tests were independently rerun before edits.

Minimal frontend changes add evidence notices and the hypothetical allocation form inside existing auxiliary panels, using existing color/spacing utilities; CSS, fonts, branding, navigation and map assets are retained. Backend architecture and model artifacts are retained. Input/output hardening, narrow optimization routes and parameter-recomputed reports extend existing services. Exact created/modified paths and preservation checks are in CHANGE_MANIFEST.json.


```json
{
  "backend_counts": {
    "tests": 181,
    "failures": 0,
    "errors": 0,
    "skipped": 0
  },
  "model_files_changed": [],
  "raw_stat_changes": 0,
  "inventory_roots": [
    "collection",
    "project_data"
  ]
}
```
