"""Compatibility exports for the dependency-light HTTP integration boundary."""
from .http_api import Handler, classify, health, models, serve

__all__ = ["Handler", "classify", "health", "models", "serve"]
