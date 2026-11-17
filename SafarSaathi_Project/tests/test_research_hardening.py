import numpy as np
import pytest
from safarsaathi_ml import flood_baseline as flood
from safarsaathi_ml.artifacts import ArtifactUnavailable
from safarsaathi_ml.http_api import predict_capability
from safarsaathi_ml.integration_services import capacity_scenario


@pytest.mark.parametrize('mode', ['nan', 'negative', 'overflow', 'shape', 'sum', 'classes', 'threshold'])
def test_malformed_segmentation_model_outputs_unavailable(monkeypatch, tmp_path, mode):
    class BadModel:
        classes_ = np.array([0, 1]) if mode != 'classes' else np.array([3, 4])
        def predict_proba(self, features):
            rows = np.tile([.5, .5], (len(features), 1))
            if mode == 'nan': rows[0, 0] = np.nan
            if mode == 'negative': rows[0] = [-.1, 1.1]
            if mode == 'overflow': rows[0, 1] = np.inf
            if mode == 'shape': return rows[:1]
            if mode == 'sum': rows[0] = [.1, .1]
            return rows
    bundle = {'model': BadModel(), 'threshold': 5 if mode == 'threshold' else .3}
    monkeypatch.setattr(flood, 'load_flood', lambda _: ({'model_id': 'flood_segmentation_model'}, bundle))
    body = {'image': np.zeros((128, 128, 2)).tolist(), 'metadata': {'source_format': 'STURM-S1-preprocessed', 'geo_tags': {}}}
    with pytest.raises(ArtifactUnavailable): flood.segment(tmp_path, body)
    status, response = predict_capability('flood_segmentation', body)
    assert status == 503 and response['status'] == 'unavailable'


def test_extreme_scenario_integer_is_validation_error_not_overflow():
    with pytest.raises(ValueError):
        capacity_scenario({'baseline_visitors': 10**1000, 'capacity': 100,
                           'demand_change_percent': 0, 'available_capacity_percent': 100})


def test_unrepresentable_utilization_is_validation_error_not_invalid_json():
    with pytest.raises(ValueError, match='numerical range'):
        capacity_scenario({'baseline_visitors': 1e9, 'capacity': 100,
                           'demand_change_percent': 0, 'available_capacity_percent': 5e-324})
