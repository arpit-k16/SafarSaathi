"""Re-evaluate a saved NLP model without fitting or retraining it."""
from __future__ import annotations

import json
from pathlib import Path

import joblib
import matplotlib.pyplot as plt
import pandas as pd
from sklearn.metrics import ConfusionMatrixDisplay, accuracy_score, classification_report, confusion_matrix, f1_score
from sklearn.model_selection import train_test_split

from .config import settings
from .registry import resolve_artifact_path


def audit_nlp(model_id: str) -> dict:
    project = settings().project_root
    registry = json.loads((project / "models" / "registry.json").read_text(encoding="utf-8"))
    entry = next((item for item in registry if item.get("model_id") == model_id), None)
    if entry is None:
        raise ValueError("Requested model is not available.")
    metadata_path = project / Path(entry["artifact"]).parent / "metadata.json"
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    relative = metadata.get("dataset_provenance", {}).get("repository_relative_path")
    if not relative:
        raise ValueError("Saved metadata has no portable dataset provenance.")
    source = project.parent / Path(*relative.replace("\\", "/").split("/"))
    frame = pd.read_csv(source)
    text, label = metadata["text_column"], metadata["label_column"]
    base = frame[[text, label]].dropna().copy(); base[text] = base[text].astype(str).str.strip(); base = base[base[text].str.len() > 0]
    exact_duplicates = int(base.duplicated().sum())
    conflicting = int(base.groupby(text)[label].nunique().gt(1).sum())
    cleaned = base.drop_duplicates()
    train, test = train_test_split(cleaned, test_size=0.2, random_state=metadata["random_seed"], stratify=cleaned[label])
    overlap = len(set(train[text]).intersection(test[text]))
    # Near-duplicate proxy: case-folded, whitespace-normalised identical strings only.
    normalise = lambda values: values.astype(str).str.lower().str.replace(r"\s+", " ", regex=True).str.strip()
    normalised_overlap = len(set(normalise(train[text])).intersection(normalise(test[text])))
    model = joblib.load(resolve_artifact_path(project, entry["artifact"]))
    predictions = model.predict(test[text]); labels = sorted(cleaned[label].astype(str).unique())
    cm = confusion_matrix(test[label], predictions, labels=labels)
    output = project / "outputs" / "metrics"; output.mkdir(parents=True, exist_ok=True)
    figure = project / "outputs" / "figures" / f"{model_id}_confusion_matrix.png"; figure.parent.mkdir(parents=True, exist_ok=True)
    display = ConfusionMatrixDisplay(cm, display_labels=labels); display.plot(cmap="Blues"); plt.tight_layout(); plt.savefig(figure, dpi=150); plt.close()
    report = {"model_id": model_id, "evaluation_type": "post-hoc held-out replay; no retraining", "source_rows": len(frame), "rows_after_cleaning": len(cleaned), "exact_duplicate_rows_removed": exact_duplicates, "conflicting_label_text_groups": conflicting, "train_rows": len(train), "test_rows": len(test), "exact_train_test_text_overlap": overlap, "normalised_text_overlap": normalised_overlap, "near_duplicate_method": "case-folded whitespace-normalised exact-match proxy only", "near_duplicate_limitations": "Semantic and fuzzy near-duplicates were not exhaustively assessed; zero exact overlap is not proof of leakage-free evaluation.", "accuracy": float(accuracy_score(test[label], predictions)), "macro_f1": float(f1_score(test[label], predictions, average="macro")), "weighted_f1": float(f1_score(test[label], predictions, average="weighted")), "classification_report": classification_report(test[label], predictions, output_dict=True, zero_division=0), "confusion_matrix": cm.tolist(), "confusion_matrix_figure": str(figure.relative_to(project)).replace("\\", "/")}
    (output / f"{model_id}_evaluation_audit.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report


if __name__ == "__main__":
    registry = json.loads((settings().models_root / "registry.json").read_text(encoding="utf-8"))
    print(json.dumps(audit_nlp(registry[0]["model_id"]), indent=2))
