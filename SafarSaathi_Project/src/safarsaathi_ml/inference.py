"""Stable inference boundary for application code; it never retrains a model."""
from __future__ import annotations

from .artifacts import ArtifactUnavailable, load_artifact

from .persistence import model_metadata
from .registry import RegistryError, resolve_artifact_path


def classify_reviews(model_id: str, reviews: list[str]) -> dict[str, object]:
    """Validate input and return source-label predictions from a persisted pipeline."""
    if not isinstance(model_id, str) or not isinstance(reviews, list) or not reviews or len(reviews) > 100:
        raise ValueError("A known model_id and 1 to 100 reviews are required.")
    if not all(isinstance(review, str) and review.strip() for review in reviews):
        raise ValueError("Every review must be a non-empty string.")
    metadata = model_metadata(model_id)
    if metadata is None:
        raise ValueError("Requested model is not available.")
    if metadata.get('task') != 'review classification':
        raise ValueError('Requested model does not support review classification.')
    from .config import settings
    try:
        artifact = resolve_artifact_path(settings().project_root, metadata["artifact"])
    except RegistryError as exc:
        raise ValueError("Saved model artifact is unavailable for inference.") from exc
    try:
        prediction = load_artifact(settings().project_root, metadata).predict(reviews).tolist()
        if len(prediction) != len(reviews) or not all(isinstance(label, str) and label for label in prediction):
            raise ArtifactUnavailable('Saved model produced an invalid response.')
    except Exception as exc:
        raise ArtifactUnavailable("Saved model artifact could not be loaded for inference.") from exc
    return {"model_id": model_id, "predictions": prediction, "status": "ok",
            'model_version': metadata.get('model_version', model_id), 'limitations': metadata.get('limitations', '')}
