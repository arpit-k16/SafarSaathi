"""Read-only research replay and independent metric checks for six saved pipelines.

No registry/artifact/raw writes, downloads, test-driven model promotion or
calibration fitting occur. Derived evidence is confined to research/model_validation.
"""
from __future__ import annotations

import os
os.environ.setdefault('OMP_NUM_THREADS', '1')
os.environ.setdefault('OPENBLAS_NUM_THREADS', '1')
os.environ.setdefault('MKL_NUM_THREADS', '1')

import hashlib
import json
import math
import platform
import time
import zipfile
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import sklearn
from sklearn.base import clone
from sklearn.calibration import calibration_curve
from sklearn.metrics import (accuracy_score, average_precision_score, brier_score_loss,
    classification_report, confusion_matrix, f1_score, log_loss, mean_absolute_error,
    mean_squared_error, precision_score, r2_score, recall_score, roc_auc_score)
from sklearn.model_selection import train_test_split

from safarsaathi_ml.artifacts import load_artifact
from safarsaathi_ml.forecasting import AnnualForecaster, load_forecast
from safarsaathi_ml.monthly_forecasting import MonthlyForecaster, load_monthly, validate_series
from safarsaathi_ml.readiness import load_arrivals
from safarsaathi_ml.scoped_forecasts import CountForecaster, SPECS, load_scoped
from safarsaathi_ml.flood_baseline import load_flood, image_features, read_pair, split_metadata

PROJECT = Path(__file__).resolve().parents[1]
OUT = PROJECT / 'research/model_validation'
SEED = 20261030


def digest(file):
    with Path(file).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def write_json(name, data):
    (OUT / name).write_text(json.dumps(data, indent=2, allow_nan=False), encoding='utf-8')


def regression(actual, predicted):
    """Metrics recomputed independently of repository metric helpers."""
    a, p = np.asarray(actual, float), np.asarray(predicted, float)
    assert len(a) == len(p) and len(a) and np.isfinite(a).all() and np.isfinite(p).all()
    errors = p - a
    return {'n': len(a), 'MAE': float(mean_absolute_error(a, p)),
            'RMSE': float(math.sqrt(mean_squared_error(a, p))),
            'R2': float(r2_score(a, p)) if len(a) > 1 and np.var(a) else None,
            'MAPE_fraction': float(np.mean(np.abs(errors / a))) if np.all(a > 0) else None,
            'WAPE_fraction': float(np.sum(np.abs(errors)) / np.sum(np.abs(a))) if np.sum(np.abs(a)) else None,
            'bias_prediction_minus_actual': float(errors.mean()),
            'residual_quantiles': {str(q): float(np.quantile(errors, q)) for q in [0, .1, .5, .9, 1]}}


def data_profile(frame, key, target):
    values = pd.to_numeric(frame[target], errors='coerce')
    return {'rows': len(frame), 'columns': list(frame.columns),
            'dtypes': {k: str(v) for k, v in frame.dtypes.items()},
            'missing': {k: int(v) for k, v in frame.isna().sum().items()},
            'duplicate_rows': int(frame.duplicated().sum()),
            'duplicate_keys': int(frame.duplicated(key).sum()),
            'invalid_or_nonfinite_targets': int((~np.isfinite(values)).sum()),
            'negative_targets': int((values < 0).sum()),
            'first_key': str(frame[key].iloc[0]), 'last_key': str(frame[key].iloc[-1])}


def calibration(actual, probability, bins=10):
    a, p = np.asarray(actual, int), np.asarray(probability, float)
    if not np.isfinite(p).all() or np.min(p) < 0 or np.max(p) > 1:
        raise ValueError('Invalid saved classifier probabilities.')
    records = []
    for i in range(bins):
        selected = (p >= i / bins) & ((p < (i + 1) / bins) if i < bins - 1 else (p <= 1))
        if selected.any():
            records.append({'bin_low': i / bins, 'bin_high': (i + 1) / bins,
                            'n': int(selected.sum()), 'mean_score': float(p[selected].mean()),
                            'observed_positive_rate': float(a[selected].mean())})
    ece = sum(r['n'] / len(a) * abs(r['mean_score'] - r['observed_positive_rate']) for r in records)
    return {'Brier': float(brier_score_loss(a, p)), 'ROC_AUC': float(roc_auc_score(a, p)),
            'PR_AUC_average_precision': float(average_precision_score(a, p)),
            'log_loss': float(log_loss(a, np.column_stack([1-p, p]), labels=[0, 1])),
            'ECE_10_equal_width_bins': float(ece), 'bins': records,
            'note': 'Descriptive heldout calibration assessment; no calibrator fitted on test outcomes.'}


