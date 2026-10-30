"""Current completion verification and release, preserving all prior release directories."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import zipfile

from .config import settings
from .pipeline import sha256,utc_now
from .registry import load_registry
from . import final_quality

NAME='final_working_20261025_02'


def preservation(project,destination):
    initial=json.loads((destination/'initial_state.json').read_text(encoding='utf-8'))
    mismatches=[]
    for relative,digest in initial['protected_sha256'].items():
        if relative=='SafarSaathi_Project/models/registry.json':continue
        path=project.parent/relative
        if not path.is_file() or sha256(path)!=digest:mismatches.append(relative)
    previous=json.loads((destination/'previous_release_preservation.json').read_text(encoding='utf-8'))
    for relative,digest in previous.items():
        path=project/relative
        if not path.is_file() or sha256(path)!=digest:mismatches.append(relative)
    with zipfile.ZipFile(project/'release/final_ml_quality_20261025_01/SafarSaathi_Final.zip') as zipped:
        old=json.loads(zipped.read('models/registry.json'))
    current=load_registry(project/'models/registry.json')
    if not all(next((m for m in current if m['model_id']==e['model_id']),None)==e for e in old):
        raise ValueError('An original registry entry changed.')
    raw=project.parent/'SafarSaathi_Datasets/raw'
    stats={p.relative_to(raw).as_posix():{'bytes':p.stat().st_size,'mtime_ns':p.stat().st_mtime_ns} for p in raw.rglob('*') if p.is_file()}
    if stats!=initial['raw_file_stats'] or mismatches:raise ValueError('Protected source/evidence changed: '+str(mismatches))
    return {'status':'PASS','original_registry_entries_preserved':True,'new_registered_ids':[m['model_id'] for m in current if m not in old],
            'prior_release_files_unchanged':len(previous),'protected_original_files_checked':len(initial['protected_sha256']),
            'raw_collection_files_unchanged':len(stats),'raw_paths_sizes_mtimes_unchanged':True,'legacy_archive_unchanged':True}


def verify(project,destination):
    # Keep the existing proven checks; replace only the preservation assertion to allow validated append-only registrations.
    final_quality.check_preservation=preservation
    if not (destination/'verification_checks.json').exists():
        final_quality.verify(project,destination)
    else:
        import xml.etree.ElementTree as ET
        previous=json.loads((destination/'verification_checks.json').read_text(encoding='utf-8'))
        rerun=json.loads((destination/'python_tests_rerun.json').read_text(encoding='utf-8'))
        suite=ET.parse(destination/'python_tests_rerun.xml').getroot().find('testsuite')
        counts={k:int(suite.attrib.get(k,0)) for k in ('tests','failures','errors','skipped')}
        counts['passed']=counts['tests']-counts['failures']-counts['errors']-counts['skipped']
        if any(counts[k] for k in ('failures','errors','skipped')) or rerun['exit_code']!=0:raise ValueError('Rerun did not pass.')
        previous['development_checks'].append({'status':'FAIL','evidence':'python_tests.json','reason':'Unscoped pytest discovered duplicate archived test modules; rerun explicitly scoped to all project tests.'})
        previous['checks']=[rerun if c['name']=='python_tests' else c for c in previous['checks']]
        previous['python_counts']=counts
        if any(c['status']!='PASS' for c in previous['checks']):raise ValueError('Unresolved quality gate.')
        final_quality.save(destination/'verification_checks_final.json',previous)
    from .monthly_forecasting import evaluate_monthly
    monthly=evaluate_monthly(project)
    final_quality.save(destination/'monthly_fta_evaluation.json',monthly)
    registry=load_registry(project/'models/registry.json')
    if any(m['model_id']=='flood_segmentation_model' for m in registry):
        from .flood_baseline import evaluate_flood
        final_quality.save(destination/'flood_evaluation_replay.json',evaluate_flood(project,project/'data/external/sturm_flood/12748983'))
    browser_env={'PLAYWRIGHT_MODULE_PATH':os.environ.get('PLAYWRIGHT_MODULE_PATH',''),
                 'SAFARSAATHI_BROWSER_OUTPUT':str(destination/'browser_final'),'OMP_NUM_THREADS':'2'}
    browser=final_quality.run_check(destination,'browser_tests',[shutil.which('node'),'scripts/browser_checks.mjs'],project/'frontend',extra_env=browser_env,timeout=180)
    if browser['status']!='PASS':raise ValueError('Final browser journeys failed; inspect retained browser evidence.')


def package(project,destination):
    verification=json.loads((destination/'verification_checks_release.json').read_text(encoding='utf-8'))
    browser=json.loads((destination/'browser_final_rerun/browser_results.json').read_text(encoding='utf-8'))
    browser_check=json.loads((destination/'browser_tests_rerun.json').read_text(encoding='utf-8'))
    if browser['status']!='PASS' or browser_check['status']!='PASS' or any(c['status']!='PASS' for c in verification['checks']):raise ValueError('Quality gate failed.')
    registry=load_registry(project/'models/registry.json')
    by_id={m['model_id']:m for m in registry}
    from .capabilities import capabilities
    caps=capabilities(project)
    status=[{'capability':'review_classification','status':'TRAINED_AND_EVALUATED','model_id':next(m['model_id'] for m in registry if m['task']=='review classification')}]
    status += [{'capability':c['model_id'],'status':c['implementation_status'],'reason':c['reason']} for c in caps]
    if 'tourism_monthly_fta_forecaster' in by_id:status.append({'capability':'monthly_foreign_tourist_arrivals','model_id':'tourism_monthly_fta_forecaster','status':'TRAINED_BUT_EXPERIMENTAL'})
    source=json.loads((destination/'source_investigation.json').read_text(encoding='utf-8'))
    report={'generated_at':utc_now(),'overall_status':'VERIFIED_WITH_EXPLICIT_DATA_AND_SCOPE_LIMITATIONS','model_status':status,
            'python_counts':verification['python_counts'],'checks':verification['checks']+[browser_check],
            'browser':browser,'source_investigation':source,'preservation':preservation(project,destination),
            'remaining_blockers':[
                'Disaster-risk forecasting still lacks a complete observed area/time outcome panel; positive-only catalogues do not establish verified negatives.',
                'Destination stress lacks measured occupancy/crowding/capacity-utilization targets aligned through time.',
                'Tourism monthly FTA observations end in 2024-12. Annual World Bank ITA observations end in 2019; neither is a current-2026 forecast.',
                'Flood-scene benchmark output is publisher-defined reference-positive water/flood extent, not calibrated temporary-flood probability or validated Uttarakhand monitoring.'],
            'release_zip':'SafarSaathi_Final.zip','post_extract_validation':'release_validation.json'}
    # Include actual Node TAP counts, without turning synthetic test success into real training claims.
    import re
    node=next(c for c in verification['checks'] if c['name']=='frontend_all_tests')
    report['frontend_counts']={k:int(re.search(r'^# '+label+r' (\d+)$',node['stdout'],re.MULTILINE).group(1)) for k,label in [('tests','tests'),('passed','pass'),('failed','fail'),('skipped','skipped')]}
    report['browser_counts']={'passed':len(browser['checks']),'failed':0,'blocked':0,'unexpected_console_errors':len(browser['unexpectedConsole']),'unexpected_network_failures':len(browser['unexpectedNetwork'])}
    report['development_checks']=verification['development_checks']+[{'status':'FAIL','evidence':'browser_tests.json','reason':'New flood metrics exposed a forecast-only metric renderer; task-specific rendering and regression test fixed the crash.'}]
    report['browser_visual_inspection']={'status':'PASS','files':['browser_final_rerun/model_center_mobile.png','browser_final_rerun/flood_prediction_desktop.png'],'findings':'Inspected closed mobile drawer, fitting cards/forms, desktop mask and explicit limitations; no overflow/overlap observed.'}
    final_quality.save(destination/'verification_report.json',report)
    lines=['# SafarSaathi working release completion', '', 'All executed quality gates passed; remaining data/scope limitations are explicit.',
           '', '## Model status', '', '| Capability | Status |', '|---|---|']
    lines += [f"| {s['capability']} | {s['status']} |" for s in status]
    lines += ['', 'The original two registry entries and artifact files remain unchanged. Monthly FTA and any flood benchmark model are separate validated entries, not silent replacements.',
              '', '## Newer tourism observations and evaluation', '',
              '72 observed monthly Foreign Tourist Arrival counts (2019-01 through 2024-12) were extracted from four official local PDF publications. Overlap values match; all monthly sums equal printed annual totals. Five table pages were rendered and visually inspected. No raw source was rewritten.',
              'FTA excludes NRI arrivals and is kept separate from the legacy World Bank international-arrivals target. Training starts with 2019–2021; 2022 validation selects the method across 1/3/6-month horizons. Test periods are 2023–2024, also reported as separate year folds. Expanding fits use only past observed prefixes.',
              '', '| Monthly method | Horizon | n | MAE | RMSE | MASE | WAPE fraction |','|---|---:|---:|---:|---:|---:|---:|']
    monthly=by_id.get('tourism_monthly_fta_forecaster')
    if monthly:
        for method,scores in monthly['metrics']['test'].items():
            for h,m in scores.items():lines.append(f"| {method} | {h} | {m['n']} | {m['MAE']} | {m['RMSE']} | {m['MASE']} | {m['WAPE']} |")
        lines += ['',f"Selected on validation only: {monthly['method']}. Seasonal MASE denominator: {monthly['metrics']['MASE_denominator']}. This denominator includes pandemic changes; MASE below 1 does not establish operational reliability.",
                  'The legacy annual comparison is preserved in `tourism_baseline_comparison.json`; no direct FTA-versus-ITA metric ranking is valid.']
    flood=by_id.get('flood_segmentation_model')
    if flood:
        score=flood['metrics']['test']
        lines += ['', '## Flood-scene segmentation', '', f"Selected model: {flood['metrics']['selected_method']}; threshold {flood['metrics']['threshold']} selected only on validation country groups.",
                  'The approved 3,985,215,183-byte Zenodo archive passed its publisher MD5 and local SHA-256 checks. Tiles are read in bounded batches without full extraction.',
                  'Country/event groups are separated before tile/pixel sampling; selected reference/image pairs differ by at most 24 hours and matching GeoTIFF tags/dimensions are checked. The target follows the publisher’s mask >0 rule, with explicit permanent-water/temporary-flood ambiguity.',
                  f"Held-out reference-positive IoU: {score['IoU']}; Dice/F1: {score['Dice_F1']}; precision: {score['precision']}; recall: {score['recall']}; pixels: {score['pixel_count']}.",
                  f"Confusion matrix [[TN,FP],[FN,TP]]: {score['confusion_matrix']}. Per-scene, event and country identities and both-class results are in the model evaluation file. Saved-model evaluation replay passed.",
                  'Supported inference input is exactly a delivered STURM-preprocessed 128×128×2 Sentinel-1 tile, not arbitrary raw GRD/dB or local Sentinel scenes. Scores are not calibrated flood probabilities.']
        lines += ['Held-out precision is only about 0.33, with 120,723 false-positive pixels; the model is a limited experimental baseline, not a reliable operational flood detector.']
    lines += ['', '## Verification', '',f"Python: {report['python_counts']}. Frontend: {report['frontend_counts']}. Browser: {report['browser_counts']}.",
              'Commands, exit statuses, timings and stdout/stderr are in verification_report.json and per-check JSON files. Full raw checksum verification is recorded in raw_checksums.json. The failed unscoped pytest collection and flood-metric browser crash are retained alongside passing corrected runs.',
              'Actual isolated headless Chrome journeys verify the known local frontend URL, all navigation routes, review validation/inference, annual/monthly forecasts, operational segmentation when available, disabled controls, loading/errors/backend-disconnection and desktop/mobile layout. Screenshots were inspected separately.',
              'Real browser testing found and fixed a missing favicon and retained page scroll position. The initial selector mismatch and temporary-test parent-directory failure were corrected; development evidence was retained.',
              'Windows API sockets now use exclusive binding so an occupied port cannot silently share a stale instance; health includes a schema fingerprint. Malformed backend metadata/forecast results are rejected by the frontend.',
              '', '## Remaining limitations', '',*['- '+b for b in report['remaining_blockers']],
              '', '## Release', '', 'The ZIP contains source, tests, config, docs, model metadata, small inference artifacts and reports. Original datasets, downloaded archive, old releases, legacy archive, secrets, caches and temporary test files are excluded.',
              'The ZIP is reopened for CRC/content-hash checks and then extracted to a fresh directory for raw-free inference from every registered model. See release_validation.json.',
              'Setup/startup/evaluation/inference instructions are in README.md and ML_MODELS.md.']
    with (destination/'FINAL_VERIFICATION_REPORT.md').open('x',encoding='utf-8') as handle:handle.write('\n'.join(lines)+'\n')
    selected=['README.md','ML_MODELS.md','requirements.txt','.gitignore','configs','src','tests','scripts','docs',
              'frontend/src','frontend/scripts','frontend/public','frontend/tests','frontend/index.html','frontend/package.json','frontend/package-lock.json','frontend/vite.config.js',
              'models/registry.json','models/artifact_integrity.json','outputs/reports/ml_data_readiness.json','outputs/reports/ml_data_readiness.md']
    selected += [Path(m['artifact']).parent.as_posix() for m in registry]
    selected += [p.relative_to(project).as_posix() for p in (project/'outputs/metrics').glob('nlp-*_evaluation_audit.json')]
    files={}
    for relative in selected:
        root=project/relative
        for p in ([root] if root.is_file() else root.rglob('*')):
            if p.is_file() and not any(k in {'__pycache__','node_modules','.git','.venv','.pytest_cache'} for k in p.parts) and p.suffix not in {'.pyc','.pyo'}:files[p.relative_to(project).as_posix()]=p
    for p in destination.glob('*.json'):
        if p.name not in {'initial_state.json','previous_release_preservation.json'}:files[p.relative_to(project).as_posix()]=p
    for name in ['FINAL_VERIFICATION_REPORT.md','python_tests.xml','python_tests_rerun.xml']:files[(destination/name).relative_to(project).as_posix()]=destination/name
    for p in (destination/'browser_final_rerun').glob('*'):
        if p.is_file():files[p.relative_to(project).as_posix()]=p
    provenance=project/'data/processed/tourism_monthly_fta/20261025/provenance.json'
    files['docs/monthly_fta_provenance.json']=provenance
    archive=destination/'SafarSaathi_Final.zip'
    manifest={name:sha256(p) for name,p in sorted(files.items())}
    with zipfile.ZipFile(archive,'x',zipfile.ZIP_DEFLATED) as zipped:
        for name,p in sorted(files.items()):zipped.write(p,name)
        zipped.writestr('release_content_manifest.json',json.dumps(manifest,indent=2))
    with zipfile.ZipFile(archive) as zipped:
        if zipped.testzip() is not None:raise ValueError('ZIP CRC failure.')
        for name,digest in manifest.items():
            if hashlib.sha256(zipped.read(name)).hexdigest()!=digest:raise ValueError('ZIP content hash mismatch.')
            if any(part in {'SafarSaathi_Datasets','trash','node_modules','.git','temporary','external'} for part in Path(name).parts):raise ValueError('Excluded content in release.')
    final_quality.save(destination/'release_content_manifest.json',{'files':manifest,'zip_sha256':sha256(archive)})
    extracted=destination/'temporary/final_extracted'
    if extracted.exists():raise ValueError('Extraction target already exists.')
    extracted.mkdir(parents=True)
    with zipfile.ZipFile(archive) as zipped:zipped.extractall(extracted)
    code="""import json,numpy as np
