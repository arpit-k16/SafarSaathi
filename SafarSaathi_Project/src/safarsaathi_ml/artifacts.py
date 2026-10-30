"""Trusted registered-artifact loading; no client paths or training-data access."""
import json
from functools import lru_cache
from threading import RLock

import joblib

from .pipeline import sha256
from .registry import resolve_artifact_path


class ArtifactUnavailable(ValueError):
    pass


_load_lock = RLock()


@lru_cache(maxsize=16)
def _deserialize(path, digest):
    # Calls remain serialized so concurrent first requests do not deserialize twice.
    return joblib.load(path)


def load_artifact(project, entry):
    try:
        path = resolve_artifact_path(project, entry['artifact'])
        expected = entry.get('artifact_sha256')
        integrity = project / 'models/artifact_integrity.json'
        if integrity.exists():
            manifest = json.loads(integrity.read_text(encoding='utf-8'))
            pinned = manifest['artifacts'].get(entry['artifact'])
            if pinned and expected and pinned != expected:
                raise ArtifactUnavailable('Saved artifact checksum metadata conflicts.')
            expected = expected or pinned
        actual = sha256(path)
        if expected and actual != expected:
            raise ArtifactUnavailable('Saved artifact checksum validation failed.')
        # Always verify bytes before a cache hit. Corrupt/replaced artifacts cannot
        # continue to serve stale cached models, even with unchanged timestamps.
        with _load_lock:
            return _deserialize(str(path), actual)
    except ArtifactUnavailable:
        raise
    except Exception as exc:
        raise ArtifactUnavailable('Saved model artifact is unavailable.') from exc