def add_comparison(comparison, entry, algorithm, metrics, horizon='', split='test', evaluation='historical holdout'):
    comparison.append({'experiment_id': f"p3_{entry['model_id']}_{algorithm}_{horizon or 'na'}",
                       'model_id': entry['model_id'], 'model_version': entry.get('model_version', entry['model_id']),
                       'algorithm': algorithm, 'horizon': horizon, 'split': split,
                       'evaluation': evaluation, **{k: v for k, v in metrics.items() if not isinstance(v, (dict, list))}})


def nlp(entry, comparison):
    source = PROJECT.parent / Path(entry['dataset_provenance']['repository_relative_path'].replace('\\', '/'))
    frame = pd.read_csv(source)
    t, l = entry['text_column'], entry['label_column']
    # Match original pipeline exactly: pair de-duplication precedes strip.
    cleaned = frame[[t, l]].dropna().drop_duplicates().copy()
    cleaned[t] = cleaned[t].astype(str).str.strip()
    cleaned = cleaned[cleaned[t].str.len() > 0]
    train, test = train_test_split(cleaned, test_size=.2, random_state=entry['random_seed'], stratify=cleaned[l])
    model = load_artifact(PROJECT, entry)
    prediction = model.predict(test[t])
    classes = model.classes_.tolist()
    positive = classes.index('POSITIVE')
    probability = model.predict_proba(test[t])[:, positive]
    actual = test[l].eq('POSITIVE').astype(int).to_numpy()
    normalise = lambda values: values.astype(str).str.casefold().str.replace(r'\s+', ' ', regex=True).str.strip()
    vectorizer = clone(model.named_steps['tfidf']).fit(train[t])
    vocabulary_equal = vectorizer.vocabulary_ == model.named_steps['tfidf'].vocabulary_
    idf_equal = bool(np.allclose(vectorizer.idf_, model.named_steps['tfidf'].idf_, atol=1e-12, rtol=0))
    scores = {'accuracy': float(accuracy_score(test[l], prediction)),
              'macro_F1': float(f1_score(test[l], prediction, average='macro')),
              'weighted_F1': float(f1_score(test[l], prediction, average='weighted')),
              'precision_positive': float(precision_score(actual, prediction == 'POSITIVE')),
              'recall_positive': float(recall_score(actual, prediction == 'POSITIVE')),
              'classification_report': classification_report(test[l], prediction, output_dict=True),
              'confusion_labels': classes, 'confusion_matrix': confusion_matrix(test[l], prediction, labels=classes).tolist(),
              **calibration(actual, probability)}
    majority = train[l].mode().iloc[0]
    dummy_prediction = np.repeat(majority, len(test))
    baseline = {'accuracy': float(accuracy_score(test[l], dummy_prediction)),
                'macro_F1': float(f1_score(test[l], dummy_prediction, average='macro')),
                'Brier': float(brier_score_loss(actual, np.repeat(train[l].eq('POSITIVE').mean(), len(test))))}
    assert math.isclose(scores['accuracy'], entry['metrics']['accuracy'], abs_tol=1e-12)
    assert math.isclose(scores['macro_F1'], entry['metrics']['macro_f1'], abs_tol=1e-12)
    profile = {'source': source.relative_to(PROJECT.parent).as_posix(), 'sha256': digest(source),
               'source_hash_matches_registered': digest(source) == entry['dataset_provenance']['sha256'],
               'source_rows': len(frame), 'missing_text_or_label': int(frame[[t, l]].isna().any(axis=1).sum()),
               'exact_duplicate_pairs_removed': int(frame[[t, l]].duplicated().sum()),
               'post_strip_duplicate_pairs': int(cleaned.duplicated().sum()),
               'conflicting_label_text_groups': int(cleaned.groupby(t)[l].nunique().gt(1).sum()),
               'exact_train_test_text_overlap': len(set(train[t]) & set(test[t])),
               'normalized_train_test_text_overlap': len(set(normalise(train[t])) & set(normalise(test[t]))),
               'class_counts': {name: data[l].value_counts().to_dict() for name, data in [('source', cleaned), ('train', train), ('test', test)]},
               'train_rows': len(train), 'test_rows': len(test),
               'tfidf_train_only_vocabulary_reproduced': vocabulary_equal,
               'tfidf_train_only_idf_reproduced': idf_equal,
               'heldout_zero_vocabulary_vector_rows':int((model.named_steps['tfidf'].transform(test[t]).getnnz(axis=1)==0).sum()),
               'controlled_unsupported_probe_zero_vectors':int((model.named_steps['tfidf'].transform(['1234567890','zzqqxxvv zzzqqq','यह यात्रा समीक्षा है']).getnnz(axis=1)==0).sum()),
               'controlled_unsupported_probe_count':3,
               'entity_temporal_split': 'Hotel/reviewer identity and temporal group labels not available; no entity or future-domain generalization established.'}
    add_comparison(comparison, entry, 'saved_tfidf_logistic', {'n': len(test), **scores})
    add_comparison(comparison, entry, 'training_majority_dummy', {'n': len(test), **baseline})
    pd.DataFrame({'source_row_index': test.index, 'actual': test[l], 'prediction': prediction, 'positive_score': probability}).to_csv(OUT/'nlp_heldout_predictions.csv', index=False)
    return {'model_id': entry['model_id'], 'algorithm': str(model), 'data': profile,
            'metrics': scores, 'baseline': baseline, 'stored_metrics_reproduced': True}


