"""Validated, atomic, single-writer model-registry operations."""
from __future__ import annotations

import json
import os
import tempfile
import time
from contextlib import contextmanager
from pathlib import Path
from pathlib import PurePosixPath
from typing import Any, Iterator


class RegistryError(RuntimeError):
    pass


def normalize_artifact_path(value: object) -> str:
    """Return a portable project-relative artifact path or raise a safe error."""
    if not isinstance(value, str) or not value.strip():
        raise RegistryError("Model artifact path must be a non-empty string.")
    candidate = value.replace("\\", "/")
    if ':' in candidate or any(ord(char) < 32 for char in candidate):
        raise RegistryError('Model artifact path contains invalid characters.')
    if candidate.startswith("/") or (len(candidate) > 1 and candidate[1] == ":"):
        raise RegistryError("Model artifact path must be project-relative.")
    path = PurePosixPath(candidate)
    if any(part in {"", ".", ".."} for part in path.parts):
        raise RegistryError("Model artifact path contains invalid traversal.")
    return path.as_posix()


def resolve_artifact_path(project_root: Path, value: object) -> Path:
    normalized = normalize_artifact_path(value)
    resolved = (project_root / Path(*PurePosixPath(normalized).parts)).resolve()
    if project_root.resolve() not in resolved.parents:
        raise RegistryError("Model artifact path escapes the project root.")
    return resolved


def _validate_entry(entry: Any, models_root: Path, verify_artifacts: bool = True) -> dict[str, Any]:
    if not isinstance(entry, dict):
        raise RegistryError("Registry entries must be JSON objects.")
    required = ("model_id", "task", "artifact", "persistence_test_passed")
    missing = [field for field in required if field not in entry]
    if missing or not isinstance(entry.get("model_id"), str) or not entry["model_id"].strip():
        raise RegistryError(f"Invalid registry entry: missing/invalid {missing or 'model_id'}.")
    if entry['persistence_test_passed'] is not True or not isinstance(entry['task'], str) or not entry['task'].strip():
        raise RegistryError('Registry requires an explicit successful persistence check and task.')
    normalized = dict(entry)
    normalized["artifact"] = normalize_artifact_path(entry["artifact"])
    artifact = resolve_artifact_path(models_root.parent, normalized["artifact"])
    if verify_artifacts and not artifact.is_file():
        raise RegistryError(f"Model {entry['model_id']} points to a missing artifact.")
    return normalized


def load_registry(path: Path, verify_artifacts: bool = True) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    try:
        parsed = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError, OSError) as exc:
        raise RegistryError(f"Registry is malformed JSON: {path.name}") from exc
    if not isinstance(parsed, list):
        raise RegistryError("Registry root must be a JSON list.")
    entries = [_validate_entry(entry, path.parent, verify_artifacts) for entry in parsed]
    ids = [entry["model_id"] for entry in entries]
    if len(ids) != len(set(ids)):
        raise RegistryError("Registry contains duplicate model_id values.")
    return entries


@contextmanager
def registry_lock(path: Path, timeout_seconds: float = 10.0) -> Iterator[None]:
    lock = path.with_suffix(path.suffix + ".lock")
    deadline = time.monotonic() + timeout_seconds
    while True:
        try:
            descriptor = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            os.write(descriptor, str(os.getpid()).encode())
            os.close(descriptor)
            break
        except FileExistsError:
            if time.monotonic() >= deadline:
                raise RegistryError("Registry is locked by another writer; retry after that run completes.")
            time.sleep(0.05)
    try:
        yield
    finally:
        lock.unlink(missing_ok=True)


def atomic_write_registry(path: Path, entries: list[dict[str, Any]]) -> None:
    for entry in entries:
        _validate_entry(entry, path.parent)
    ids = [entry.get('model_id') for entry in entries if isinstance(entry, dict)]
    if len(ids) != len(set(ids)):
        raise RegistryError('Registry contains duplicate model_id values.')
    handle = tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent, prefix=".registry-", suffix=".tmp", delete=False)
    try:
        json.dump(entries, handle, indent=2)
        handle.flush(); os.fsync(handle.fileno()); handle.close()
        os.replace(handle.name, path)
    except Exception:
        handle.close()
        Path(handle.name).unlink(missing_ok=True)
        raise


def register_model(path: Path, entry: dict[str, Any]) -> list[dict[str, Any]]:
    with registry_lock(path):
        existing = load_registry(path)
        _validate_entry(entry, path.parent)
        if any(item["model_id"] == entry["model_id"] for item in existing):
            raise RegistryError(f"Model id already registered: {entry['model_id']}")
        updated = [*existing, entry]
        atomic_write_registry(path, updated)
        return updated
