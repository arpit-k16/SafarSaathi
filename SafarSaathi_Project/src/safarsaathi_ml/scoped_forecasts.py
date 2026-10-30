"""Two explicitly narrow archive/indicator forecasting experiments, never nationwide warnings."""
import json,platform
from datetime import datetime,timezone
from pathlib import Path
import joblib,numpy as np,pandas as pd,sklearn
from sklearn.linear_model import PoissonRegressor
from .artifacts import load_artifact
from .forecasting import AnnualForecaster,metrics
from .india_data import DERIVED,validate_series
from .pipeline import sha256,utc_now
from .registry import load_registry,register_model

SPECS={
 'cyclone_count':{'id':'north_indian_cyclone_count_forecaster','file':'cyclone_monthly.csv','frequency':'monthly','period':12,'train_end':'2009-12','validation_end':'2014-12','geography':'NI','max_horizon':12,'units':'eligible archived tropical storm IDs/month','target':'Distinct MAIN IBTrACS SIDs with NI tropical (TS) positions; includes depressions, counted in first qualifying month.',
 'limitations':['North Indian Ocean basin only; not India-wide multi-hazard risk, Indian landfall probability or district warning.','Zero counts describe this archive, not verified absence of all real-world events. No binary disaster negatives are manufactured.','Revised best tracks through 2024; publication-time vintages are unavailable. Retrospective scores do not establish operational forecasting.','No rainfall, future weather, severity, fatalities or post-event impact predictors; only known calendar fields.','No calibrated probability or uncertainty intervals. Forecasts start in 2025, not current 2026.']},
 'pm25':{'id':'india_pm25_exposure_forecaster','file':'pm25_annual.csv','frequency':'annual','period':1,'train_end':'2009','validation_end':'2016','geography':'IND','max_horizon':1,'units':'micrograms/m³','target':'India national population-weighted modeled annual PM2.5 exposure (World Bank EN.ATM.PM25.MC.M3 / GBD2023).',
 'limitations':['National modeled exposure only; not destination occupancy, ecological carrying capacity or tourism-caused pollution.','Underlying indicator is modeled by GBD/IHME, not a local sensor outcome.','Only 34 annual observations; seven held-out annual targets, no independent geographic holdout.','Revised source vintage published in 2026, not historical publication-time data. Past-prefix evaluation is retrospective, not a real-time backtest.','No tourism or future environmental variables used as predictors; no causal tourism claim.','Last observed year is 2023. Output is a historical 2024 extrapolation, not current air quality or medical guidance. No calibrated intervals.']}}

def calendar_features(dates):
    month=pd.PeriodIndex(dates,freq='M').month.to_numpy()
    return np.column_stack([np.sin(2*np.pi*month/12),np.cos(2*np.pi*month/12),np.sin(4*np.pi*month/12),np.cos(4*np.pi*month/12)])

class CountForecaster:
    def __init__(self,method):self.method=method
    def fit(self,dates,values):
        self.mean=float(np.mean(values));months=pd.PeriodIndex(dates,freq='M').month
        self.seasonal={int(m):float(np.mean(np.asarray(values)[months==m])) for m in range(1,13)}
        if self.method=='poisson_calendar':self.estimator=PoissonRegressor(alpha=.1,max_iter=500).fit(calendar_features(dates),values)
        return self
    def predict(self,dates):
        if self.method=='poisson_calendar':return self.estimator.predict(calendar_features(dates))
        if self.method=='seasonal_mean':return np.array([self.seasonal[m] for m in pd.PeriodIndex(dates,freq='M').month])
        return np.full(len(dates),self.mean)