def regression_rows(entry, rows, comparison, pool_horizons=False):
    frame = pd.DataFrame(rows)
    scores = {}
    metric_frame = frame.assign(horizon=0) if pool_horizons else frame
    for (method, split, horizon), selected in metric_frame.groupby(['method', 'split', 'horizon'], sort=True):
        score = regression(selected.actual, selected.prediction)
        scores[f'{method}/{split}/h{horizon}'] = score
        if split == 'test':
            add_comparison(comparison, entry, method, score, 'pooled fixed-origin months 1..120' if pool_horizons else int(horizon))
    frame['residual_prediction_minus_actual'] = frame.prediction - frame.actual
    frame.to_csv(OUT/f"{entry['model_id']}{entry.get('_evidence_suffix','')}_predictions.csv", index=False)
    selected_method = entry['method']
    # A descriptive residual band, not a formal prediction interval: validation
    # residuals are few/nonexchangeable and publication-time vintages unavailable.
    bands = []
    for horizon in sorted(metric_frame.horizon.unique()):
        val = metric_frame[(metric_frame.method == selected_method) & (metric_frame.split == 'validation') & (metric_frame.horizon == horizon)]
        test = metric_frame[(metric_frame.method == selected_method) & (metric_frame.split == 'test') & (metric_frame.horizon == horizon)]
        if len(val) and len(test):
            q = float(np.quantile(np.abs(val.actual-val.prediction), .9, method='higher'))
            bands.append({'horizon': int(horizon), 'validation_n': len(val), 'test_n': len(test),
                          'validation_absolute_residual_quantile_90': q,
                          'test_band_coverage': float((np.abs(test.actual-test.prediction) <= q).mean()),
                          'mean_band_width': 2*q,
                          'status': 'EXPLORATORY_FIXED_WIDTH_RESIDUAL_BAND_NOT_CALIBRATED_INTERVAL'})
    return scores, bands


