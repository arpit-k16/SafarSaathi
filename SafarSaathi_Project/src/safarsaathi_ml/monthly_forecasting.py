"""Separate Ministry FTA target. Does not replace or splice the preserved ITA model."""
from dataclasses import dataclass
from datetime import datetime, timezone
import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.linear_model import Ridge
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from .artifacts import load_artifact
from .forecasting import metrics
from .pipeline import sha256, utc_now
from .registry import load_registry, register_model

MODEL_ID = 'tourism_monthly_fta_forecaster'
METHODS = ('persistence', 'drift', 'historical_mean', 'seasonal_naive', 'ridge')
LIMITATIONS = ['Experimental India national Foreign Tourist Arrivals (FTA), excluding NRI arrivals; not the legacy World Bank ITA target.',
               'Latest observed month is December 2024. Forecasts are historical extrapolations, not current 2026 demand.',
               'Only 72 monthly observations and six annual cycles; COVID/recovery changes limit generalization.',
               'No calibrated intervals, destination-level accuracy or future weather features.',
               'Revised source vintages are used; publication-time vintages are unavailable.']


def validate_series(frame):
    if not {'destination', 'date', 'arrivals'}.issubset(frame): raise ValueError('Missing monthly source columns.')
    if frame.empty or not frame.destination.eq('IND').all() or frame[['date', 'arrivals']].isna().any().any():
        raise ValueError('Observed IND monthly arrival targets are required.')
    dates = pd.PeriodIndex(frame.date.astype(str), freq='M')
    values = pd.to_numeric(frame.arrivals, errors='raise').to_numpy(float)
    if dates.has_duplicates or not dates.equals(pd.period_range(dates[0], dates[-1], freq='M')):
        raise ValueError('Monthly observations must be unique, sorted and contiguous.')
    if not np.isfinite(values).all() or (values < 0).any() or (values % 1 != 0).any():
        raise ValueError('Finite non-negative count targets are required.')
    return dates, values


def monthly_features(history, first_month=1):
    y = np.asarray(history, dtype=float)
    if y.ndim != 1 or len(y) < 12 or not np.isfinite(y).all() or (y < 0).any():
        raise ValueError('Need at least 12 finite non-negative past months.')
    month = (first_month - 1 + len(y)) % 12
    return np.array([y[-1], y[-2], y[-12], y[-3:].mean(), np.sin(2*np.pi*month/12), np.cos(2*np.pi*month/12)])


@dataclass
class MonthlyForecaster:
    method: str
    first_month: int = 1
    estimator: object = None
    drift: float = 0.0
    mean: float = 0.0

    def fit(self, history):
        y = np.asarray(history, dtype=float)
        monthly_features(y, self.first_month)
        if len(y) < 24 or self.method not in METHODS: raise ValueError('Need 24 months and a supported method.')
        self.drift, self.mean = float(np.diff(y).mean()), float(y.mean())
        if self.method == 'ridge':
            self.estimator = make_pipeline(StandardScaler(), Ridge(alpha=10))
            self.estimator.fit(np.stack([monthly_features(y[:i], self.first_month) for i in range(12,len(y))]), y[12:])
        return self

    def forecast(self, history, horizon):
        if type(horizon) is not int or not 1 <= horizon <= 6: raise ValueError('Monthly horizon must be an integer from 1 to 6.')
        y = list(np.asarray(history, dtype=float)); monthly_features(y, self.first_month)
        result = []
        for _ in range(horizon):
            if self.method == 'persistence': value = y[-1]
            elif self.method == 'drift': value = y[-1] + self.drift
            elif self.method == 'historical_mean': value = self.mean
            elif self.method == 'seasonal_naive': value = y[-12]
            elif self.method == 'ridge': value = float(self.estimator.predict(monthly_features(y, self.first_month).reshape(1,-1))[0])
            else: raise ValueError('Unsupported monthly model method.')
            value = max(0.0, float(value))
            if not np.isfinite(value): raise ValueError('Model produced an invalid forecast.')
            y.append(value); result.append(value)
        return result


def evaluate_method(method, values, dates, start, stop, scale):
    rows = []
    for origin in range(start, stop):
        model = MonthlyForecaster(method, dates[0].month).fit(values[:origin])
        prediction = model.forecast(values[:origin], min(6, stop-origin))
        for h in (1,3,6):
            if h <= len(prediction): rows.append({'origin': str(dates[origin-1]), 'target': str(dates[origin+h-1]), 'horizon': h,
                                                  'actual': float(values[origin+h-1]), 'prediction': prediction[h-1]})
    result = {}
    for h in (1,3,6):
        selected = [r for r in rows if r['horizon']==h]
        result[str(h)] = {**metrics([r['actual'] for r in selected],[r['prediction'] for r in selected],scale),
                          'origins': [r['origin'] for r in selected], 'targets': [r['target'] for r in selected]}
    return result


