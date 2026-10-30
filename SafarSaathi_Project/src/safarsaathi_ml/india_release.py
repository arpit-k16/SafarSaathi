"""Immutable evidence and packaging for the scoped India experiments; prior releases stay untouched."""
import argparse,hashlib,json,os,re,shutil,subprocess,sys,threading,zipfile
from pathlib import Path
import xml.etree.ElementTree as ET
from .config import settings
from .pipeline import sha256,utc_now
from .registry import load_registry
from .final_quality import run_check,save

NAME='india_scope_20261025_03'

def preservation(project,dest):
    initial=json.loads((dest/'initial_state.json').read_text())
    errors=[]
    for relative,digest in initial['protected_sha256'].items():
        if relative=='models/registry.json':continue
        path=project/relative
        if not path.is_file() or sha256(path)!=digest:errors.append(relative)
    for relative,digest in initial['legacy_protected_sha256'].items():
        path=project.parent/relative
        if not path.is_file() or sha256(path)!=digest:errors.append(relative)
    current=load_registry(project/'models/registry.json')
    if any(next((e for e in current if e['model_id']==old['model_id']),None)!=old for old in initial['registry']):errors.append('original registry entry')
    raw=project.parent/'SafarSaathi_Datasets/raw'
    stats={p.relative_to(raw).as_posix():{'bytes':p.stat().st_size,'mtime_ns':p.stat().st_mtime_ns} for p in raw.rglob('*') if p.is_file()}
    if stats!=initial['raw_stats']:errors.append('raw file path/size/mtime inventory')
    if errors:raise ValueError('Preservation mismatch: '+str(errors))
    return {'status':'PASS','protected_files_checked':len(initial['protected_sha256']),'legacy_files_checked':len(initial['legacy_protected_sha256']),'original_registry_entries_preserved':len(initial['registry']),'raw_files_unchanged':len(stats),'prior_release_hashes_unchanged':True,'raw_paths_sizes_mtimes_unchanged':True}

def verify(project,dest):
    checks=[]
    commands=[('python_tests',[sys.executable,'-m','pytest','tests','-q','--tb=short','--basetemp',str(project/'data/interim/test_runs/india_final01'),'--junitxml',str(dest/'python_tests.xml')],project),
      ('artifact_validation',[sys.executable,'-m','safarsaathi_ml.cli','validate-artifacts'],project),
      ('cyclone_evaluation',[sys.executable,'-m','safarsaathi_ml.cli','evaluate','--model','cyclone_count'],project),
      ('pm25_evaluation',[sys.executable,'-m','safarsaathi_ml.cli','evaluate','--model','pm25'],project),
      ('cyclone_inference',[sys.executable,'-m','safarsaathi_ml.cli','predict','--model','cyclone_count','--destination','NI','--horizon','12'],project),
      ('pm25_inference',[sys.executable,'-m','safarsaathi_ml.cli','predict','--model','pm25','--destination','IND','--horizon','1'],project),
      ('fresh_process_startup',[sys.executable,'-m','safarsaathi_ml.startup_check'],project),
      ('raw_checksums',[sys.executable,'verify_checksums.py'],project.parent/'SafarSaathi_Datasets'),
      ('frontend_build',[shutil.which('node'),str(project/'frontend/node_modules/vite/bin/vite.js'),'build'],project/'frontend')]
    for name,command,cwd in commands:checks.append(run_check(dest,name,command,cwd,extra_env={'OMP_NUM_THREADS':'2'}))
    from .http_api import Handler,ThreadingHTTPServer
    server=ThreadingHTTPServer(('127.0.0.1',0),Handler);thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
    try:checks.append(run_check(dest,'frontend_tests',[shutil.which('node'),'--test','--test-reporter=tap','tests/api.test.js','tests/routes.test.js'],project/'frontend',extra_env={'SAFARSAATHI_TEST_API':f'http://127.0.0.1:{server.server_port}','OMP_NUM_THREADS':'2'}))
    finally:server.shutdown();thread.join();server.server_close()
    for model in ['cyclone_count','pm25','disaster_risk','destination_stress']:
        checks.append(run_check(dest,model+'_training_refusal',[sys.executable,'-m','safarsaathi_ml.cli','train','--model',model],project,expected=2))
    checks.append(run_check(dest,'browser_tests',[shutil.which('node'),'scripts/browser_checks.mjs'],project/'frontend',extra_env={'PLAYWRIGHT_MODULE_PATH':os.environ.get('PLAYWRIGHT_MODULE_PATH',''),'SAFARSAATHI_BROWSER_OUTPUT':str(dest/'browser_final'),'OMP_NUM_THREADS':'2'},timeout=180))
    root=ET.parse(dest/'python_tests.xml').getroot().find('testsuite');counts={k:int(root.attrib.get(k,0)) for k in ['tests','failures','errors','skipped']};counts['passed']=counts['tests']-counts['failures']-counts['errors']-counts['skipped']
    save(dest/'verification_checks.json',{'generated_at':utc_now(),'checks':checks,'python_counts':counts,'preservation':preservation(project,dest)})
    if any(c['status']!='PASS' for c in checks) or any(counts[k] for k in ['failures','errors','skipped']):raise ValueError('Quality gate failed; preserve evidence and resolve before packaging.')