def annual(comparison):
    entry, bundle = load_forecast(PROJECT)
    frame, profile = load_arrivals(PROJECT.parent/'SafarSaathi_Datasets/raw')
    values = np.asarray(bundle['values'], float); years = bundle['years']
    assert frame.arrivals.tolist() == bundle['values'] and frame.year.tolist() == years
    rows = []
    methods = ['drift', 'persistence', 'historical_mean', 'expanding_drift', 'expanding_ridge']
    for split, start, stop in [('validation', bundle['train_end'], bundle['validation_end']), ('test', bundle['validation_end'], len(values))]:
        frozen = AnnualForecaster('drift').fit(values[:start]) if split == 'validation' else bundle['evaluation_model']
        for method in methods:
            for origin in range(start, stop):
                horizon = min(3, stop-origin)
                past = values[:origin]
                if method == 'drift': predictions = frozen.forecast(past, horizon)
                elif method == 'persistence': predictions = [past[-1]]*horizon
                elif method == 'historical_mean': predictions = [past.mean()]*horizon
                else: predictions = AnnualForecaster('drift' if method == 'expanding_drift' else 'ridge').fit(past).forecast(past, horizon)
                rows += [{'method': method, 'split': split, 'origin': years[origin-1], 'target': years[origin+h-1], 'horizon': h,
                          'actual': float(values[origin+h-1]), 'prediction': float(pred)} for h,pred in enumerate(predictions,1)]
    scores, bands = regression_rows(entry, rows, comparison)
    matched = all(math.isclose(scores[f'drift/test/h{h}'][metric], entry['metrics']['by_horizon'][str(h)][metric], abs_tol=1e-8)
                  for h in [1,2,3] for metric in ['MAE','RMSE'])
    assert matched
    return {'model_id': entry['model_id'], 'algorithm': 'Frozen drift estimator for original holdout; final inference drift refit through 2019',
            'source_profile': profile, 'data': data_profile(frame,'year','arrivals'), 'metrics': scores,
            'source_hash_matches_registered':profile['sha256']==entry['dataset_provenance']['sha256'],
            'residual_bands': bands, 'stored_metrics_reproduced': matched,
            'seasonal_baseline': 'Not applicable: annual totals do not establish a within-year seasonal period.',
            'comparison_note': 'Original evaluation drift stays frozen through 2014; expanding baselines recompute using only past observations. All methods share exact targets/origins.'}


def monthly(comparison):
    entry, bundle = load_monthly(PROJECT)
    source = PROJECT/'data/processed/tourism_monthly_fta/20261025/monthly_fta.csv'
    frame = pd.read_csv(source); dates, values = validate_series(frame)
    assert values.tolist() == bundle['values'] and dates.astype(str).tolist() == bundle['dates']
    rows=[]
    for split,start,stop in [('validation',36,48),('test',48,72)]:
        for method in ['persistence','drift','historical_mean','seasonal_naive','ridge']:
            for origin in range(start,stop):
                pred=MonthlyForecaster(method,dates[0].month).fit(values[:origin]).forecast(values[:origin],min(6,stop-origin))
                rows += [{'method':method,'split':split,'origin':str(dates[origin-1]),'target':str(dates[origin+h-1]),'horizon':h,
                          'actual':float(values[origin+h-1]),'prediction':float(pred[h-1])} for h in [1,3,6] if h<=len(pred)]
    scores,bands=regression_rows(entry,rows,comparison)
    matched=all(math.isclose(scores[f"{entry['method']}/test/h{h}"][m],entry['metrics']['test'][entry['method']][str(h)][m],abs_tol=1e-8)
                for h in [1,3,6] for m in ['MAE','RMSE'])
    assert matched
    pdf_sources=[]
    for item in entry['dataset_provenance']['sources']:
        path=PROJECT.parent/item['path']
        pdf_sources.append({'path':item['path'],'exists':path.is_file(),
                            'sha256_matches_provenance':digest(path)==item['sha256'] if path.is_file() else False})
    return {'model_id':entry['model_id'],'algorithm':entry['method'],'data':data_profile(frame,'date','arrivals'),
            'source_sha256':digest(source),'source_matches_provenance':digest(source)==entry['dataset_provenance']['derived_csv_sha256'],
            'pdf_source_hash_checks':pdf_sources,
            'metrics':scores,'residual_bands':bands,'stored_metrics_reproduced':matched,
            'selection_warning':'Validation-selected persistence is preserved. Test-set seasonal-naive superiority at horizons 3/6 cannot be used to claim a newly validated improvement; a new untouched future period is required.'}


