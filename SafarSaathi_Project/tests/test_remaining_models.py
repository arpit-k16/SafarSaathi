"""Synthetic fixtures only; these tests never train a project production artifact."""
import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from safarsaathi_ml.forecasting import AnnualForecaster, evaluate_forecast, features, forecast, load_forecast, train_forecast
from safarsaathi_ml.readiness import ARRIVALS, data_readiness, load_arrivals, validate_flood_pair, validate_observed_table, validate_group_splits
from safarsaathi_ml.registry import load_registry, register_model
from safarsaathi_ml.http_api import predict_capability


def fixture_raw(tmp_path, count=30):
    raw = tmp_path / 'raw'; path = raw / ARRIVALS; path.parent.mkdir(parents=True)
    rows = [{'indicator': {'id': 'ST.INT.ARVL'}, 'countryiso3code': 'IND', 'date': str(1990 + i), 'value': 1000 + i * 50} for i in range(count)]
    path.write_text(json.dumps([{}, rows]), encoding='utf-8')
    return raw


def test_missing_discovery_and_training(tmp_path):
    report = data_readiness(tmp_path, tmp_path / 'missing', write=False)
    assert report['models']['tourism_demand']['readiness'] == 'UNAVAILABLE'
    assert report['models']['flood_segmentation']['readiness'] == 'UNAVAILABLE'
    with pytest.raises(ValueError, match='missing'):
        load_arrivals(tmp_path / 'missing')


@pytest.mark.parametrize('defect', ['duplicate', 'gap', 'negative', 'missing', 'wrong_indicator', 'nonfinite'])
def test_invalid_tourism_targets(tmp_path, defect):
    raw = fixture_raw(tmp_path); path = raw / ARRIVALS
    payload = json.loads(path.read_text()); rows = payload[1]
    if defect == 'duplicate': rows.append(rows[0])
    elif defect == 'gap': rows[5]['value'] = None
    elif defect == 'negative': rows[5]['value'] = -1
    elif defect == 'nonfinite': rows[5]['value'] = float('inf')
    elif defect == 'missing':
        for row in rows: row['value'] = None
    else: rows[0]['indicator']['id'] = 'not_arrivals'
    path.write_text(json.dumps(payload))
    with pytest.raises(ValueError): load_arrivals(raw)


def test_past_only_features_and_recursive_predictions():
    history = np.arange(20, dtype=float) + 100
    original = history.copy()
    assert np.array_equal(features(history[:10]), features(original[:10]))
    history[10:] = 999999
    assert np.array_equal(features(history[:10]), features(original[:10]))
    for method in ('naive', 'drift', 'ridge'):
        a = AnnualForecaster(method).fit(original[:10])
        b = AnnualForecaster(method).fit(original[:10])
        assert a.forecast(original[:10], 3) == b.forecast(original[:10], 3)


def test_training_reload_evaluation_registry_preservation(tmp_path):
    raw = fixture_raw(tmp_path); models = tmp_path / 'models'; models.mkdir()
    old = models / 'old.bin'; old.write_bytes(b'prior fixture')
    entry = {'model_id': 'existing', 'task': 'fixture', 'artifact': 'models/old.bin', 'persistence_test_passed': True}
    register_model(models / 'registry.json', entry)
    metadata = train_forecast(tmp_path, raw)
    assert metadata['training_completed']
    assert metadata['split']['train_years'][-1] < metadata['split']['validation_years'][0]
    assert metadata['split']['validation_years'][-1] < metadata['split']['test_years'][0]
    assert evaluate_forecast(tmp_path)['evaluation_reproduced']
    assert forecast(tmp_path, 'IND', 3)['forecasts'][-1]['year'] == 2022
    assert load_registry(models / 'registry.json')[0] == entry
    with pytest.raises(ValueError, match='already registered'): train_forecast(tmp_path, raw)
    artifact = tmp_path / metadata['artifact']; artifact.write_bytes(b'corrupt')
    with pytest.raises(ValueError, match='checksum'): load_forecast(tmp_path)
    artifact.unlink()
    with pytest.raises(Exception): load_forecast(tmp_path)


@pytest.mark.parametrize('destination,horizon', [('UK', 1), ('IND', 0), ('IND', True), ('IND', 4), ('IND', '1')])
def test_inference_schema(tmp_path, destination, horizon):
    with pytest.raises(ValueError): forecast(tmp_path, destination, horizon)


@pytest.mark.parametrize('task', ['disaster_risk', 'destination_stress'])
def test_future_observed_table_validation(task):
    frame = pd.DataFrame({'region_id': ['A'], 'date': ['2020-01-01'], 'target': [1], 'available_at': ['2019-12-01']})
    assert validate_observed_table(frame, task).target.tolist() == [1]
    for invalid in (frame.drop(columns='target'), pd.concat([frame, frame]), frame.assign(target=np.nan)):
        with pytest.raises(ValueError): validate_observed_table(invalid, task)
    with pytest.raises(ValueError, match='availability'):
        validate_observed_table(frame.assign(available_at='2021-01-01'), task)


def test_flood_pair_alignment_and_labels():
    image, mask = np.zeros((4, 4, 3)), np.zeros((4, 4), dtype=int)
    meta = {'crs': 'EPSG:4326', 'transform': [1, 0, 0, 0, -1, 0], 'scene_id': 'scene-A', 'event_id': 'event-A'}
    assert validate_flood_pair(image, mask, meta, meta)['flood_fraction'] == 0
    with pytest.raises(ValueError): validate_flood_pair(image, mask + 2, meta, meta)
    with pytest.raises(ValueError): validate_flood_pair(image, mask[:2], meta, meta)
    with pytest.raises(ValueError): validate_flood_pair(image, mask, meta, {**meta, 'event_id': 'event-B'})
    assert validate_group_splits(['a'], ['b'], ['c'])
    with pytest.raises(ValueError): validate_group_splits(['a'], ['b'], ['a'])


def test_api_schema_and_unavailable_tasks():
    for body in (None, {}, {'destination': 'IND', 'horizon': True}, {'destination': 'IND', 'horizon': 1, 'path': '../x'}):
        assert predict_capability('tourism_demand', body)[0] == 422
    for task in ('disaster_risk', 'flood_segmentation', 'destination_stress'):
        status, response = predict_capability(task, {})
        if task=='flood_segmentation' and status==422:
            from safarsaathi_ml.flood_baseline import load_flood
            from safarsaathi_ml.config import settings
            assert load_flood(settings().project_root)[0]['training_completed']
        else:
            assert status == 503 and response['status'] == 'not_trained'
    assert predict_capability('unknown', {})[0] == 404
