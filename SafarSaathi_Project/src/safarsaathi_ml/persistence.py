"""Read-only model registry access for runtime services."""
from __future__ import annotations

from pathlib import Path

from .config import settings
from .registry import load_registry


def registry_path() -> Path:
    return settings().models_root / "registry.json"


def list_models() -> list[dict]:
    return load_registry(registry_path())


def model_metadata(model_id: str) -> dict | None:
    for model in list_models():
        if model.get("model_id") == model_id:
            return model
    return None