def scoped(kind,comparison):
    entry,bundle=load_scoped(PROJECT,kind);spec=SPECS[kind]
    dates=np.asarray(bundle['dates']); values=np.asarray(bundle['values'],float)
    frame=pd.read_csv(PROJECT/'data/processed/india_scope_20261025'/spec['file'],dtype={'date':str})
    assert frame.value.tolist()==bundle['values'] and frame.date.tolist()==bundle['dates']
    methods=['constant_mean','seasonal_mean','poisson_calendar'] if kind=='cyclone_count' else ['naive','drift','ridge']
    rows=[]
    for split,start_label,end_label in [('validation',spec['train_end'],spec['validation_end']),('test',spec['validation_end'],str(dates[-1]))]:
        indices=np.flatnonzero((dates>start_label)&(dates<=end_label))
        for method in methods:
            if kind=='cyclone_count':
                model=CountForecaster(method).fit(dates[:indices[0]],values[:indices[0]])
                prediction=model.predict(dates[indices])
            else: prediction=[AnnualForecaster(method).fit(values[:i]).forecast(values[:i],1)[0] for i in indices]
            rows += [{'method':method,'split':split,'origin':str(dates[indices[0]-1] if kind=='cyclone_count' else dates[i-1]),
                      'target':str(dates[i]),'horizon':int(i-indices[0]+1) if kind=='cyclone_count' else 1,'actual':float(values[i]),'prediction':float(p)} for i,p in zip(indices,prediction)]
    scores,bands=regression_rows(entry,rows,comparison,pool_horizons=kind=='cyclone_count')
    matched=all(math.isclose(scores[f"{entry['method']}/test/h{0 if kind=='cyclone_count' else 1}"][m],entry['metrics']['methods'][entry['method']]['test'][m],abs_tol=1e-10) for m in ['MAE','RMSE'])
    assert matched
    data=data_profile(frame,'date','value')
    if kind=='cyclone_count':
        events=pd.read_csv(PROJECT/'data/processed/india_scope_20261025/cyclone_events.csv')
        event_sets=[set(events.loc[events.date.between(s['start'],s['end']),'event_id']) for s in entry['metrics']['splits'].values()]
        data['event_ids_disjoint_across_splits']=not any(event_sets[i]&event_sets[j] for i,j in [(0,1),(0,2),(1,2)])
        data['zero_target_months']=int((values==0).sum())
        data['event_rows']=len(events);data['unique_events']=int(events.event_id.nunique())
        rolling=[]
        for method in methods:
            for origin in np.flatnonzero(dates>spec['validation_end']):
                fitted=CountForecaster(method).fit(dates[:origin],values[:origin])
                for h in [1,3,6,12]:
                    if origin+h<=len(values):
                        target=origin+h-1
                        rolling.append({'method':f'rolling_{method}','split':'test','origin':str(dates[origin-1]),'target':str(dates[target]),
                                        'horizon':h,'actual':float(values[target]),'prediction':float(fitted.predict([dates[target]])[0])})
        rolling_scores,_=regression_rows({**entry,'_evidence_suffix':'_rolling_diagnostic'},rolling,comparison)
    else:rolling_scores=None
    provenance=json.loads((PROJECT/'data/processed/india_scope_20261025/model_data_provenance.json').read_text())
    source_path=PROJECT/'data/external/india_scope_20261025'/('disaster_risk' if kind=='cyclone_count' else 'destination_stress')/entry['dataset_provenance']['source']['original_filename']
    return {'model_id':entry['model_id'],'algorithm':entry['method'],'data':data,'metrics':scores,'residual_bands':bands,
            'derived_source_hash_matches_provenance':digest(PROJECT/'data/processed/india_scope_20261025'/spec['file'])==provenance['files'][spec['file']],
            'original_source_hash_matches_registered':digest(source_path)==entry['dataset_provenance']['source']['sha256'],
            'stored_metrics_reproduced':matched,'rolling_horizon_diagnostic':rolling_scores,
            'publication_time_vintages':'Unavailable; revised-vintage retrospective evaluation only.',
            'horizon_note':'Count model test predictions cover a fixed 120-month holdout from one origin, not 120 independent operational one-month refits.' if kind=='cyclone_count' else 'Only one-step annual forecast supported.'}


