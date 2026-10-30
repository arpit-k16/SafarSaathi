import json
from pathlib import Path

import pytest
import pandas as pd

from safarsaathi_ml.registry import RegistryError, atomic_write_registry, load_registry, normalize_artifact_path, register_model


def entry(model_id: str = "nlp-test") -> dict:
    return {"model_id": model_id, "task": "review classification", "artifact": f"models/nlp/{model_id}/pipeline.joblib", "persistence_test_passed": True}


def prepare(tmp_path: Path, model_id: str = "nlp-test") -> Path:
    artifact = tmp_path / "models" / "nlp" / model_id / "pipeline.joblib"
    artifact.parent.mkdir(parents=True); artifact.write_bytes(b"fixture")
    return tmp_path / "models" / "registry.json"


def test_existing_and_unrelated_entries_survive_registration(tmp_path):
    registry = prepare(tmp_path, "nlp-old"); prepare(tmp_path, "hazard-old")
    atomic_write_registry(registry, [entry("nlp-old"), entry("hazard-old")])
    prepare(tmp_path, "nlp-new")
    register_model(registry, entry("nlp-new"))
    assert {item["model_id"] for item in load_registry(registry)} == {"nlp-old", "hazard-old", "nlp-new"}


def test_corrupt_registry_is_not_silently_replaced(tmp_path):
    registry = prepare(tmp_path); registry.write_text("not json", encoding="utf-8")
    with pytest.raises(RegistryError, match="malformed"):
        register_model(registry, entry("new"))
    assert registry.read_text(encoding="utf-8") == "not json"


def test_missing_artifact_is_explicit(tmp_path):
    registry = tmp_path / "models" / "registry.json"; registry.parent.mkdir()
    registry.write_text(json.dumps([entry()]), encoding="utf-8")
    with pytest.raises(RegistryError, match="missing artifact"):
        load_registry(registry)


def test_failed_atomic_update_keeps_old_registry(tmp_path, monkeypatch):
    registry = prepare(tmp_path); atomic_write_registry(registry, [entry()])
    original = registry.read_text(encoding="utf-8")
    import safarsaathi_ml.registry as module
    monkeypatch.setattr(module.os, "replace", lambda *_: (_ for _ in ()).throw(OSError("disk error")))
    with pytest.raises(OSError):
        atomic_write_registry(registry, [entry()])
    assert registry.read_text(encoding="utf-8") == original


def test_skipped_training_does_not_erase_registry(tmp_path, monkeypatch):
    import safarsaathi_ml.pipeline as pipeline
    registry = prepare(tmp_path, "nlp-old"); atomic_write_registry(registry, [entry("nlp-old")])
    monkeypatch.setattr(pipeline, "PROJECT", tmp_path)
    monkeypatch.setattr(pipeline, "OUTPUTS", tmp_path / "outputs")
    monkeypatch.setattr(pipeline, "discover", lambda **_: pd.DataFrame({"category": []}))
    monkeypatch.setattr(pipeline, "profile_tabular_files", lambda _: [])
    monkeypatch.setattr(pipeline, "build_weather_summary", lambda _: {"status": "not_found"})
    monkeypatch.setattr(pipeline, "train_nlp", lambda _: {"status": "skipped", "reason": "fixture"})
    monkeypatch.setattr(pipeline, "find_raw_roots", lambda: [])
    pipeline.run()
    assert [item["model_id"] for item in load_registry(registry)] == ["nlp-old"]


def test_windows_legacy_path_is_normalized_and_traversal_is_rejected(tmp_path):
    registry = prepare(tmp_path)
    legacy = entry(); legacy["artifact"] = "models\\nlp\\nlp-test\\pipeline.joblib"
    atomic_write_registry(registry, [legacy])
    assert load_registry(registry)[0]["artifact"] == "models/nlp/nlp-test/pipeline.joblib"
    with pytest.raises(RegistryError):
        normalize_artifact_path("models/../secret.joblib")
    with pytest.raises(RegistryError):
        normalize_artifact_path("C:\\models\\pipeline.joblib")