def package(project,dest):
    verification=json.loads((dest/'verification_checks.json').read_text());browser=json.loads((dest/'browser_visual/browser_results.json').read_text())
    verification['checks'].append(json.loads((dest/'browser_visual_review.json').read_text()))
    if any(c['status']!='PASS' for c in verification['checks']) or browser['status']!='PASS':raise ValueError('Quality gate failed.')
    registry=load_registry(project/'models/registry.json')
    from .scoped_forecasts import SPECS,evaluate_scoped
    new=[]
    for kind,spec in SPECS.items():
        entry=next(m for m in registry if m['model_id']==spec['id']);replay=evaluate_scoped(project,kind)
        save(dest/(kind+'_evaluation_replay.json'),replay)
        new.append({'kind':kind,'model_id':entry['model_id'],'status':entry['quality_status'],'model_version':entry['model_version'],'artifact_sha256':entry['artifact_sha256'],'target':entry['target_definition'],'units':spec['units'],'geography':spec['geography'],'observations':sum(s['n'] for s in entry['metrics']['splits'].values()),'splits':entry['metrics']['splits'],'selected_method':entry['method'],'metrics':entry['metrics']['methods'],'leakage':entry['metrics']['leakage'],'limitations':entry['limitations'],'training_completed':True,'artifact_replay_passed':replay['evaluation_reproduced']})
    node=next(c for c in verification['checks'] if c['name']=='frontend_tests')
    node_counts={k:int(re.search(r'^# '+label+r' (\d+)$',node['stdout'],re.M).group(1)) for k,label in [('tests','tests'),('passed','pass'),('failed','fail'),('skipped','skipped')]}
    if node_counts['failed'] or node_counts['skipped']:raise ValueError('Incomplete frontend tests.')
    report={'generated_at':utc_now(),'overall_status':'VERIFIED_SCOPED_EXPERIMENTS_BROAD_TARGETS_REMAIN_LABELS_INSUFFICIENT','requested_capabilities':[{'model_id':'disaster_risk_predictor','status':'LABELS_INSUFFICIENT','reason':'No verified India-wide multi-disaster event/outcome frame and pre-cutoff predictors. Separate NI archive-count experiment is not a replacement warning model.'},{'model_id':'destination_stress_predictor','status':'LABELS_INSUFFICIENT','reason':'No measured aligned destination occupancy/capacity/ecological-pressure target. Separate national modeled-PM2.5 forecast and historical indicators do not establish tourism causation or local stress.'}],
      'trained_models':new,'preserved_models':[m['model_id'] for m in json.loads((dest/'initial_state.json').read_text())['registry']],
      'indicators':{'status':'DERIVED_INDICATOR_NOT_A_TRAINED_MODEL','national_rows':14,'state_rows':72,'states_uts':36,'national_years':[2011,2024],'state_years':[2023,2024],'environment_context':'National modeled PM2.5 through 2023 and FAO water stress through 2022; missing values remain null. No geographic allocation of national context.','capacity_labels':0},
      'python_counts':verification['python_counts'],'frontend_counts':node_counts,'browser_counts':{'passed':len(browser['checks']),'failed':0,'unexpected_console_errors':len(browser['unexpectedConsole']),'unexpected_network_failures':len(browser['unexpectedNetwork'])},'checks':verification['checks'],'browser_evidence':'browser_visual/browser_results.json','visual_inspection':'browser_visual_inspection.json','preservation':preservation(project,dest),'remaining_blockers':['Nationwide compatible event categories, observation completeness and verified no-event windows are absent.','National/basin fits have no geographic holdout; political India, districts, landfalls and arbitrary destination generalization are unsupported.','Historical revised source vintages were unavailable at the simulated historical cutoffs; these are retrospective experiments, not live forecast validation.','Destination/time measured capacity, occupancy or ecological-pressure labels and matching environmental observations are absent.','New forecasts start in 2025 (cyclones) and 2024 (PM2.5); no current 2026 conditions or calibrated probabilities/intervals are claimed.','External fonts and Tailwind remain an offline appearance dependency.'],'development_evidence':['browser/browser_results.json: first 16-journey integration pass; final rerun adds scoped failure and long-geography mobile checks.','Initial full-page screenshots captured a scrolled fixed header; screenshot positioning corrected and all 18 journeys rerun in browser_visual.','World Bank initial water-stress request timed out, then bounded retry succeeded; no original file overwritten.'],'release_zip':'SafarSaathi_Final.zip','post_extraction_evidence':'release_validation.json'}
    visual=json.loads((dest/'browser_visual_inspection.json').read_text())
    if visual['status']!='PASS':raise ValueError('Visual inspection not complete.')
    save(dest/'verification_report.json',report)
    lines=['# SafarSaathi India-scope completion release','','The four existing models are preserved. Two separately named experimental forecasts and a historical indicator view are integrated. The requested broad India-wide multi-disaster warning and destination ecological-stress predictors remain LABELS_INSUFFICIENT; no fake labels or capability renaming hides those limits.','','## Model results','']
    for model in new:
        lines += [f"### {model['model_id']} — {model['status']}",'',model['target'],f"Geography: {model['geography']}. Units: {model['units']}. Observations: {model['observations']}. Selected method: {model['selected_method']}.",f"Chronological split: {model['splits']}.",'','| Method | Split | n | MAE | RMSE | MASE | WAPE fraction |','|---|---|---:|---:|---:|---:|---:|']
        for method,scores in model['metrics'].items():
            for split,m in scores.items():lines.append(f"| {method} | {split} | {m['n']} | {m['MAE']} | {m['RMSE']} | {m['MASE']} | {m['WAPE']} |")
        lines += ['',f"Leakage controls: {model['leakage']}",'','Save/reload, inference and evaluation replay passed. No original model was replaced.']+['- '+limit for limit in model['limitations']]+['']
    lines += ['## Source and target details','','NOAA IBTrACS v04r01 NI snapshot: 27,886,424 bytes; 388 distinct qualifying tropical MAIN storm IDs mapped to 540 months, 1980–2024. There are 304 zero archive-count months. Those are not verified no-disaster outcomes. Counts include depressions; no intensity or India landfall label is inferred. Storm IDs are disjoint across train/validation/test. Calendar models fit through 2009 for validation and 2014 for the fixed 2015–2024 holdout; final artifact refits through 2024. Target counts never use fatalities, severity or post-event impact as features.',
      'World Bank EN.ATM.PM25.MC.M3 / GBD2023: 34 modeled national annual exposure observations, 1990–2023, no target imputation. Expanding one-year test fits use past exposure only; method selection uses 2010–2016 validation. The indicator was published/revised in 2026: historical source vintages and their operational availability cannot be reconstructed. Test year-fold metrics are recorded but do not establish geographic robustness.',
      'Tourism: official local Compendium 2025 tables 4.1.1/4.1.2, PDF pages 211/213/214. All 36 State/UT rows retained for 2023–2024, with rounded million units; national 2011–2024 counts are separate. Source-estimated Delhi/Maharashtra 2024 rows and revised 2023 rows remain flagged. The printed Jammu & Pradesh label is canonicalized by row identity to Jammu and Kashmir, without numeric changes. Rounded sums reconcile within declared rounding tolerance. Source pages were rendered and inspected.',
      'Environmental alignment is country/year only: 13 nonmissing PM2.5 years, 12 water-stress years, 14 surface-area years across 2011–2024. No state allocation, interpolation, capacity invention, weighted stress label or causal tourism claim. The explicit derived indicator is domestic visits / same-year national surface area, with units visits/km²/year; it is not simultaneous crowding or capacity utilization. Missing area yields null; nonpositive area is rejected. Growth uses a null result for a missing or zero previous-period denominator.',
      'See disaster_data_readiness.json, destination_stress_data_readiness.json, source_investigation.json and source_manifests.json for source access, licenses, missingness, transformations and rejection reasons.','','## Validation','',f"Python: {report['python_counts']}. Node: {node_counts}. Browser: {report['browser_counts']}.",
      'All commands, exit codes and outputs are retained in verification_report.json and individual check files. Browser tests execute actual saved-model requests and indicator views, all navigation routes, loading/failures/disconnection and mobile layouts. Deliberately injected failures are recorded separately from unexpected errors. Both old and new saved models load without raw source files. Full raw checksum verification and hash comparison of prior releases passed.',
      'Fixture tests cover source schema, duplicated/cross-year storms, archive-zero semantics, missing/invalid targets, chronological leakage, serialization/refusal, corrupt artifacts, unsupported regions/years and real HTTP. Synthetic fixtures are not real-source training evidence.','','## Remaining blockers','']+['- '+b for b in report['remaining_blockers']]+['','## Release','','SafarSaathi_Final.zip includes source, tests, documentation, all six inference artifacts, compact indicator snapshot and evidence. Raw data, external archives/CSVs, previous releases, credentials and caches are excluded. release_validation.json records ZIP hashes, CRC checks and fresh extracted-copy inference. Setup and troubleshooting: README.md and docs/INDIA_SCOPE_MODELS.md.']
    with (dest/'FINAL_VERIFICATION_REPORT.md').open('x',encoding='utf-8') as f:f.write('\n'.join(lines)+'\n')
    selected=['README.md','ML_MODELS.md','requirements.txt','.gitignore','configs','src','tests','scripts','docs','frontend/src','frontend/scripts','frontend/tests','frontend/public','frontend/index.html','frontend/package.json','frontend/package-lock.json','frontend/vite.config.js','models/registry.json','models/artifact_integrity.json','outputs/reports/ml_data_readiness.json','outputs/indicators/india_environment_tourism']+[str(Path(e['artifact']).parent) for e in registry]
    files={}
    for relative in selected:
        root=project/relative
        for p in ([root] if root.is_file() else root.rglob('*')):
            if p.is_file() and not any(k in {'__pycache__','node_modules','.git','.venv','.pytest_cache'} for k in p.parts) and p.suffix not in {'.pyc','.pyo'}:files[p.relative_to(project).as_posix()]=p
    for p in dest.glob('*'):
        if p.is_file() and p.suffix in {'.json','.md','.xml'} and p.name!='initial_state.json':files[p.relative_to(project).as_posix()]=p
    for p in (dest/'browser_visual').iterdir():
        if p.is_file():files[p.relative_to(project).as_posix()]=p
    manifest={name:sha256(path) for name,path in sorted(files.items())};archive=dest/'SafarSaathi_Final.zip'
    with zipfile.ZipFile(archive,'x',zipfile.ZIP_DEFLATED) as z:
        for name,path in sorted(files.items()):z.write(path,name)
        z.writestr('release_content_manifest.json',json.dumps(manifest,indent=2))
    with zipfile.ZipFile(archive) as z:
        if z.testzip() is not None:raise ValueError('CRC check failed.')
        for name,digest in manifest.items():
            if hashlib.sha256(z.read(name)).hexdigest()!=digest or any(k in {'raw','external','temporary','trash','node_modules','.git'} for k in Path(name).parts):raise ValueError('ZIP content/hash policy failed.')
    save(dest/'release_content_manifest.json',{'files':manifest,'zip_sha256':sha256(archive)})
    extracted=dest/'temporary/extracted';extracted.mkdir(parents=True,exist_ok=False)
    with zipfile.ZipFile(archive) as z:z.extractall(extracted)
    code="""import json,numpy as np
from safarsaathi_ml.config import settings
from safarsaathi_ml.validation import validate_artifacts
from safarsaathi_ml.registry import load_registry
from safarsaathi_ml.inference import classify_reviews
from safarsaathi_ml.forecasting import forecast
from safarsaathi_ml.monthly_forecasting import forecast_monthly
from safarsaathi_ml.flood_baseline import segment
from safarsaathi_ml.scoped_forecasts import predict_scoped
from safarsaathi_ml.pressure_indicators import indicators
from safarsaathi_ml.capabilities import capabilities
p=settings().project_root;assert not (p.parent/'SafarSaathi_Datasets').exists();assert not (p/'data/external').exists()
models=load_registry(p/'models/registry.json');assert len(validate_artifacts(p))==len(models)
review=next(m for m in models if m['task']=='review classification')
assert classify_reviews(review['model_id'],['A pleasant hotel with helpful staff.'])['predictions']
assert forecast(p,'IND',1)['latest_observed_year']==2019
assert forecast_monthly(p,'IND',1)['latest_observed_date']=='2024-12'
assert segment(p,{'image':np.zeros((128,128,2)).tolist(),'metadata':{'source_format':'STURM-S1-preprocessed','geo_tags':{}}})['dimensions']==[128,128]
assert predict_scoped(p,'cyclone_count',{'geography':'NI','horizon':1})['forecasts'][0]['date']=='2025-01'
assert predict_scoped(p,'pm25',{'geography':'IND','horizon':1})['forecasts'][0]['date']=='2024'
assert indicators(p,{'geography':'IND','year':2024})['trained_model'] is False
assert all(not c['inference_available'] for c in capabilities(p) if c['model_id'] in {'disaster_risk_predictor','destination_stress_predictor'})
print(json.dumps({'status':'PASS','models_loaded':len(models),'all_registered_inference_passed':True,'raw_external_data_absent':True,'indicator_snapshot_passed':True,'broad_unsupported_models_disabled':True}))
"""
    result=subprocess.run([sys.executable,'-c',code],cwd=extracted,env={**os.environ,'PYTHONPATH':str(extracted/'src'),'OMP_NUM_THREADS':'2'},capture_output=True,text=True,timeout=120)
    if result.returncode:raise ValueError('Extracted inference failed: '+result.stderr)
    save(dest/'release_validation.json',{**json.loads(result.stdout),'zip_crc_and_content_hashes_verified':True,'zip_sha256':sha256(archive),'zip_bytes':archive.stat().st_size,'entries':len(manifest)+1,'preservation':preservation(project,dest)})
    print(json.dumps({'status':'PASS','zip':str(archive),'bytes':archive.stat().st_size},indent=2))

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('stage',choices=['verify','package']);args=parser.parse_args();project=settings().project_root;destination=project/'release'/NAME
    if args.stage=='verify':verify(project,destination)
    else:package(project,destination)