def flood(comparison):
    entry,bundle=load_flood(PROJECT)
    path=PROJECT/'data/external/sturm_flood/12748983/Dataset.zip'
    report={'model_id':entry['model_id'],'algorithm':str(bundle['model']),
            'archive_bytes':path.stat().st_size,'registered_archive_bytes':entry['dataset_provenance']['bytes'],
            'archive_integrity_scope':'Existing archive-size checked; ZIP CRC checked automatically for every member read. Full 3.985GB hash not recomputed in this bounded validation.'}
    if path.stat().st_size != entry['dataset_provenance']['bytes']:raise ValueError('Archive size differs from registered source.')
    probabilities=[];actuals=[];scenes=[]
    with zipfile.ZipFile(path) as archive:
        metadata=pd.read_csv(archive.open('Dataset/Sentinel1_metadata.csv'))
        splits,groups,inventory=split_metadata(metadata)
        report['metadata_inventory']=inventory
        report['split_country_groups']=groups
        report['saved_splits_reproduced']=all(splits[k].tile_id.tolist()==entry['metrics']['splits'][k]['tiles'] for k in groups)
        assert report['saved_splits_reproduced']
        for row in splits['test'].itertuples():
            image,mask,tags,class_values=read_pair(archive,row.tile_id)
            proba=bundle['model'].predict_proba(image_features(image))[:,1]
            prediction=proba>=bundle['threshold']; actual=mask.ravel().astype(bool)
            counts=np.array([np.sum(~actual&~prediction),np.sum(~actual&prediction),np.sum(actual&~prediction),np.sum(actual&prediction)],dtype=np.int64)
            scenes.append({'tile':row.tile_id,'country':row.country,'event':row.ems_code,'tn':int(counts[0]),'fp':int(counts[1]),'fn':int(counts[2]),'tp':int(counts[3]),
                           'sentinel_date':str(row.sentinel_date),'reference_date':str(row.floodmap_date),'epsg':int(row.epsg_code),
                           'finite_image':bool(np.isfinite(image).all()),'minimum_input':float(image.min()),'maximum_input':float(image.max()),'observed_raw_mask_classes':str(class_values)})
            probabilities.append(proba);actuals.append(actual)
    p=np.concatenate(probabilities);a=np.concatenate(actuals).astype(int);pred=p>=bundle['threshold']
    tn,fp,fn,tp=confusion_matrix(a,pred).ravel()
    scores={'n':len(a),'precision_positive':float(precision_score(a,pred)), 'recall_positive':float(recall_score(a,pred)),
            'Dice_F1':float(f1_score(a,pred)),'IoU':float(tp/(tp+fp+fn)),
            'accuracy':float(accuracy_score(a,pred)),'confusion_matrix':[[int(tn),int(fp)],[int(fn),int(tp)]],
            'reference_positive_prevalence':float(a.mean()),**calibration(a,p)}
    matched=np.array_equal(scores['confusion_matrix'],entry['metrics']['test']['confusion_matrix'])
    assert matched
    country=[]
    for name,group in pd.DataFrame(scenes).groupby('country'):
        tn,fp,fn,tp=group[['tn','fp','fn','tp']].sum()
        country.append({'country':name,'tiles':len(group),'events':int(group.event.nunique()),
                        'precision':float(tp/(tp+fp)) if tp+fp else None,'recall':float(tp/(tp+fn)) if tp+fn else None,
                        'IoU':float(tp/(tp+fp+fn)) if tp+fp+fn else None,'Dice_F1':float(2*tp/(2*tp+fp+fn)) if 2*tp+fp+fn else None})
    pd.DataFrame(scenes).to_csv(OUT/'flood_test_tiles.csv',index=False)
    pd.DataFrame(country).to_csv(OUT/'flood_metrics_by_country.csv',index=False)
    add_comparison(comparison,entry,f"saved_{entry['metrics']['selected_method']}_threshold_{bundle['threshold']}",scores,evaluation='Country/event-heldout reference pixels')
    baseline_negative={'n':len(a),'accuracy':float((1-a).mean()),'recall_positive':0.,'Dice_F1':0.,'IoU':0.}
    baseline_positive={'n':len(a),'accuracy':float(a.mean()),'precision_positive':float(a.mean()),'recall_positive':1.,'Dice_F1':float(2*a.mean()/(1+a.mean())),'IoU':float(a.mean())}
    add_comparison(comparison,entry,'always_reference_negative',baseline_negative,evaluation='Identical heldout pixels')
    add_comparison(comparison,entry,'always_reference_positive',baseline_positive,evaluation='Identical heldout pixels')
    train_prevalence=entry['metrics']['training_reference_positive_fraction']
    train_constant={'n':len(a),'Brier':float(brier_score_loss(a,np.repeat(train_prevalence,len(a))))}
    add_comparison(comparison,entry,'constant_training_sample_prevalence',train_constant,evaluation='Identical heldout pixels; probability fixed from training only')
    return {**report,'metrics':scores,'country_metrics':country,'threshold':bundle['threshold'],'stored_metrics_reproduced':matched,
            'confidence_intervals':'Not computed as independent-pixel binomial intervals: spatial dependence and only four country holdouts would make these misleading.',
            'limitations':['Reference label includes permanent water and temporary flood extent; not a validated temporary-flood detector.',
                           'Calibration/AUC scores are pooled descriptive pixel metrics. Correlated pixels do not constitute independent replication.',
                           'No Nepal, Uttarakhand, raw-scene or event-specific 2026 generalization is established.']}


