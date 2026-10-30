"""Small annual forecaster with fixed chronological selection and replayable holdout."""
from __future__ import annotations

import json
import platform
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import joblib
import numpy as np
import sklearn
from sklearn.linear_model import Ridge
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from .pipeline import sha256, utc_now
from .readiness import IDS, load_arrivals
from .registry import load_registry, register_model, resolve_artifact_path

LIMITATIONS = [
    'Experimental historical India national annual forecast; not an Uttarakhand or destination forecast.',
    'Latest observation is 2019. Horizon is anchored to that year, not today. No current-demand claim.',
    'Only 25 annual observations; five test origins and no pandemic/post-pandemic outcomes.',
    'Large 2014 level change may reflect source/measurement changes; not reconciled with ministry counts.',
    'Vintage backtest uses the locally collected revised series, not historical publication vintages.',
    'No calibrated uncertainty intervals; forecasts are estimates, not observed facts.',
]


def features(history) -> np.ndarray:
    h = np.asarray(history, dtype=float)
    if h.ndim != 1 or len(h) < 3 or not np.isfinite(h).all() or (h < 0).any():
        raise ValueError('At least three finite non-negative past annual observations are required.')
    return np.array([h[-1], h[-2], h[-3], h[-3:].mean(), h[-1] - h[-2]])


@dataclass
class AnnualForecaster:
    method: str
    estimator: object = None
    drift: float = 0.0

    def fit(self, values):
        y = np.asarray(values, dtype=float)
        features(y)
        if len(y) < 8:
            raise ValueError('At least eight observations are required for fitting.')
        if self.method == 'ridge':
            self.estimator = make_pipeline(StandardScaler(), Ridge(alpha=10.0))
            self.estimator.fit(np.stack([features(y[:i]) for i in range(3, len(y))]), y[3:])
        elif self.method == 'drift':
            self.drift = float(np.diff(y).mean())
        elif self.method != 'naive':
            raise ValueError('Unsupported forecasting method.')
        return self

    def forecast(self, history, horizon=1):
        if type(horizon) is not int or not 1 <= horizon <= 3:
            raise ValueError('horizon must be an integer from 1 to 3 annual periods.')
        past = list(np.asarray(history, dtype=float))
        features(past)
        result = []
        for _ in range(horizon):
            prediction = (float(self.estimator.predict(features(past).reshape(1, -1))[0]) if self.method == 'ridge'
                          else past[-1] + (self.drift if self.method == 'drift' else 0.0))
            prediction = max(0.0, prediction)
            if not np.isfinite(prediction):
                raise ValueError('Saved model produced an invalid forecast.')
            past.append(prediction); result.append(prediction)
        return result


def metrics(actual, predicted, scale):
    actual, predicted = np.asarray(actual, dtype=float), np.asarray(predicted, dtype=float)
    if actual.ndim != 1 or actual.size == 0 or actual.shape != predicted.shape or not np.isfinite(actual).all() or not np.isfinite(predicted).all() or not np.isfinite(scale) or scale < 0:
        raise ValueError('Metrics require aligned non-empty finite arrays and a finite non-negative scale.')
    error = actual - predicted
    return {'MAE': float(np.abs(error).mean()), 'RMSE': float(np.sqrt((error ** 2).mean())),
            'MASE': float(np.abs(error).mean() / scale) if scale > 0 else None,
            'WAPE': float(np.abs(error).sum() / np.abs(actual).sum()) if np.abs(actual).sum() > 0 else None,
            'n': len(actual)}


def backtest(model, values, years, start, stop, scale):
    rows = []
    for origin in range(start, stop):
        forecast = model.forecast(values[:origin], min(3, stop - origin))
        for horizon, prediction in enumerate(forecast, 1):
            rows.append({'destination': 'IND', 'origin_year': int(years[origin - 1]), 'year': int(years[origin + horizon - 1]),
                         'horizon': horizon, 'actual': float(values[origin + horizon - 1]), 'prediction': prediction})
    by_horizon = {str(h): metrics([r['actual'] for r in rows if r['horizon'] == h],
                                 [r['prediction'] for r in rows if r['horizon'] == h], scale) for h in (1, 2, 3)}
    return {'by_destination': {'IND': by_horizon['1']}, 'by_horizon': by_horizon, 'predictions': rows}


