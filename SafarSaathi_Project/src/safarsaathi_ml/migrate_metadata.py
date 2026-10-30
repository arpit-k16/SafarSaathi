"""One-time portability migration for already-persisted model metadata."""
from __future__ import annotations

import json
from pathlib import Path

from .config import settings
from .pipeline import sha256
from .registry import atomic_write_registry, load_registry
from .registry import normalize_artifact_path


def migrate() -> None:
    cfg = settings(); registry_file = cfg.models_root / "registry.json"
    entries = load_registry(registry_file)
    updated = []
    for entry in entries:
        metadata_file = cfg.project_root / Path(entry["artifact"]).parent / "metadata.json"
        metadata = json.loads(metadata_file.read_text(encoding="utf-8"))
        metadata["artifact"] = normalize_artifact_path(metadata["artifact"])
        source = metadata.pop("source", None)
        if source:
            source_path = Path(source)
            relative = source_path.relative_to(cfg.project_root.parent) if source_path.is_relative_to(cfg.project_root.parent) else None
            metadata["dataset_provenance"] = {"logical_name": "labelled_hotel_reviews", "source_description": "Repository-provided hotel review dataset", "repository_relative_path": str(relative) if relative else None, "external_to_project": not source_path.is_relative_to(cfg.project_root), "format": source_path.suffix.lower(), "bytes": source_path.stat().st_size if source_path.exists() else None, "sha256": sha256(source_path) if source_path.exists() else None, "label_definition": metadata.get("label_column")}
        metadata_file.write_text(json.dumps(metadata, indent=2), encoding="utf-8")
        updated.append(metadata)
    atomic_write_registry(registry_file, updated)


if __name__ == "__main__":
    migrate()
