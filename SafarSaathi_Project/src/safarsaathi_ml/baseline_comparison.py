"""Like-for-like historical comparisons. Never register or select using test scores."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np

from .config import settings
from .forecasting import AnnualForecaster, evaluate_forecast, load_forecast, metrics
from .pipeline import sha256, utc_now
from .readiness import load_arrivals

METHODS = ('persistence', 'expanding_drift', 'historical_mean', 'expanding_ridge', 'registered_fixed_drift')


def predict_at_origin(method, history, horizon, saved_model):
    """Only a prefix is accepted; callers must never pass future targets."""
    history = np.asarray(history, dtype=float)
    if method == 'persistence':
        return [float(history[-1])] * horizon
    if method == 'historical_mean':
        return [float(history.mean())] * horizon
    if method == 'registered_fixed_drift':
        return saved_model.forecast(history, horizon)
    if method in {'expanding_drift', 'expanding_ridge'}:
        return AnnualForecaster('drift' if method == 'expanding_drift' else 'ridge').fit(history).forecast(history, horizon)
    raise ValueError('Unknown baseline method.')


def compare(values, years, train_end, validation_end, saved_model):
    values, years = np.asarray(values, dtype=float), np.asarray(years, dtype=int)
    if len(values) != len(years) or not 8 <= train_end < validation_end < len(values) or not np.diff(years).tolist() == [1] * (len(years) - 1):
        raise ValueError('Contiguous annual data and ordered chronological split boundaries are required.')
    scale = float(np.abs(np.diff(values[:train_end])).mean())
    result = {}
    for method in METHODS:
        rows = []
        for origin in range(validation_end, len(values)):
            predictions = predict_at_origin(method, values[:origin], min(3, len(values) - origin), saved_model)
            for h, prediction in enumerate(predictions, 1):
                rows.append({'forecast_origin_year': int(years[origin - 1]), 'target_year': int(years[origin + h - 1]),
                             'horizon': h, 'actual': float(values[origin + h - 1]), 'prediction': prediction})
        horizons = {}
        for h in (1, 2, 3):
            sample = [r for r in rows if r['horizon'] == h]
            horizons[str(h)] = {**metrics([r['actual'] for r in sample], [r['prediction'] for r in sample], scale),
                                'horizon': h, 'origins': [r['forecast_origin_year'] for r in sample],
                                'target_years': [r['target_year'] for r in sample]}
        result[method] = {'by_horizon': horizons, 'predictions': rows,
                          'fit_policy': 'Frozen registered evaluation estimator fitted through validation end; actual past history at each origin.' if method == 'registered_fixed_drift' else 'Fit/compute from expanding observed prefix strictly before each forecast origin.'}
    baseline = result['persistence']['by_horizon']
    for method in result:
        for h, score in result[method]['by_horizon'].items():
            score['differences_vs_persistence'] = {
                metric: {'absolute': score[metric] - baseline[h][metric] if score[metric] is not None and baseline[h][metric] is not None else None,
                         'relative': (score[metric] - baseline[h][metric]) / baseline[h][metric] if score[metric] is not None and baseline[h][metric] not in (None, 0) else None}
                for metric in ('MAE', 'RMSE', 'MASE', 'WAPE')}
    return {'mase_denominator': scale, 'mase_denominator_years': years[:train_end].tolist(), 'methods': result}


def build_comparison(project: Path, raw: Path):
    entry, bundle = load_forecast(project)
    observed, profile = load_arrivals(raw)
    if observed.year.tolist() != bundle['years'] or observed.arrivals.tolist() != bundle['values']:
        raise ValueError('Current source differs from the registered model history; investigate before comparison.')
    replay = evaluate_forecast(project)
    comparison = compare(bundle['values'], bundle['years'], bundle['train_end'], bundle['validation_end'], bundle['evaluation_model'])
    fixed = comparison['methods']['registered_fixed_drift']['by_horizon']
    for h in ('1', '2', '3'):
        for name in ('MAE', 'RMSE', 'MASE', 'WAPE', 'n'):
            if fixed[h][name] != replay['metrics']['by_horizon'][h][name]:
                raise ValueError('Independent sample alignment did not reproduce registered scores.')
    # Validation-only comparison is reported separately. The registered snapshot stays unchanged.
    validation = {}
    for method in METHODS[:-1]:
        predictions = [predict_at_origin(method, bundle['values'][:i], 1, None)[0]
                       for i in range(bundle['train_end'], bundle['validation_end'])]
        validation[method] = metrics(bundle['values'][bundle['train_end']:bundle['validation_end']], predictions, comparison['mase_denominator'])
    path = raw / profile['path']
    return {'generated_at': utc_now(), **comparison, 'validation_one_year': validation,
            'source': {**profile, 'bytes': path.stat().st_size, 'repository_relative_path': path.relative_to(project.parent).as_posix()},
            'artifact': {'path': entry['artifact'], 'sha256': sha256(project / entry['artifact']), 'model_version': entry['model_version']},
            'split': entry['split'], 'selection_policy': 'No replacement selected. This is a post-hoc audit of a known test set, not a new independent model-selection experiment.',
            'decision': 'Retain existing registered artifact; classify tourism as TRAINED_BUT_EXPERIMENTAL. Small pre-2020 sample and structural change prevent reliable operational superiority claims.',
            'metric_definitions': {'MAE': 'mean absolute error in arrivals', 'RMSE': 'root mean squared error in arrivals',
                'MASE': 'MAE divided by mean absolute one-year differences of the unchanged 1995–2009 training block; same denominator for every method/horizon.',
                'WAPE': 'sum absolute error / sum absolute actual; fraction. Individual zero actuals allowed; all-zero denominator gives null.',
                'differences': 'method minus persistence; relative differences are fractions; negative means lower error.'},
            'mase_resolution': 'The original model and persistence scores use identical test targets/origins and the same training-scale denominator. MASE >1 compares to smaller pre-2010 annual changes, not to 2015–2019 persistence MAE. There is no arithmetic contradiction.',
            'seasonal_naive': {'status': 'NOT_APPLICABLE', 'reason': 'Annual totals contain no identifiable within-year seasonality; no defensible multi-year seasonal period established.'},
            'limitations': entry['limitations'] + ['Overlapping multi-year forecasts and 5/4/3 observations are not independent evidence of generalization.',
                'Expanding baselines refit at each origin; the original evaluation snapshot intentionally stays fixed through 2014. Both receive identical past observed histories.',
                'No future-known external features are used. Data-vintage revision leakage cannot be ruled out without historical publication vintages.']}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    project = settings().project_root
    result = build_comparison(project, project.parent / 'SafarSaathi_Datasets/raw')
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open('x', encoding='utf-8') as handle:
        json.dump(result, handle, indent=2, allow_nan=False)
    print(json.dumps({name: item['by_horizon']['1'] for name, item in result['methods'].items()}, indent=2))


if __name__ == '__main__':
    main()