def train_forecast(project: Path, raw: Path) -> dict:
    registry = project / 'models/registry.json'
    existing = load_registry(registry)
    if any(m['model_id'] == IDS['tourism_demand'] for m in existing):
        raise ValueError('Tourism model is already registered; existing artifacts are never overwritten. Use a separate project root for a new experiment.')
    frame, profile = load_arrivals(raw)
    if len(frame) < 20:
        raise ValueError('Need at least 20 contiguous observed annual targets for train/validation/test.')
    values, years = frame.arrivals.to_numpy(float), frame.year.to_numpy(int)
    train_end, validation_end = len(values) - 10, len(values) - 5
    scale = float(np.abs(np.diff(values[:train_end])).mean())
    selection = {}
    for method in ('naive', 'drift', 'ridge'):
        fitted = AnnualForecaster(method).fit(values[:train_end])
        selection[method] = backtest(fitted, values, years, train_end, validation_end, scale)['by_horizon']['1']
    selected = min(selection, key=lambda name: selection[name]['MAE'])
    evaluation_model = AnnualForecaster(selected).fit(values[:validation_end])
    test = backtest(evaluation_model, values, years, validation_end, len(values), scale)
    baseline = backtest(AnnualForecaster('naive').fit(values[:validation_end]), values, years, validation_end, len(values), scale)
    final = AnnualForecaster(selected).fit(values)
    version = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    folder = project / 'models/tourism_demand' / version
    folder.mkdir(parents=True, exist_ok=False)
    artifact = folder / 'pipeline.joblib'
    bundle = {'model': final, 'evaluation_model': evaluation_model, 'values': values.tolist(), 'years': years.tolist(),
              'train_end': train_end, 'validation_end': validation_end, 'mase_scale': scale}
    joblib.dump(bundle, artifact)
    reloaded = joblib.load(artifact)
    if reloaded['model'].forecast(values, 3) != final.forecast(values, 3):
        raise ValueError('Artifact reload predictions differ.')
    reproduced = backtest(reloaded['evaluation_model'], values, years, validation_end, len(values), scale)
    if reproduced != test:
        raise ValueError('Saved evaluation replay differs.')
    schema = {'input': {'destination': 'IND only', 'horizon': 'integer 1..3 years after latest observed year'},
              'features': ['lag_1', 'lag_2', 'lag_3', 'past_3_mean', 'lag_1_minus_lag_2'],
              'output': 'annual predicted international tourist arrivals; non-negative counts',
              'external_features': 'none; all features derived strictly from prior observations'}
    metadata = {'model_id': IDS['tourism_demand'], 'model_version': version, 'task': 'annual tourism demand forecasting',
                'task_type': 'time_series_regression', 'target_definition': 'India annual international tourist arrivals, World Bank ST.INT.ARVL',
                'trained_at': utc_now(), 'training_completed': True, 'evaluation_independently_reproduced': True,
                'reproduction_scope': 'Saved evaluation estimator reloaded and test metrics replayed; separate CLI replay available.',
                'dataset_provenance': profile, 'feature_schema': schema, 'method': selected,
                'split': {'train_years': years[:train_end].tolist(), 'validation_years': years[train_end:validation_end].tolist(),
                          'test_years': years[validation_end:].tolist(),
                          'strategy': 'Fixed chronological blocks; select using validation one-year MAE only; freeze fit through validation for rolling-origin test; final refit all observed years.',
                          'test_history': 'Past actual observations permitted at successive origins; multi-step forecasts recursive, never use future actuals.'},
                'training_configuration': {'seed': 20261025, 'ridge_alpha': 10.0, 'max_horizon': 3, 'normalization': 'StandardScaler fit on training features only',
                                           'compute': 'CPU; <100 rows, <10 MB incremental expected memory; expected <10 seconds, no downloads'},
                'validation_comparison': selection, 'metrics': test, 'baseline_metrics': baseline,
                'metric_definitions': {'MASE': 'MAE / mean absolute first difference in initial training series', 'WAPE': 'sum absolute error / sum absolute actual; fraction, null if zero denominator'},
                'software_versions': {'python': platform.python_version(), 'scikit_learn': sklearn.__version__, 'numpy': np.__version__, 'joblib': joblib.__version__},
                'latest_observed_year': int(years[-1]), 'geographic_scope': 'IND', 'limitations': LIMITATIONS,
                'artifact': artifact.relative_to(project).as_posix(), 'artifact_sha256': sha256(artifact), 'persistence_test_passed': True}
    for filename, content in [('metadata.json', metadata), ('feature_schema.json', schema), ('evaluation.json', test), ('configuration.json', metadata['training_configuration'])]:
        (folder / filename).write_text(json.dumps(content, indent=2), encoding='utf-8')
    register_model(registry, metadata)
    return metadata


def load_forecast(project: Path):
    entry = next((m for m in load_registry(project / 'models/registry.json') if m['model_id'] == IDS['tourism_demand']), None)
    if entry is None:
        raise ValueError('Tourism forecasting is not trained or registered.')
    artifact = resolve_artifact_path(project, entry['artifact'])
    if sha256(artifact) != entry.get('artifact_sha256'):
        raise ValueError('Tourism artifact checksum validation failed.')
    try:
        from .artifacts import load_artifact
        bundle = load_artifact(project, entry)
        if not isinstance(bundle['model'], AnnualForecaster):
            raise ValueError('Unsupported model artifact.')
        bundle['model'].forecast(bundle['values'], 1)
    except Exception as exc:
        raise ValueError('Tourism artifact could not be validated.') from exc
    return entry, bundle


def forecast(project: Path, destination: str, horizon: int) -> dict:
    if destination != 'IND' or type(horizon) is not int or not 1 <= horizon <= 3:
        raise ValueError('destination must be IND and horizon an integer from 1 to 3.')
    entry, bundle = load_forecast(project)
    predicted = bundle['model'].forecast(bundle['values'], horizon)
    last = bundle['years'][-1]
    return {'model_id': entry['model_id'], 'model_version': entry['model_version'], 'destination': 'IND',
            'status': 'historical_experimental_forecast', 'latest_observed_year': last, 'units': 'international tourist arrivals/year',
            'forecast_origin_year': last, 'horizon': horizon, 'quality_status': 'TRAINED_BUT_EXPERIMENTAL', 'is_forecast': True,
            'forecasts': [{'year': last + h, 'horizon': h, 'prediction': p} for h, p in enumerate(predicted, 1)],
            'limitations': entry['limitations']}


def evaluate_forecast(project: Path) -> dict:
    entry, bundle = load_forecast(project)
    replay = backtest(bundle['evaluation_model'], bundle['values'], bundle['years'], bundle['validation_end'], len(bundle['values']), bundle['mase_scale'])
    if replay != entry['metrics']:
        raise ValueError('Replayed evaluation differs from registered metrics.')
    return {'model_id': entry['model_id'], 'artifact_valid': True, 'evaluation_reproduced': True, 'metrics': replay}