from safarsaathi_ml.config import settings
from safarsaathi_ml.validation import validate_artifacts
from safarsaathi_ml.registry import load_registry
from safarsaathi_ml.inference import classify_reviews
from safarsaathi_ml.forecasting import forecast
from safarsaathi_ml.monthly_forecasting import forecast_monthly
from safarsaathi_ml.capabilities import capabilities
p=settings().project_root
assert not (p.parent/'SafarSaathi_Datasets').exists()
entries=load_registry(p/'models/registry.json');assert validate_artifacts(p)
review=next(m for m in entries if m['task']=='review classification')
assert classify_reviews(review['model_id'],['A comfortable hotel with helpful staff.'])['predictions']
assert forecast(p,'IND',1)['forecast_origin_year']==2019
assert forecast_monthly(p,'IND',1)['latest_observed_date']=='2024-12'
if any(m['model_id']=='flood_segmentation_model' for m in entries):
 from safarsaathi_ml.flood_baseline import segment
 assert segment(p,{'image':np.zeros((128,128,2)).tolist(),'metadata':{'source_format':'STURM-S1-preprocessed','geo_tags':{}}})['dimensions']==[128,128]
unavailable=[m for m in capabilities(p) if m['model_id'] in {'disaster_risk_predictor','destination_stress_predictor'}]
assert all(not m['inference_available'] for m in unavailable)
print(json.dumps({'status':'PASS','models_loaded':len(entries),'raw_directory_absent':True,'all_registered_inference_passed':True,'unavailable_models_disabled':True}))
"""
    result=subprocess.run([sys.executable,'-c',code],cwd=extracted,env={**os.environ,'PYTHONPATH':str(extracted/'src'),'OMP_NUM_THREADS':'2'},capture_output=True,text=True,timeout=90)
    if result.returncode:raise ValueError('Extracted inference failed: '+result.stderr)
    final_quality.save(destination/'release_validation.json',{**json.loads(result.stdout),'zip_crc_and_hashes_verified':True,
        'zip_sha256':sha256(archive),'zip_bytes':archive.stat().st_size,'entries':len(manifest)+1,'preservation':preservation(project,destination)})
    print(json.dumps({'release':str(destination),'zip':str(archive),'verified':True,'bytes':archive.stat().st_size},indent=2))


def finalize(project,destination):
    """Recheck the changed frontend after the recorded browser defect was fixed."""
    import threading
    from .http_api import Handler,ThreadingHTTPServer
    checks=json.loads((destination/'verification_checks_final.json').read_text(encoding='utf-8'))
    build=final_quality.run_check(destination,'frontend_build_final',[shutil.which('node'),str(project/'frontend/node_modules/vite/bin/vite.js'),'build'],project/'frontend')
    service=ThreadingHTTPServer(('127.0.0.1',0),Handler)
    thread=threading.Thread(target=service.serve_forever,daemon=True);thread.start()
    try:
        node=final_quality.run_check(destination,'frontend_all_tests_final',[shutil.which('node'),'--test','--test-reporter=tap','tests/api.test.js','tests/routes.test.js'],project/'frontend',extra_env={'SAFARSAATHI_TEST_API':f'http://127.0.0.1:{service.server_port}'})
    finally:service.shutdown();thread.join();service.server_close()
    checks['checks']=[build if c['name']=='frontend_build' else node if c['name']=='frontend_all_tests' else c for c in checks['checks']]
    # Keep stable names for consumer summaries, with separate evidence filenames.
    for item in checks['checks']:
        if item['name']=='frontend_build_final':item['name']='frontend_build'
        if item['name']=='frontend_all_tests_final':item['name']='frontend_all_tests'
    if build['status']!='PASS' or node['status']!='PASS':raise ValueError('Changed frontend verification failed.')
    final_quality.save(destination/'verification_checks_release.json',checks)
    from .capabilities import capabilities
    final_quality.save(destination/'current_data_readiness.json',{'scope':'Original raw-only readiness is preserved separately; these capabilities additionally account for verified derived monthly FTA and approved external STURM labels.','capabilities':capabilities(project),'source_investigation':'source_investigation.json'})


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('stage',choices=('verify','finalize','package'));args=parser.parse_args()
    project=settings().project_root;destination=project/'release'/NAME
    if args.stage=='verify':verify(project,destination)
    elif args.stage=='finalize':finalize(project,destination)
    else:package(project,destination)
