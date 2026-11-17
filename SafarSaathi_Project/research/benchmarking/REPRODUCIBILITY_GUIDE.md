# Reproduce Phase 3

Run from SafarSaathi_Project using the existing environment. Preserve the sibling SafarSaathi_Datasets collection; no download is needed. Evidence is derived into research/ only. Scripts overwrite their own derived reports, not raw datasets or models. Baseline checkpoints must be retained independently.

```powershell
$env:PYTHONPATH='src'
$env:OMP_NUM_THREADS='1'
$env:OPENBLAS_NUM_THREADS='1'
python scripts/phase3_model_validation.py
python scripts/phase3_geospatial_satellite.py
python scripts/phase3_event_sources.py
python scripts/phase3_research.py
python -m pytest tests -q --basetemp research/regression_tmp --junitxml research/backend_regression.xml
python -m safarsaathi_ml.cli serve --port 8011
# In a separate terminal:
cd frontend
$env:SAFARSAATHI_TEST_API='http://127.0.0.1:8011'
npm test
npm run lint
node ../scripts/frontend_runner.mjs build
cd ..
python scripts/phase3_finalize.py
```

Check the port is unused before launching the loopback server. Browser preview uses Vite's configured backend URL; restart the backend after code changes. A cached or older process is not evidence of the current implementation. phase3_event_sources.py regenerates local inventory and source ledger; official online content may change or be unavailable. Do not interpret inaccessible PDF material as inspected evidence.

Model environment versions are recorded in evaluation_results.json; the installed GIS audit uses pyproj, shapely, pyosmium, tifffile and Pillow (no rasterio requirement). Baseline Python 3.14.6, NumPy 2.4.6, pandas 2.3.3, scikit-learn 1.9.1. Reuse compatible artifact dependencies. The deep GIS run streams a 223 MB PBF and hashes ~11 GB of local rasters; it is intentionally slower than unit tests. --reuse-osm reuses a prior derived OSM audit and must be treated as cached evidence. --skip-hashes does not validate checksums.

The model seed is 20261030; saved training seeds/configuration are retained in the inventory. GA/PSO primary seeds 5,23,79, population16, iterations30; budget sensitivity includes8×10 and32×60. Wall times vary by host; same-seed allocations and traces are asserted, not wall-time identity. All reported results are historical replay or explicitly hypothetical. New model selection requires untouched future/spatial validation.
