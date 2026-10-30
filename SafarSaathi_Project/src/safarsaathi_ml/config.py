"""Runtime path resolution; no machine-specific paths are stored in code."""
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    project_root: Path
    models_root: Path
    outputs_root: Path


def settings() -> Settings:
    project_root = Path(__file__).resolve().parents[2]
    return Settings(project_root, project_root / "models", project_root / "outputs")
