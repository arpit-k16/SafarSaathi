"""Assemble evidence-linked Phase 3 reports from executed audit outputs; never train or edit raw data."""
from pathlib import Path
import csv
import hashlib
import json
import platform
import re
import xml.etree.ElementTree as ET

P = Path(__file__).resolve().parents[1]
R = P / 'research'


def read(path):
    return json.loads((R / path).read_text(encoding='utf-8'))


def write(path, text):
    file = R / path
    file.parent.mkdir(parents=True, exist_ok=True)
    file.write_text(text.rstrip() + '\n', encoding='utf-8')


def block(value):
    return '\n```json\n' + json.dumps(value, indent=2, ensure_ascii=False) + '\n```\n'


def csvout(path, rows):
    file = R / path
    file.parent.mkdir(parents=True, exist_ok=True)
    fields = list(dict.fromkeys(k for row in rows for k in row))
    with file.open('w', newline='', encoding='utf-8') as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader(); writer.writerows(rows)


def main():
    results = read('model_validation/evaluation_results.json')
    comparisons = list(csv.DictReader((R / 'model_validation/MODEL_COMPARISON.csv').open(encoding='utf-8')))
    opts = list(csv.DictReader((R / 'optimization/OPTIMIZATION_COMPARISON.csv').open(encoding='utf-8')))
    inventory = read('model_validation/MODEL_INVENTORY.json')
    rows = []
    for row in comparisons:
        artifact = next((m for m in inventory if m['model_id'] == row['model_id']), {})
        source_result = next((v for v in results.values() if isinstance(v, dict) and v.get('model_id') == row['model_id']), {})
        source_version = artifact.get('dataset_provenance') or {k: v for k, v in source_result.items() if 'source' in k or 'data' == k or 'archive' in k}
        rows.append({**row, 'experiment_id': row['experiment_id'] + '_' + row['split'], 'dataset_version': json.dumps(source_version),
                     'random_seed': results['seed'], 'training_configuration': 'Frozen saved artifact or source-aligned baseline; see MODEL_INVENTORY.json and evaluation_results.json',
                     'limitations': 'Known historical holdout replay; horizons/algorithms examined after original evaluation; not an untouched external test.',
                     'artifact_sha256': artifact.get('sha256', '')})
    rows += [{**r, 'model_version': 'capacity-allocation-v1', 'random_seed': r['seed'],
              'training_configuration': f"population={r['population']};iterations={r['iterations']}",
              'evaluation': 'feasibility, repeated-seed replay and convex numerical reference',
              'limitations': 'Hypothetical inputs; assumed proxies; no empirical intervention benefits'} for r in opts]
    for i, row in enumerate(csv.DictReader((R / 'scenario_validation/SCENARIO_SENSITIVITY_RESULTS.csv').open(encoding='utf-8'))):
        rows.append({'experiment_id': f'scenario_{i:03}', 'dataset_version': 'Explicit input row in SCENARIO_SENSITIVITY_RESULTS.csv',
                     'model_version': 'capacity-scenario-v1', 'random_seed': 'none deterministic',
                     'evaluation': 'independent algebra and conservation', 'metrics': json.dumps(row),
                     'training_configuration': 'No learned parameters', 'limitations': 'Capacity arithmetic only; no rainfall/evacuation physics'})
    for component, evidence in [('geospatial', 'geospatial/validation_test_results.json'), ('satellite', 'satellite_validation/satellite_audit.json')]:
        file = R / evidence
        if file.exists():
            data = json.loads(file.read_text())
            rows.append({'experiment_id': component + '_native_audit', 'dataset_version': 'Original local sources; individual source hashes/stat inventory retained in ' + evidence,
                         'model_version': 'none data audit', 'random_seed': 'none deterministic', 'training_configuration': 'No model fitting',
                         'evaluation': 'Native source/geometry/integrity checks', 'metrics': json.dumps({k: v for k,v in data.items() if not isinstance(v,(list,dict))}),
                         'limitations': 'No independent operational route, pixel ground truth or event skill validation'})
    csvout('benchmarking/EXPERIMENT_REGISTRY.csv', rows)

    models = [(k, v) for k, v in results.items() if isinstance(v, dict) and 'model_id' in v]
    data_text = '# Data validation and partition audit\n\nExecuted with `scripts/phase3_model_validation.py`; detailed source hashes, periods, labels and partitions are retained below. No raw data were changed. Missing trailing annual targets are excluded, never filled with invented values. These checks do not establish every possible semantic label error or external ground truth.\n'
    for key, value in models:
        data_text += '\n## ' + value['model_id'] + '\n' + block({k: v for k, v in value.items() if k in ['data', 'source_profile', 'metadata_inventory', 'split_country_groups', 'saved_splits_reproduced', 'train_test_event_overlap', 'train_test_country_overlap', 'threshold']})
    data_text += '\nNLP TF-IDF vocabulary/IDF were independently fitted on the recovered training split and matched the saved transform. Exact and normalized text overlap are checked; unavailable hotel/reviewer/time identifiers prevent group leakage certification. Flood country/event holdouts are checked from delivered metadata. No pixel-independent confidence interval is claimed. The annual final inference artifact is refit on the full observed history; historical metrics are replayed with the original frozen split rather than evaluating that refit on its training years. Baselines and horizon diagnostics are exploratory comparisons on already known test periods.\n'
    write('model_validation/DATA_VALIDATION_REPORT.md', data_text)
    model_text = '# Six-model evaluation\n\nAll six stored metric sets were reproduced. This is historical holdout replay, not prospective certification. Models and raw data remain unchanged.\n\n![Executed horizon, calibration and geography comparisons](model_benchmark.png)\n\n| Model | Algorithm | Stored metrics reproduced |\n|---|---|---|\n'
    for key, value in models:
        model_text += f"| {value['model_id']} | {str(value['algorithm']).replace(chr(10), ' ')} | {value['stored_metrics_reproduced']} |\n"
    model_text += '\nFull precision metrics, denominators, per-horizon baselines and residual quantiles: [MODEL_COMPARISON.csv](MODEL_COMPARISON.csv), [evaluation_results.json](evaluation_results.json). Positive-class confusion matrices and calibration bins are retained in the JSON; predictions are separate CSVs.\n\nNLP accuracy 0.8500 and macro-F1 0.8495 exceed the training-majority accuracy 0.5245. ROC-AUC 0.9249, PR-AUC 0.9251, Brier 0.1158 and 10-bin ECE 0.0786 describe the source holdout.\n\nAnnual one-step drift MAE 578,589 versus persistence 961,400 uses only five test targets. Monthly persistence performs well at one month (MAE 100,187 versus seasonal-naive 150,104), but at six months its MAE 266,022 is worse than seasonal-naive 75,519. The seasonal diagnostic therefore has about 71.6% lower error at six months on this known period. This does not authorize selecting a new production model on the test set. PM2.5 negative R² (−0.9188) rules out presenting its output as a strong explanatory forecast. Consult the CSV for cyclone count versus persistence/mean comparisons; archive counts are not local event probabilities.\n\nFlood reference-positive precision 0.3302, recall 0.8372, Dice 0.4736 and IoU 0.3103 across 42 heldout tiles, seven events and four countries reveal substantial false positives and geographic variation. Permanent water is included in the target, so this is not event-specific temporary flood validation. Pooled pixel calibration is descriptive under spatial dependence.\n\nNo replacement artifact was promoted: additional untouched periods, external locations and adequate event counts are needed. Hardening rejects malformed model outputs without changing learned predictions.\n'
    write('model_validation/MODEL_EVALUATION_REPORT.md', model_text)
    with (R / 'model_validation/MODEL_EVALUATION_REPORT.md').open('a', encoding='utf-8') as stream:
        stream.write('\n## Forecast residual bands and validation scope\n\nBands use validation residuals only where available; they are exploratory, uncalibrated and may have very small samples. Coverage/width cannot be equated with operational assurance.\n')
        for key, value in models:
            if 'residual_bands' in value:
                stream.write('\n### ' + value['model_id'] + '\n' + block(value['residual_bands']))
    write('model_validation/MODEL_LIMITATIONS.md', '# Model limitations\n\n- Known holdouts are reused for audit; new horizon/baseline comparisons are exploratory, not a new independent trial.\n- Annual history ends in 2019 and has five original test targets; no contemporary national or local demand validity follows.\n- Monthly persistence is horizon-sensitive and weak at longer horizons. National FTA excludes NRI and cannot be interpreted as destination occupancy.\n- Cyclone archive coverage and basin counts are not local hazard probabilities; annual PM2.5 is national modeled exposure, not a calibrated sensor forecast.\n- NLP labels are source-domain binary sentiment; entity/time metadata and verified local community labels are absent. The selected Aditya1010 source manifest records Apache-2.0; do not generalize other corpus licenses to it.\n- Flood labels combine permanent water and flood extent, and test pixels are spatially dependent. Four country holdouts do not validate Nepal or Uttarakhand transfer.\n- Residual quantiles are descriptive, not calibrated prediction intervals. Test coverage, if recorded for a validation-residual band, is explicitly exploratory with small samples. No operational confidence percentage is supplied.\n- No model is certified for emergency dispatch, casualties, road closure or evacuation decisions.\n')

    suite = ET.parse(R / 'backend_regression.xml').getroot() if (R / 'backend_regression.xml').exists() else None
    counts = {k: sum(int(s.get(k, 0)) for s in suite.iter('testsuite')) for k in ['tests', 'failures', 'errors', 'skipped']} if suite is not None else {'status': 'NOT_RUN'}
    frontend_log = (R / 'frontend_tests.log').read_text(encoding='utf-8', errors='replace') if (R / 'frontend_tests.log').exists() else ''
    frontend_counts = {key: int(match.group(1)) if (match := re.search(r'\b' + label + r'\s+(\d+)', frontend_log)) else None for key, label in [('passed', 'pass'), ('failed', 'fail'), ('skipped', 'skipped')]}
    geo_path = R / 'geospatial/validation_test_results.json'
    geo = json.loads(geo_path.read_text()) if geo_path.exists() else {'status': 'PENDING'}
    checks = [
        ('Sources → ingestion', 'VERIFIED LIMITED', 'Existing catalog/file adapters and source hashes; no live ingestion claimed'),
        ('Ingestion → validation', 'VERIFIED LIMITED', 'Six source-aligned audits, missing/duplicate/type/temporal checks'),
        ('Validation → preprocessing', 'VERIFIED LIMITED', 'Recovered train-only TF-IDF; chronological forecasts; geographic flood holdout'),
        ('Preprocessing → inference', 'VERIFIED LIMITED', 'Six stored metric sets reproduced; malformed flood output fails unavailable'),
        ('Inference → geospatial hazard analysis', 'UNSUPPORTED', 'No matching local hazard reference or event-period registered raster pipeline'),
        ('Geospatial → digital twin', 'EXPLORATORY', 'Static source points and schematic SVG; no operational registered twin'),
        ('Digital twin → what-if', 'EXPERIMENTAL', 'Explicit user capacity inputs; not inferred road/hazard physics'),
        ('What-if → optimization', 'EXPERIMENTAL', 'Separate explicit hypothetical multi-destination inputs; no automatic empirical hazard join'),
        ('Optimization → report', 'VERIFIED LIMITED', 'HTTP report recomputes submitted parameters and returns actual allocations'),
        ('Frontend → API', 'SEE RUNTIME EVIDENCE', 'Node integration, build/lint and browser evidence logged separately; do not infer visual validation from unit tests'),
        ('Nepal 2026 event → segmentation metrics', 'NOT EVALUATED', 'No aligned event images/reference mask; cannot score historical accuracy'),
    ]
    csvout('end_to_end/SYSTEM_VALIDATION_MATRIX.csv', [{'connection': a, 'status': b, 'evidence_or_blocker': c} for a, b, c in checks])
    write('end_to_end/END_TO_END_TEST_REPORT.md', '# End-to-end verification\n\nThe requested empirical chain is only partially supported. Each connection is separately recorded in SYSTEM_VALIDATION_MATRIX.csv. A passing software test is not geographic or event validation.\n\nBefore modifications: 153 backend tests passed, no skips; 9 frontend tests passed, no skips; build and lint passed. Checkpoint and logs are in ../_baseline.\n\nFinal backend XML counts:\n' + block(counts) + '\nFinal frontend results: ../frontend_tests.log; build: ../frontend_build.log; lint: ../frontend_lint.log. The first frontend rerun skipped its server-dependent case; the subsequent configured API run supersedes it. New optimization/HTTP/hardening tests initially passed 28/28. Final full-suite XML is authoritative.\n\nGeographic checks:\n' + block(geo) + '\nControlled tests cover missing/infeasible/invalid/nonfinite inputs, unavailable metadata and malformed flood outputs. Model audit recomputed all six stored metric sets. Scenario audit independently checked 21 sensitivity cases; optimizer audit ran 18 primary cases with repeated seeds and six budget checks. Neither test suite connects Nepal observations to local tourist stress: those aligned inputs are absent.\n')
    write('end_to_end/KNOWN_FAILURES.md', '# Known failures and unsupported connections\n\n- Operational hazard → local road closures → calibrated tourism stress → intervention benefits is not implemented or scientifically validated.\n- No 2026 Nepal event images/reference masks, verified closures or tourist panel; historical flood skill remains not evaluated.\n- Full-cloud/quality-layer satellite metadata and image readability require explicit flags; checksum matches cannot prove valid georeferencing or clear ground.\n- Sentinel-1 GCP grid lacks affine registration; no terrain correction/radiometric preparation or raw-to-STURM conversion exists.\n- The first GIS audit stopped at an unrecognized quality JP2; the revised audit records unreadable headers rather than suppressing them. Read satellite_audit.json for actual totals.\n- Existing national models cannot populate local telemetry counts. Landing live telemetry N/A remains honest.\n- Legacy operational optimization/solve returns 501; hypothetical allocation uses optimization/allocate.\n- The approval-review usage limit interrupted one test command; it was not executed then. A later approved rerun passed.\n')

    write('benchmarking/RESEARCH_BENCHMARK_REPORT.md', '# Research benchmark\n\nThe experiment registry combines actual model/baseline/horizon results, 21 scenario cases and 18 seeded optimizer experiments. Dataset and artifact hashes, seed/configuration, evaluation scope and limitations are retained without converting proxy objectives into empirical accuracy.\n\n![Model comparisons](../model_validation/model_benchmark.png)\n\nNLP materially exceeds its dummy baseline. Annual one-step drift outperforms persistence on five targets. Monthly longer-horizon seasonal-naive is substantially better on the known holdout; no model promotion follows from selecting against this test set. Flood geographic performance varies and precision is low. PM2.5 R² is negative. GA and PSO satisfy this small hypothetical convex problem, but no claim of algorithmic superiority follows from one fixture. Numerical-reference gaps, repeatability, exposure/utilization components, wall times and seed variation are preserved in ../optimization/OPTIMIZATION_COMPARISON.csv. Satellite header/integrity and OSM proximity audits are data checks, not predictive benchmarks.\n\nNo full raw-scene or Nepal event benchmark exists. These missing experiments are recorded as unsupported rather than assigned fabricated metrics.\n')
    write('benchmarking/REPRODUCIBILITY_GUIDE.md', '''# Reproduce Phase 3

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
''')

    status = {'status': 'RESEARCH EVALUATED · LIMITED HISTORICAL AND HYPOTHETICAL SCOPE', 'date': '2026-10-30',
              'findings': ['Six stored model metric sets reproduced on known historical holdouts; this is not prospective certification.',
                           'Monthly persistence weakens at longer horizons; PM2.5 heldout R² is negative.',
                           'Flood reference-positive precision 0.330 and IoU 0.310; permanent water is included in its labels.',
                           'Rasuwagadhi event date/corridor verified; no aligned local imagery/reference masks for event accuracy.',
                           'GA/PSO available only for explicit hypothetical capacity allocation; no empirical intervention benefits.',
                           'Native satellite metadata require cloud-mask and registration checks; no live sensor feed exists.'],
              'geospatial_audit_status': geo['status']}
    write('research_status.json', json.dumps(status, indent=2))

    before = read('_baseline/application_manifest.json')
    before_map = {r['path']: r for r in before}
    modified, missing, artifacts_changed = [], [], []
    for row in before:
        file = P / row['path']
        if not file.exists(): missing.append(row['path']); continue
        digest = hashlib.sha256(file.read_bytes()).hexdigest()
        if digest != row['sha256']:
            modified.append({'path': row['path'], 'before_sha256': row['sha256'], 'after_sha256': digest})
            if row['path'].startswith('models/'): artifacts_changed.append(row['path'])
    created = []
    for root in ['src', 'tests', 'scripts', 'frontend/src', 'research']:
        for file in (P / root).rglob('*'):
            relative = file.relative_to(P).as_posix()
            if file.is_file() and relative not in before_map and not any(s == '__pycache__' or s == '_baseline' or s.startswith(('regression_tmp', 'research_api_tmp', 'research_unit_tmp')) for s in file.parts):
                created.append(relative)
    collection = P.parent / 'SafarSaathi_Datasets'
    changed_raw = []
    roots = {'collection': collection, 'project_data': P / 'data', 'project': P / 'data'}
    root_names = sorted({r['root'] for r in read('_baseline/dataset_inventory.json')})
    for row in read('_baseline/dataset_inventory.json'):
        root = roots.get(row['root'])
        if root is None: continue
        file = root / row['path']
        if not file.exists() or file.stat().st_size != row['bytes'] or file.stat().st_mtime_ns != row['mtime_ns']:
            changed_raw.append(str(file))
    manifest = {'modified': modified, 'created': sorted(set(created)), 'missing_baseline_files': missing,
                'model_files_changed': artifacts_changed, 'raw_inventory_stat_changes': changed_raw,
                'raw_inventory_roots': root_names, 'integrity_scope': 'Models SHA256; original dataset size/mtime inventory; raster content hashes in satellite audit. Not a full raw collection rehash.'}
    manifest['created_scope'] = 'Code, tests, scripts, frontend sources and durable research evidence. Excludes checkpoint, bytecode and pytest scratch directories.'
    write('CHANGE_MANIFEST.json', json.dumps(manifest, indent=2))
    write('PROJECT_RESEARCH_AUDIT.md', '# Research audit and preservation\n\nThe project is a React/Vite frontend with a Python stdlib HTTP API and six saved inference pipelines. There is no Git repository in this checkout; the safe checkpoint is research/_baseline/checkpoint, with 576 original application/model file records and 2,561 dataset stat records. Existing integration documentation was reviewed before implementation. Baseline tests were independently rerun before edits.\n\nMinimal frontend changes add evidence notices and the hypothetical allocation form inside existing auxiliary panels, using existing color/spacing utilities; CSS, fonts, branding, navigation and map assets are retained. Backend architecture and model artifacts are retained. Input/output hardening, narrow optimization routes and parameter-recomputed reports extend existing services. Exact created/modified paths and preservation checks are in CHANGE_MANIFEST.json.\n\n' + block({'backend_counts': counts, 'model_files_changed': artifacts_changed, 'raw_stat_changes': len(changed_raw), 'inventory_roots': root_names}))
    final = '''# SafarSaathi Phase 3 research validation

## 1. Project overview
SafarSaathi remains a local research prototype using historical national tourism/environment series, source-domain reviews, a preprocessed flood benchmark, static GIS and native satellite archives. Existing UI design and model artifacts are preserved; this work establishes bounded evidence, not operational readiness.

## 2. Research objectives
Audit six pipelines, reproduce appropriate metrics/baselines, check native GIS/image provenance, verify the Nepal event, test capacity arithmetic, implement genuine seeded GA/PSO, and expose only supported research functions. VERIFIED means the stated check was executed; EXPERIMENTAL and EXPLORATORY identify assumptions and retrospective analysis. Unsupported claims and future work remain explicit.

## 3. Dataset inventory
Baseline contains 2,561 file stat records. Model inventories retain artifact/source hashes, feature/target schemas and periods. Annual observed arrivals end in2019 despite later null source dates. Regional Uttarakhand satellite scenes do not cover a2026 Nepal event. No raw datasets were edited; preservation scope and exact changes are in CHANGE_MANIFEST.json.

## 4. Six-model evaluation
VERIFIED: all six stored metric sets reproduced. NLP accuracy0.8500, macro-F1 0.8495, ROC-AUC0.9249, PR-AUC0.9251. Flood precision0.3302, recall0.8372, Dice0.4736, IoU0.3103;42tiles/sevenevents/fourcountries. National annual/monthly/cyclone/PM2.5 metrics and denominators are in model_validation/MODEL_COMPARISON.csv. PM2.5 R²−0.9188 is a material weakness. Calibration bins/residuals are descriptive; no calibrated operational confidence claimed.

## 5. Baseline comparison
NLP majority accuracy0.5245. Annual drift one-step MAE578,589 versus persistence961,400 on five test targets. Monthly persistence one-month MAE100,187 versus seasonal150,104, but six-month MAE266,022 versus seasonal75,519. EXPLORATORY: seasonal baseline is substantially stronger at the longer horizon on this known period. No model was promoted by selecting on the test set. [Executed comparisons](model_validation/MODEL_EVALUATION_REPORT.md).

![Model benchmark](model_validation/model_benchmark.png)

## 6. Geospatial validation
Native longitude/latitude validity, WGS84 ellipsoidal checks, local AEQD metric proximity, clipped OSM shared-node connectivity and coordinate/grid displacement are documented in geospatial/. Source POWER points are not attraction boundaries. Static OSM hospitals are tags/proxies, not verified operating facilities; connectivity does not establish routing. The frontend map remains schematic. Hazard polygons and field reference data are missing.

## 7. Rasuwagadhi case study
VERIFIED event date/corridor:26August2026, BhoteKoshi/Rasuwa, based on the [Nepal Ministry of Home Affairs appeal](https://www.moha.gov.np/en/post/ha-ra-tha-ka-apa-l-11) and [ICIMOD preliminary report record](https://lib.icimod.org/records/qdvc1-tc123). ICIMOD describes a cascading rock/ice/debris process; no conventional GLOF classification is inferred. Quantitative model validation NOT EVALUATED: no aligned event imagery/reference masks, closures or tourist panel. Inaccessible PDF material is not treated as inspected evidence. See flood_case_study/ for source ledger and limitations.

## 8. Scenario validation
VERIFIED arithmetic on21controlled sensitivity cases, independent formula checks, deterministic replay and conservation. Demand, base load, capacity and availability effects are recorded in scenario_validation/. EXPERIMENTAL capacity pressure does not model rainfall, landslide mechanics, evacuation or casualties. Unsupported physical parameters are rejected.

## 9. GA/PSO evaluation
EXPERIMENTAL genuine tournament/blend/mutation/elitist GA and inertia/cognitive/social PSO. Capped-simplex repair enforces continuous nonnegative allocation and demand conservation within minimum effective/road/resource capacities.18primary seeded experiments, exact allocation/trace replay and six budget checks; maximum capacity violation0, largest numerical-reference gap about4.68e−7 objective units on the explicit fixture. Both algorithms retain a proportional-capacity baseline. Exposure weights are assumptions, not learned benefits. No global optimum, causal gain or empirical algorithm superiority is claimed. See optimization/ and formulation_v1 metadata/API.

## 10. Satellite validation
Native raster checksums, header dimensions, delivered product identities, sensing dates, coverage and pilot intersections are audited. Sentinel-1 VV/VH GRD source has GCP tiepoints without affine registration: terrain/radiometric correction and co-registration remain required. Sentinel-2 wrapper/actual processing baselines differ; SCL cloud classification is checked against suspicious zero-cloud metadata. Unreadable quality layers are flagged. No raw-scene flood accuracy or cloud-free ground claim follows from integrity. See satellite_validation/ for actual counts and denominator definitions.

## 11. End-to-end results
Baseline153backend+9frontend tests/build/lint passed before edits. Final machine-readable results and connection statuses are in end_to_end/END_TO_END_TEST_REPORT.md and SYSTEM_VALIDATION_MATRIX.csv. The empirical hazard→geospatial exposure→digital twin→intervention chain is UNSUPPORTED because aligned inputs/target validation are absent. Separately, hypothetical allocation→HTTP→recomputed JSON report is tested. Unit tests do not imply browser or scientific event validation.

## 12. Reproducibility
Run the scripts/commands in benchmarking/REPRODUCIBILITY_GUIDE.md. EXPERIMENT_REGISTRY.csv records actual models/baselines/horizons, scenarios and seeded optimizers. Exact hashes, configurations, predictions and limitations are retained in JSON/CSV. CHANGE_MANIFEST.json lists exact created/modified paths, unchanged-artifact checks and raw inventory preservation scope. No retraining or raw downloads were performed.

## 13. Limitations
Known test periods have been revisited; no new untouched prospective evaluation. Sparse annual/event samples, spatial correlation, source-domain labels, national/local scale mismatch, missing Nepal aligned references and uncertain infrastructure status limit generalization. Neither optimizer nor scenario proxies validate actual hazard, emergency action or intervention effectiveness. N/A live telemetry remains correct. Scientific validation is incomplete wherever essential reference data are missing.

## 14. Future research directions
FUTURE WORK: obtain authorized event-aligned registered Sentinel scenes and target-compatible independent masks; validate geographic registration and local infrastructure; assemble local temporal demand/exposure observations; reserve untouched time/event/spatial splits; assess horizon-specific forecast selection and calibrated intervals; validate intervention costs/outcomes before operational optimization. Use prospective evaluation to decide model promotion rather than this retrospective test comparison.
'''
    final += '\n## Executed release evidence\n' + block({'backend': counts, 'frontend': {**frontend_counts, 'evidence': 'frontend_tests.log'}, 'geospatial': geo, 'models_changed': artifacts_changed, 'raw_stat_changes': len(changed_raw)})
    final += '\nExact deliverable and change paths: [CHANGE_MANIFEST.json](CHANGE_MANIFEST.json). Browser actions/results: [BROWSER_VERIFICATION.md](end_to_end/BROWSER_VERIFICATION.md). The 181 backend and9 frontend counts refer to this run; they are not predictions for a different installation.\n'
    write('FINAL_RESEARCH_VALIDATION_REPORT.md', final)
    print(json.dumps({'models_evaluated': len(models), 'registry_rows': len(rows), 'backend': counts, 'geospatial': geo['status'], 'model_files_changed': artifacts_changed, 'raw_stat_changes': len(changed_raw)}))


if __name__ == '__main__':
    main()