def make_figure(results):
    fig,axes=plt.subplots(2,2,figsize=(12,8),layout='constrained')
    monthly=results['monthly']['metrics']; hs=[1,3,6]
    for method in ['persistence','seasonal_naive','ridge']:
        axes[0,0].plot(hs,[monthly[f'{method}/test/h{h}']['MAE'] for h in hs],marker='o',label=method)
    axes[0,0].set(title='FTA: persistence weakens at longer horizons',xlabel='Forecast horizon (months)',ylabel='Heldout MAE (arrivals)');axes[0,0].legend(fontsize=8)
    methods=['drift','persistence','historical_mean','expanding_drift','expanding_ridge'];annual=results['annual']['metrics']
    axes[0,1].bar(range(len(methods)),[annual[f'{m}/test/h1']['MAE'] for m in methods],color='#377eb8')
    axes[0,1].set_xticks(range(len(methods)),methods,rotation=25,ha='right',fontsize=8);axes[0,1].set(title='Annual national arrivals: five test targets only',ylabel='One-step MAE (arrivals)')
    for key,label in [('nlp','Review labels'),('flood','Reference-positive pixels')]:
        bins=results[key]['metrics']['bins'];axes[1,0].plot([r['mean_score'] for r in bins],[r['observed_positive_rate'] for r in bins],marker='o',label=label)
    axes[1,0].plot([0,1],[0,1],'k--',linewidth=1);axes[1,0].set(xlabel='Mean predicted score in bin',ylabel='Observed positive rate',title='Descriptive heldout calibration; not operational confidence');axes[1,0].legend(fontsize=8)
    country=results['flood']['country_metrics'];axes[1,1].bar([r['country'] for r in country],[r['IoU'] for r in country],color='#ff7f00');axes[1,1].set(ylim=(0,1),ylabel='Reference-positive IoU',title='Flood benchmark geographic variation')
    fig.savefig(OUT/'model_benchmark.png',dpi=160);plt.close(fig)


def main():
    OUT.mkdir(parents=True,exist_ok=True)
    registry=json.loads((PROJECT/'models/registry.json').read_text(encoding='utf-8'))
    comparison=[];start=time.perf_counter()
    results={'generated_utc':pd.Timestamp.now(tz='UTC').isoformat(),'seed':SEED,
             'environment':{'python':platform.python_version(),'numpy':np.__version__,'pandas':pd.__version__,'scikit_learn':sklearn.__version__},
             'evaluation_scope':'Independent metric recomputation and source-aligned replay of existing known holdouts, not a new untouched external test set.'}
    results['nlp']=nlp(next(e for e in registry if e['task']=='review classification'),comparison)
    print('NLP evaluated',flush=True)
    results['annual']=annual(comparison);print('Annual evaluated',flush=True)
    results['monthly']=monthly(comparison);print('Monthly evaluated',flush=True)
    results['cyclone']=scoped('cyclone_count',comparison);results['pm25']=scoped('pm25',comparison);print('Scoped forecasts evaluated',flush=True)
    results['flood']=flood(comparison);print('Flood evaluated',flush=True)
    results['runtime_seconds']=time.perf_counter()-start
    pd.DataFrame(comparison).to_csv(OUT/'MODEL_COMPARISON.csv',index=False)
    write_json('evaluation_results.json',results)
    make_figure(results)
    summary={k:{'model_id':v['model_id'],'stored_metrics_reproduced':v['stored_metrics_reproduced']} for k,v in results.items() if isinstance(v,dict) and 'model_id' in v}
    print(json.dumps(summary,indent=2))


if __name__=='__main__':main()
