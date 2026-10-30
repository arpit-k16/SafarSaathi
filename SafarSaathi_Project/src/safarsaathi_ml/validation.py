"""Explicit read-only registry reload checks, separate from training."""
from .artifacts import load_artifact
from .forecasting import evaluate_forecast
from .registry import load_registry, resolve_artifact_path


def validate_artifacts(project):
    results = []
    for entry in load_registry(project / 'models/registry.json'):
        if entry['task'] == 'review classification':
            model = load_artifact(project, entry)
            prediction = model.predict(['A comfortable hotel with helpful staff.']).tolist()
            if len(prediction) != 1 or not set(model.classes_).issubset({'NEGATIVE', 'POSITIVE'}):
                raise ValueError('Review artifact failed prediction validation.')
            results.append({'model_id': entry['model_id'], 'reload_valid': True, 'classes': model.classes_.tolist()})
        elif entry['model_id'] == 'tourism_demand_forecaster':
            results.append(evaluate_forecast(project))
        elif entry['model_id'] == 'tourism_monthly_fta_forecaster':
            from .monthly_forecasting import evaluate_monthly
            results.append(evaluate_monthly(project))
        elif entry['model_id'] == 'flood_segmentation_model':
            from .flood_baseline import segment
            import numpy as np
            result=segment(project,{'image':np.zeros((128,128,2)).tolist(),'metadata':{'source_format':'STURM-S1-preprocessed','geo_tags':{}}})
            if result['dimensions']!=[128,128]:raise ValueError('Flood output dimensions invalid.')
            results.append({'model_id':entry['model_id'],'reload_valid':True,'mask_shape':[128,128]})
        elif entry['model_id'] in {'north_indian_cyclone_count_forecaster','india_pm25_exposure_forecaster'}:
            from .scoped_forecasts import evaluate_scoped,predict_scoped,SPECS
            kind=next(k for k,v in SPECS.items() if v['id']==entry['model_id'])
            results.append(evaluate_scoped(project,kind))
            predict_scoped(project,kind,{'geography':SPECS[kind]['geography'],'horizon':1})
        else:
            raise ValueError('No task-specific validator exists for registered model.')
    return results