def train_monthly(project, derived):
    registry = project / 'models/registry.json'
    if any(m['model_id']==MODEL_ID for m in load_registry(registry)): raise ValueError('Monthly model already registered; no overwrite.')
    source = derived / 'monthly_fta.csv'; provenance = json.loads((derived/'provenance.json').read_text(encoding='utf-8'))
    if sha256(source) != provenance['derived_csv_sha256']: raise ValueError('Derived source checksum mismatch.')
    dates, values = validate_series(pd.read_csv(source))
    if len(values) != 72 or str(dates[0]) != '2019-01' or str(dates[-1]) != '2024-12':
        raise ValueError('This explicit experiment requires the audited 2019–2024 source window.')
    # Initial 2019–2021, select only on 2022. Independently report two later test-year blocks.
    scale = float(np.abs(values[12:36]-values[:24]).mean())
    validation = {m:evaluate_method(m,values,dates,36,48,scale) for m in METHODS}
    selected = min(METHODS, key=lambda m: np.mean([validation[m][str(h)]['MAE'] for h in (1,3,6)]))
    test = {m:evaluate_method(m,values,dates,48,72,scale) for m in METHODS}
    folds = {str(year): {m:evaluate_method(m,values,dates,start,start+12,scale) for m in METHODS}
             for year,start in ((2023,48),(2024,60))}
    for m in METHODS:
        for h in ('1','3','6'):
            baseline = test['persistence'][h]
            test[m][h]['differences_vs_persistence'] = {k: {'absolute': test[m][h][k]-baseline[k],
                'relative': (test[m][h][k]-baseline[k])/baseline[k] if baseline[k] else None} for k in ('MAE','RMSE','MASE','WAPE')}
    model = MonthlyForecaster(selected, dates[0].month).fit(values)
    version = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    folder = project/'models/tourism_monthly_fta'/version;folder.mkdir(parents=True,exist_ok=False)
    artifact = folder/'pipeline.joblib'
    bundle = {'model':model,'values':values.tolist(),'dates':[str(d) for d in dates],'scale':scale,'selected_method':selected}
    joblib.dump(bundle,artifact)
    loaded=joblib.load(artifact)
    if loaded['model'].forecast(values,6)!=model.forecast(values,6):raise ValueError('Monthly artifact reload mismatch.')
    report={'validation':validation,'test':test,'test_year_folds':folds,'selected_method':selected,
            'selection':'Lowest mean validation MAE across horizons 1,3,6 on 2022 only; no test-set selection.',
            'MASE_denominator':scale,'MASE_definition':'Mean absolute seasonal (lag-12) differences in initial 2019–2021 block, identical across all methods/horizons.',
            'legacy_comparison':'Old ITA artifact remains unchanged; its target differs, so direct FTA-vs-ITA error rankings are invalid.'}
    metadata={'model_id':MODEL_ID,'model_version':version,'task':'monthly foreign tourist arrivals forecasting','task_type':'time_series_regression',
              'artifact':artifact.relative_to(project).as_posix(),'artifact_sha256':sha256(artifact),'persistence_test_passed':True,
              'trained_at':utc_now(),'training_completed':True,'quality_status':'TRAINED_BUT_EXPERIMENTAL',
              'target_definition':provenance['target'],'dataset_provenance':provenance,'derived_source':source.relative_to(project).as_posix(),
              'latest_observed_date':str(dates[-1]),'units':'foreign tourist arrivals/month','method':selected,'metrics':report,
              'split':{'initial_train':'2019-01 through 2021-12','validation':'2022-01 through 2022-12','test':'2023-01 through 2024-12',
                       'policy':'Expanding-prefix refit before each origin. Final inference estimator fit through 2024-12.'},
              'feature_schema':{'destination':'IND only','horizon':'integer 1..6 months','derived_features':['lag1','lag2','lag12','past3mean','calendar_sin','calendar_cos']},
              'configuration':{'seed':20261025,'ridge_alpha':10,'CPU':True,'expected_memory':'<50 MB incremental','no_downloads_or_weights':True},
              'limitations':LIMITATIONS}
    for name,content in [('metadata.json',metadata),('evaluation.json',report),('feature_schema.json',metadata['feature_schema'])]:
        (folder/name).write_text(json.dumps(content,indent=2,allow_nan=False),encoding='utf-8')
    register_model(registry,metadata)
    return metadata


def load_monthly(project):
    entry=next((m for m in load_registry(project/'models/registry.json') if m['model_id']==MODEL_ID),None)
    if entry is None:raise ValueError('Monthly FTA model is unavailable.')
    bundle=load_artifact(project,entry)
    if not isinstance(bundle.get('model'),MonthlyForecaster):raise ValueError('Invalid monthly artifact.')
    bundle['model'].forecast(bundle['values'],1)
    return entry,bundle


def forecast_monthly(project,destination,horizon):
    if destination!='IND' or type(horizon) is not int or not 1<=horizon<=6:raise ValueError('Expected destination=IND and integer monthly horizon=1..6.')
    entry,bundle=load_monthly(project);last=pd.Period(bundle['dates'][-1],freq='M')
    predictions=bundle['model'].forecast(bundle['values'],horizon)
    return {'model_id':MODEL_ID,'model_version':entry['model_version'],'destination':'IND','status':'historical_experimental_forecast',
            'quality_status':'TRAINED_BUT_EXPERIMENTAL','latest_observed_date':str(last),'forecast_origin':str(last),'horizon':horizon,
            'units':entry['units'],'is_forecast':True,'target_definition':entry['target_definition'],
            'forecasts':[{'date':str(last+h),'horizon':h,'prediction':p} for h,p in enumerate(predictions,1)],'limitations':LIMITATIONS}


def evaluate_monthly(project):
    entry,bundle=load_monthly(project);dates=pd.PeriodIndex(bundle['dates'],freq='M');values=np.asarray(bundle['values'])
    replay=evaluate_method(entry['method'],values,dates,48,72,bundle['scale'])
    expected=entry['metrics']['test'][entry['method']]
    for h in ('1','3','6'):
        for key in ('MAE','RMSE','MASE','WAPE','n'):
            if replay[h][key]!=expected[h][key]:raise ValueError('Monthly evaluation replay mismatch.')
    return {'model_id':MODEL_ID,'artifact_valid':True,'evaluation_reproduced':True,'metrics':replay}