def compare(frame,kind):
    spec=SPECS[kind];values=validate_series(frame,spec['frequency']);dates=frame.date.astype(str).to_numpy()
    train=dates<=spec['train_end'];validation=(dates>spec['train_end'])&(dates<=spec['validation_end']);test=dates>spec['validation_end']
    if train.sum()<15 or validation.sum()<5 or test.sum()<5:raise ValueError('Insufficient chronological coverage.')
    scale=float(np.abs(values[spec['period']:train.sum()]-values[:train.sum()-spec['period']]).mean())
    methods=['constant_mean','seasonal_mean','poisson_calendar'] if kind=='cyclone_count' else ['naive','drift','ridge']
    predictions={};comparison={}
    for method in methods:
        predictions[method]={};comparison[method]={}
        for label,mask in [('validation',validation),('test',test)]:
            indices=np.flatnonzero(mask)
            if kind=='cyclone_count':
                # Freeze the fit before each holdout block; no test outcomes enter its fitted model.
                stop=indices[0];model=CountForecaster(method).fit(dates[:stop],values[:stop]);predicted=model.predict(dates[indices])
            else:
                # Expanding annual origins; fit every candidate on exactly the same past prefix.
                predicted=np.array([AnnualForecaster(method).fit(values[:i]).forecast(values[:i],1)[0] for i in indices])
            rows=[{'origin':str(dates[i-1]),'date':str(dates[i]),'actual':float(values[i]),'prediction':float(p)} for i,p in zip(indices,predicted)]
            if kind=='cyclone_count':
                for row in rows:row['origin']=str(dates[indices[0]-1])
            predictions[method][label]=rows
            comparison[method][label]=metrics(values[indices],predicted,scale)
            if kind=='cyclone_count':
                from sklearn.metrics import mean_poisson_deviance
                comparison[method][label]['mean_poisson_deviance']=float(mean_poisson_deviance(values[indices],np.maximum(predicted,1e-12)))
            comparison[method][label]['year_folds']={str(year):metrics([r['actual'] for r in rows if r['date'][:4]==str(year)],[r['prediction'] for r in rows if r['date'][:4]==str(year)],scale) for year in sorted({r['date'][:4] for r in rows})}
    # Count target selects on validation Poisson deviance; exposure uses validation MAE.
    criterion='mean_poisson_deviance' if kind=='cyclone_count' else 'MAE'
    selected=min(methods,key=lambda m:comparison[m]['validation'][criterion])
    baseline=methods[0]
    for method in methods:
        for split in ['validation','test']:
            comparison[method][split]['MAE_difference_vs_baseline']=comparison[method][split]['MAE']-comparison[baseline][split]['MAE']
    return {'selected_method':selected,'selection':f'Lowest {criterion} on validation only; test never selects method.','methods':comparison,'predictions':predictions,'MASE_denominator':scale,
      'splits':{name:{'start':str(dates[mask][0]),'end':str(dates[mask][-1]),'n':int(mask.sum())} for name,mask in [('train',train),('validation',validation),('test',test)]},
      'leakage':{'chronological':True,'cutoff_feature_rule':'Only calendar fields for cyclone counts; only observed past annual exposure prefixes for PM2.5. No contemporaneous/future weather, impact or tourism features.','geographic_holdout':'NOT_APPLICABLE: one basin or one country; no geographic generalization claim.','publication_time_vintages':'UNAVAILABLE: revised-vintage retrospective experiment, not simulated historical availability.'},
      'classification_metrics':'NOT_APPLICABLE: count/continuous regression; no fabricated binary negative labels or calibrated probabilities.'}

def load_scoped(project,kind):
    if kind not in SPECS:raise ValueError('Unknown supported forecasting task.')
    entry=next((m for m in load_registry(project/'models/registry.json') if m['model_id']==SPECS[kind]['id']),None)
    if entry is None:raise ValueError('No validated scoped forecasting model is registered.')
    bundle=load_artifact(project,entry)
    if not {'model','dates','values','kind'}.issubset(bundle) or bundle['kind']!=kind:raise ValueError('Invalid scoped artifact.')
    validate_series(pd.DataFrame({'date':bundle['dates'],'value':bundle['values']}),SPECS[kind]['frequency'])
    return entry,bundle

def predict_scoped(project,kind,payload):
    spec=SPECS[kind]
    if not isinstance(payload,dict) or set(payload)!={'geography','horizon'} or payload.get('geography')!=spec['geography'] or type(payload.get('horizon')) is not int or not 1<=payload['horizon']<=spec['max_horizon']:raise ValueError(f"Expected geography={spec['geography']} and integer horizon=1..{spec['max_horizon']} only.")
    entry,bundle=load_scoped(project,kind);horizon=payload['horizon'];origin=bundle['dates'][-1]
    if kind=='cyclone_count':
        dates=pd.period_range(pd.Period(origin,freq='M')+1,periods=horizon,freq='M').astype(str).tolist();prediction=bundle['model'].predict(dates)
    else:dates=[str(int(origin)+1)];prediction=bundle['model'].forecast(bundle['values'],1)
    if not np.isfinite(prediction).all() or min(prediction)<0:raise ValueError('Invalid saved-model output.')
    return {'status':'historical_experimental_forecast','model_id':entry['model_id'],'model_version':entry['model_version'],'quality_status':entry['quality_status'],'geography':spec['geography'],'target_definition':spec['target'],'units':spec['units'],'latest_observed_date':origin,'forecast_origin':origin,'horizon':horizon,'forecasts':[{'date':d,'horizon':i+1,'prediction':float(v)} for i,(d,v) in enumerate(zip(dates,prediction))],'limitations':spec['limitations']}

