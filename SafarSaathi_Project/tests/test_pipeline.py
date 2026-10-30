import json
from pathlib import Path

from safarsaathi_ml.pipeline import find_raw_roots, predict_nlp


def test_raw_roots_are_external_to_outputs():
    assert find_raw_roots()
    assert all("outputs" not in str(path).lower() for path in find_raw_roots())


def test_registry_models_can_be_reloaded_if_present():
    project = Path(__file__).resolve().parents[1]
    registry = project / "models" / "registry.json"
    if registry.exists():
        for item in json.loads(registry.read_text(encoding="utf-8")):
            assert item["persistence_test_passed"] is True
            if item['task'] == 'review classification':
                assert predict_nlp(item["model_id"], ["A clean technical smoke test."])
