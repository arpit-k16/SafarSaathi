"""Offline, rerunnable discovery, preprocessing, training and inference pipeline.

The pipeline never writes below a discovered raw-data directory.  A trained
model is produced only if a labelled review table can be unambiguously found.
Tourism PDFs and unlabelled imagery are inventoried, not converted into claims.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import platform
import re
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd
import sklearn
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix, f1_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline

from .registry import load_registry, register_model

SEED = 20261024
PROJECT = Path(__file__).resolve().parents[2]
ROOT = PROJECT.parent
OUTPUTS = PROJECT / "outputs"
RAW_CANDIDATES = (ROOT / "SafarSaathi_Datasets" / "raw", PROJECT / "data" / "raw_v2")


def inventory_path(row: Any) -> Path:
    return ROOT / Path(row.raw_root) / Path(row.relative_path)


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def find_raw_roots() -> list[Path]:
    return [path.resolve() for path in RAW_CANDIDATES if path.is_dir()]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def discover(checksum_mode: str = "fast", hash_max_bytes: int = 50_000_000, raw_roots: tuple[Path, ...] | None = None) -> pd.DataFrame:
    """Inventory immutable raw files. Full mode hashes every readable file."""
    if checksum_mode not in {"fast", "full", "none"}:
        raise ValueError("checksum_mode must be fast, full, or none")
    rows: list[dict[str, Any]] = []
    for root in (raw_roots if raw_roots is not None else tuple(find_raw_roots())):
        for path in root.rglob("*"):
            if not path.is_file():
                continue
            relative = path.relative_to(root)
            category = relative.parts[0] if len(relative.parts) > 1 else "root"
            try:
                stat = path.stat()
                requested = checksum_mode == "full" or (checksum_mode == "fast" and stat.st_size <= hash_max_bytes)
                digest = sha256(path) if requested else None
                status = "verified" if requested else ("skipped_size_limit" if checksum_mode == "fast" else "not_requested")
                reason = None if requested else (f"size exceeds fast-audit limit of {hash_max_bytes} bytes" if checksum_mode == "fast" else "checksum policy disabled")
            except OSError as exc:
                stat, digest, status, reason = None, None, "unreadable", f"{type(exc).__name__}: {exc}"
            root_label = str(root.relative_to(ROOT)) if root.is_relative_to(ROOT) else root.name
            rows.append({"raw_root": root_label, "relative_path": str(relative), "category": category,
                         "extension": path.suffix.lower() or "[none]", "bytes": stat.st_size if stat else None,
                         "modified_utc": datetime.fromtimestamp(stat.st_mtime, timezone.utc).isoformat() if stat else None,
                         "hash_algorithm": "sha256", "sha256": digest, "hash_status": status, "hash_reason": reason})
    return pd.DataFrame(rows).sort_values(["raw_root", "relative_path"]).reset_index(drop=True)


def profile_tabular_files(inventory: pd.DataFrame) -> list[dict[str, Any]]:
    profiles: list[dict[str, Any]] = []
    for row in inventory[inventory.extension.isin([".csv", ".parquet"])].itertuples():
        path = inventory_path(row)
        try:
            frame = pd.read_csv(path, nrows=5000) if path.suffix == ".csv" else pd.read_parquet(path)
            profiles.append({"path": str(path), "rows_sampled": len(frame), "columns": list(frame.columns),
                             "dtypes": {k: str(v) for k, v in frame.dtypes.items()},
                             "missing": frame.isna().sum().to_dict(), "duplicates": int(frame.duplicated().sum())})
        except Exception as exc:  # A report must record unreadable sources, not hide them.
            profiles.append({"path": str(path), "error": f"{type(exc).__name__}: {exc}"})
    return profiles


def build_weather_summary(inventory: pd.DataFrame) -> dict[str, Any]:
    """Validate NASA POWER JSON structure without joining it to tourism data."""
    records: list[dict[str, Any]] = []
    for row in inventory[inventory.category.isin(["weather_nasa_power", "weather_power"])].itertuples():
        if row.extension != ".json":
            continue
        path = inventory_path(row)
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            parameters = payload.get("properties", {}).get("parameter", {})
            if not isinstance(parameters, dict) or not parameters:
                continue
            first = next(iter(parameters.values()))
            values = pd.to_numeric(pd.Series(first.values()), errors="coerce") if isinstance(first, dict) else pd.Series(dtype=float)
            records.append({"source_file": str(path), "parameter_count": len(parameters), "observations": len(values),
                            "missing_first_parameter": int(values.isna().sum()), "parameter_names": sorted(parameters)})
        except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
            records.append({"source_file": str(path), "error": f"{type(exc).__name__}: {exc}"})
    return {"status": "validated" if records else "not_found", "files": records,
            "limitation": "Weather is not joined to tourism because the currently auditable tourism sources are report documents, not an extracted target table."}


def find_labelled_reviews(inventory: pd.DataFrame) -> tuple[Path, str, str] | None:
    text_names = {"review", "text", "content", "comment", "review_text"}
    label_names = {"label", "sentiment", "rating", "category", "class"}
    candidates = inventory[(inventory.category == "reviews") & inventory.extension.isin([".csv", ".parquet"])]
    for row in candidates.itertuples():
        path = inventory_path(row)
        try:
            sample = pd.read_csv(path, nrows=10) if path.suffix == ".csv" else pd.read_parquet(path)
            lookup = {str(column).strip().lower(): str(column) for column in sample.columns}
            text = next((lookup[name] for name in text_names if name in lookup), None)
            label = next((lookup[name] for name in label_names if name in lookup), None)
            if text and label:
                return path, text, label
        except Exception:
            continue
    return None


def train_nlp(inventory: pd.DataFrame) -> dict[str, Any]:
    found = find_labelled_reviews(inventory)
    if found is None:
        return {"status": "skipped", "reason": "No review file with unambiguous text and label columns was found; no pseudo-labels were created."}
    path, text_column, label_column = found
    frame = pd.read_csv(path) if path.suffix == ".csv" else pd.read_parquet(path)
    frame = frame[[text_column, label_column]].dropna().drop_duplicates().copy()
    frame[text_column] = frame[text_column].astype(str).str.strip()
    frame = frame[frame[text_column].str.len() > 0]
    if frame[label_column].nunique() < 2 or len(frame) < 40:
        return {"status": "skipped", "reason": "Review labels do not support a supervised split.", "source": str(path)}
    train, test = train_test_split(frame, test_size=0.2, random_state=SEED, stratify=frame[label_column])
    model = Pipeline([("tfidf", TfidfVectorizer(ngram_range=(1, 2), min_df=2, max_features=30_000)),
                      ("classifier", LogisticRegression(max_iter=1000, random_state=SEED))])
    model.fit(train[text_column], train[label_column])
    predictions = model.predict(test[text_column])
    majority_label = train[label_column].mode().iloc[0]
    metrics = {"accuracy": float(accuracy_score(test[label_column], predictions)),
               "macro_f1": float(f1_score(test[label_column], predictions, average="macro")),
               "weighted_f1": float(f1_score(test[label_column], predictions, average="weighted")),
               "majority_baseline_accuracy": float(accuracy_score(test[label_column], [majority_label] * len(test))),
               "class_distribution": {"source": frame[label_column].value_counts().to_dict(), "train": train[label_column].value_counts().to_dict(), "test": test[label_column].value_counts().to_dict()},
               "classification_report": classification_report(test[label_column], predictions, output_dict=True, zero_division=0)}
    version = f"nlp-{datetime.now(timezone.utc):%Y%m%dT%H%M%SZ}"
    artifact_dir = PROJECT / "models" / "nlp" / version
    artifact_dir.mkdir(parents=True, exist_ok=False)
    artifact = artifact_dir / "pipeline.joblib"
    joblib.dump(model, artifact)
    sample_prediction = model.predict(test.iloc[:1][text_column]).tolist()
    reloaded_prediction = joblib.load(artifact).predict(test.iloc[:1][text_column]).tolist()
    source_relative = path.relative_to(ROOT) if path.is_relative_to(ROOT) else None
    metadata = {"model_id": version, "task": "review classification", "trained_at": utc_now(), "random_seed": SEED,
                "dataset_provenance": {"logical_name": "labelled_hotel_reviews", "source_description": "Repository-provided hotel review dataset", "repository_relative_path": str(source_relative) if source_relative else None, "external_to_project": not path.is_relative_to(PROJECT), "format": path.suffix.lower(), "bytes": path.stat().st_size, "sha256": sha256(path), "source_rows": len(pd.read_csv(path) if path.suffix == '.csv' else pd.read_parquet(path)), "rows_used": len(frame)},
                "text_column": text_column, "label_column": label_column,
                "train_rows": len(train), "test_rows": len(test), "metrics": metrics,
                "software_versions": {"python": sys.version, "pandas": pd.__version__, "scikit_learn": sklearn.__version__, "joblib": joblib.__version__},
                "artifact": str(artifact.relative_to(PROJECT)), "persistence_test_passed": sample_prediction == reloaded_prediction,
                "limitations": "This classifies the labels supplied by the source dataset; it is not destination-specific sentiment unless source provenance establishes that scope."}
    (artifact_dir / "metadata.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    (artifact_dir / "feature_schema.json").write_text(json.dumps({"input": {"reviews": "list[str]"}, "output": "source-defined label", "text_column": text_column, "label_column": label_column}, indent=2), encoding="utf-8")
    pd.DataFrame({"text": test[text_column], "actual": test[label_column], "prediction": predictions}).to_csv(OUTPUTS / "predictions" / "nlp_test.csv", index=False)
    return {"status": "trained", **metadata}


def run(checksum_mode: str = "fast") -> dict[str, Any]:
    for directory in (OUTPUTS, OUTPUTS / "reports", OUTPUTS / "metrics", OUTPUTS / "predictions", PROJECT / "models"):
        directory.mkdir(parents=True, exist_ok=True)
    registry_path = PROJECT / "models" / "registry.json"
    # Fail before training on corruption; never overwrite an unreadable registry.
    existing_registry = load_registry(registry_path)
    inventory = discover(checksum_mode=checksum_mode)
    inventory.to_csv(OUTPUTS / "metrics" / "data_inventory.csv", index=False)
    tabular_profiles = profile_tabular_files(inventory)
    weather = build_weather_summary(inventory)
    nlp = train_nlp(inventory)
    if nlp.get("status") == "trained":
        register_model(registry_path, nlp)
    quality = {"generated_at": utc_now(), "raw_roots": [str(root.relative_to(ROOT)) for root in find_raw_roots()], "checksum_mode": checksum_mode,
               "files": int(len(inventory)), "by_category": inventory.groupby("category").size().to_dict(),
               "tabular_profiles": tabular_profiles, "weather": weather, "nlp": nlp, "registered_model_count_before_run": len(existing_registry), "registered_model_count_after_run": len(load_registry(registry_path)),
               "explicitly_not_modelled": ["Tourism forecasting: no audited machine-readable visitor-count target table.", "Disaster prediction: no defensible confirmed-negative labels.", "Flood segmentation: no flood masks and rasterio is unavailable.", "Destination stress: no validated stress target; no supervised model trained."]}
    (OUTPUTS / "reports" / "data_quality.json").write_text(json.dumps(quality, indent=2, default=str), encoding="utf-8")
    report = "# SafarSaathi ML run\n\n" + "- Generated: " + quality["generated_at"] + "\n" + "- Raw files discovered: " + str(quality["files"]) + "\n" + "- NLP status: " + nlp["status"] + "\n\n## Guardrails\n\n" + "\n".join(f"- {item}" for item in quality["explicitly_not_modelled"]) + "\n"
    (OUTPUTS / "reports" / "run_report.md").write_text(report, encoding="utf-8")
    return quality


def predict_nlp(model_id: str, texts: list[str]) -> list[Any]:
    artifact = PROJECT / "models" / "nlp" / model_id / "pipeline.joblib"
    if not artifact.is_file() or not texts or not all(isinstance(text, str) and text.strip() for text in texts):
        raise ValueError("A known model_id and one or more non-empty text values are required.")
    return joblib.load(artifact).predict(texts).tolist()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=("run",))
    args = parser.parse_args()
    print(json.dumps(run(), indent=2, default=str))