def train_scoped(project,kind):
    spec=SPECS[kind]
    if any(e['model_id']==spec['id'] for e in load_registry(project/'models/registry.json')):raise ValueError('Registered model exists; no overwrite.')
    path=project/DERIVED/spec['file'];provenance=json.loads((project/DERIVED/'model_data_provenance.json').read_text())
    if sha256(path)!=provenance['files'][spec['file']]:raise ValueError('Derived source checksum mismatch.')
    frame=pd.read_csv(path,dtype={'date':str});values=validate_series(frame,spec['frequency']);report=compare(frame,kind);method=report['selected_method']
    model=CountForecaster(method).fit(frame.date,values) if kind=='cyclone_count' else AnnualForecaster(method).fit(values)
    bundle={'model':model,'dates':frame.date.tolist(),'values':values.tolist(),'kind':kind}
    version=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ');folder=project/'models'/kind/version;folder.mkdir(parents=True,exist_ok=False)
    artifact=folder/'pipeline.joblib';joblib.dump(bundle,artifact);loaded=joblib.load(artifact)
    expected=model.predict(['2025-01']) if kind=='cyclone_count' else model.forecast(values,1)
    actual=loaded['model'].predict(['2025-01']) if kind=='cyclone_count' else loaded['model'].forecast(values,1)
    if not np.array_equal(expected,actual):raise ValueError('Artifact reload mismatch.')
    if kind=='cyclone_count':
        events=pd.read_csv(project/DERIVED/'cyclone_events.csv',dtype=str)
        groups=[set(events.loc[events.date.between(s['start'],s['end']),'event_id']) for s in report['splits'].values()]
        if any(groups[i]&groups[j] for i,j in [(0,1),(0,2),(1,2)]):raise ValueError('Event leakage across chronological splits.')
        report['leakage']['event_groups_disjoint']=True
        report['event_ids_by_split']={name:sorted(group) for name,group in zip(report['splits'],groups)}
    entry={'model_id':spec['id'],'model_version':version,'trained_at':utc_now(),'task':spec['target'],'task_type':'count_forecasting' if kind=='cyclone_count' else 'environmental_indicator_forecasting','quality_status':'TRAINED_BUT_EXPERIMENTAL','training_completed':True,'persistence_test_passed':True,'artifact':artifact.relative_to(project).as_posix(),'artifact_sha256':sha256(artifact),'method':method,'target_definition':spec['target'],'feature_schema':{'geography':spec['geography'],'horizon_max':spec['max_horizon'],'features':'known month sine/cosine harmonics' if kind=='cyclone_count' else 'past exposure only: up to three lags, past mean, past difference depending on selected method','frequency':spec['frequency'],'units':spec['units']},'latest_observed_date':str(frame.date.iloc[-1]),'dataset_provenance':provenance['cyclone' if kind=='cyclone_count' else 'pm25'],'metrics':report,'dependencies':{'python':platform.python_version(),'numpy':np.__version__,'pandas':pd.__version__,'sklearn':sklearn.__version__,'joblib':joblib.__version__},'limitations':spec['limitations']}
    for name,payload in [('metadata.json',entry),('evaluation.json',report),('feature_schema.json',entry['feature_schema']),('source_manifest.json',entry['dataset_provenance'])]:
        with (folder/name).open('x',encoding='utf-8') as f:json.dump(payload,f,indent=2,allow_nan=False)
    register_model(project/'models/registry.json',entry)
    return entry

def evaluate_scoped(project,kind):
    entry,bundle=load_scoped(project,kind)
    result=compare(pd.DataFrame({'date':bundle['dates'],'value':bundle['values']}),kind)
    if result['methods']!=entry['metrics']['methods'] or result['predictions']!=entry['metrics']['predictions'] or result['selected_method']!=entry['method']:raise ValueError('Evaluation replay mismatch.')
    return {'model_id':entry['model_id'],'status':'PASS','artifact_valid':True,'evaluation_reproduced':True,'selected_method':entry['method'],'metrics':result['methods'],'splits':result['splits']}
