"""Runtime capabilities based only on saved readiness and validated artifacts."""
import json
from pathlib import Path

from .forecasting import load_forecast
from .readiness import IDS


def _released(project, model_id, default):
    try:
        from .release_gate import status_for
        return status_for(project, model_id, default)
    except Exception:
        return default


def capabilities(project: Path) -> list[dict]:
    report = project / 'outputs/reports/ml_data_readiness.json'
    readiness = json.loads(report.read_text(encoding='utf-8')).get('models', {}) if report.exists() else {}
    result = []
    for task, model_id in IDS.items():
        item = readiness.get(task, {})
        if task == 'flood_segmentation':
            try:
                from .flood_baseline import load_flood
                flood, _ = load_flood(project)
                result.append({'model_id':model_id,'name':'Flood-scene water segmentation','task':flood['task'],
                    'dataset_readiness':'READY_FOR_TRAINING','implementation_status':_released(project,model_id,flood['quality_status']),
                    'status':'FINAL_V1' if _released(project,model_id,'')=='FINAL_V1' else 'EXPERIMENTAL',
                    'implementation_scope':'Trained CPU pixel-segmentation benchmark baseline with country/event holdout.',
                    'training_completed':True,'evaluation_status':'Held-out country/event evaluation executed',
                    'inference_available':True,'reason':'Publisher-labelled STURM subset validated; temporary flood vs permanent water is not independently separated.',
                    'metrics':flood['metrics']['test'],'model_version':flood['model_version'],
                    'supported_input':'128x128x2 delivered STURM-preprocessed Sentinel-1 array plus metadata; JSON <=1 MB',
                    'supported_output':'128x128 reference-positive mask and uncalibrated confidence map','limitations':flood['limitations']})
                continue
            except Exception:
                pass
        active, metrics = False, None
        reason = item.get('reason', 'Data readiness has not been checked on this installation.')
        if task == 'tourism_demand':
            try:
                metadata, _ = load_forecast(project)
                active, metrics = True, metadata['metrics']['by_horizon']['1']
            except Exception:
                reason = 'No validated tourism artifact is available. Run data-readiness and explicit training/validation.'
        result.append({'model_id': model_id, 'name': task.replace('_', ' ').title(),
                       'task': item.get('task', task), 'dataset_readiness': item.get('readiness', 'UNAVAILABLE'),
                       'implementation_status': _released(project, model_id, 'TRAINED_BUT_EXPERIMENTAL') if active else ('IMPLEMENTED_BUT_NOT_TRAINED' if task == 'tourism_demand' else 'LABELS_INSUFFICIENT'),
                       'status': ('FINAL_V1' if _released(project, model_id, '') == 'FINAL_V1' else 'EXPERIMENTAL') if active else ('UNAVAILABLE' if task == 'tourism_demand' else 'DATA_INSUFFICIENT'),
                       'implementation_scope': 'Forecast training/evaluation/inference pipeline' if task == 'tourism_demand' else 'Readiness and schema validation; supervised learner unavailable pending observed labels',
                       'training_completed': active, 'evaluation_status': 'small historical holdout; experimental' if active else 'not evaluated',
                       'inference_available': active, 'reason': reason, 'metrics': metrics,
                       'supported_input': f"destination=IND; horizon=1..3 annual periods from {metadata['latest_observed_year']}" if active else 'No supported inference input',
                       'latest_observed_year': metadata['latest_observed_year'] if active else None,
                       'model_version': metadata['model_version'] if active else None,
                       'units': 'international tourist arrivals/year' if active else None,
                       'supported_output': 'historical forecast annual arrivals' if task == 'tourism_demand' else 'unavailable status only',
                       'limitations': metadata['limitations'] if active else [reason]})
        if task == 'tourism_demand':
            from .monthly_forecasting import load_monthly
            try:
                monthly, _ = load_monthly(project)
                result[-1]['monthly_fta'] = {'inference_available':True,'model_id':monthly['model_id'],'model_version':monthly['model_version'],
                    'latest_observed_date':monthly['latest_observed_date'],'units':monthly['units'],'metrics':monthly['metrics']['test'][monthly['method']],
                    'quality_status':_released(project,monthly['model_id'],monthly['quality_status']),'status':'FINAL_V1' if _released(project,monthly['model_id'],'')=='FINAL_V1' else 'EXPERIMENTAL','limitations':monthly['limitations']}
            except Exception:
                result[-1]['monthly_fta'] = {'inference_available':False,'reason':'No validated monthly FTA model is available.'}
    from .scoped_forecasts import load_scoped,SPECS
    for kind,parent in [('cyclone_count','disaster_risk_predictor'),('pm25','destination_stress_predictor')]:
        item=next(r for r in result if r['model_id']==parent)
        try:
            entry,_=load_scoped(project,kind);spec=SPECS[kind]
            item['scoped_forecast']={'model_id':entry['model_id'],'model_version':entry['model_version'],'status':'FINAL_V1' if _released(project,entry['model_id'],'')=='FINAL_V1' else 'EXPERIMENTAL','inference_available':True,'geography':spec['geography'],'target':spec['target'],'units':spec['units'],'horizon_max':spec['max_horizon'],'latest_observed_date':entry['latest_observed_date'],'metrics':entry['metrics']['methods'][entry['method']]['test'],'limitations':spec['limitations']}
        except Exception:item['scoped_forecast']={'inference_available':False}
    try:
        from .pressure_indicators import load_indicators
        data=load_indicators(project)
        next(r for r in result if r['model_id']=='destination_stress_predictor')['historical_indicators']={'available':True,'status':'INDICATOR_ONLY','geographies':len(data['geographies']),'observations':len(data['records']),'limitations':data['limitations']}
    except Exception:pass
    for r in result:  # what answers each capability today (report §9.10 MVP choices); learned predictors stay untrained
        if r['model_id'] in SERVED_AS:
            r['served_as'] = SERVED_AS[r['model_id']]
    return result


SERVED_AS = {
    'destination_stress_predictor': {
        'status': 'INDEX_V1', 'label': 'Index v1.0', 'page': 'twin', 'how': 'Destination Stress Index',
        'method': 'Transparent weighted index (report §9.2 and §9.10 MVP choice)',
        'reason': 'Served as the transparent Destination Stress Index on the Digital twin page: 28 destinations, UTDB visitors and NASA POWER climate, ranking robust to re-weighting (Spearman ρ ≈ 0.98).',
        'learned_model': 'A learned stress predictor still needs observed crowding, occupancy or capacity labels.'},
    'disaster_risk_predictor': {
        'status': 'RULES_V1', 'label': 'Rule-based v1.0', 'page': 'routing', 'how': 'risk rules and scenarios',
        'method': 'Rules and scenario-based risk model (report §9.10 MVP choice)',
        'reason': 'Served as rule- and scenario-based hazard exposure: risk-aware routing with simulated closures, rainfall and visitor anomaly detection (checked against 2013 and COVID), and the scoped cyclone-count forecaster.',
        'learned_model': 'A learned disaster predictor still needs dated event, impact and verified non-event labels.'},
}
