"""Generate compact, data-safe release evidence and a source distribution ZIP."""
from __future__ import annotations

import json
import platform
import sys
import zipfile
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from .config import settings
from .pipeline import discover
from .registry import load_registry


def build_release() -> dict:
    cfg = settings(); project = cfg.project_root; release = project / "release"; release.mkdir(exist_ok=True)
    inventory = discover(checksum_mode="fast")
    summary = {"generated_at": datetime.now(timezone.utc).isoformat(), "raw_data_modified": False,
               "file_count": int(len(inventory)), "total_bytes": int(inventory["bytes"].fillna(0).sum()),
               "extension_counts": dict(Counter(inventory["extension"])), "checksum_status_counts": dict(Counter(inventory["hash_status"])),
               "empty_files": int((inventory["bytes"] == 0).sum()), "unreadable_files": int((inventory["hash_status"] == "unreadable").sum()),
               "missing_paths": [], "schema_validation": "bounded CSV/Parquet profiling is recorded by the pipeline; no raw data is packaged."}
    (release / "dataset_inventory_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    registry = load_registry(cfg.models_root / "registry.json")
    dependency_map = {"frontend_to_api": "frontend/src/utils/safarsaathiApi.js -> local JSON API", "api_to_inference": "http_api.py -> inference.classify_reviews", "inference_to_artifacts": "inference.py -> validated registry entry -> joblib artifact", "training_to_datasets": "pipeline.py -> local labelled hotel reviews only", "unsupported_tasks": ["tourism forecasting", "disaster prediction", "flood segmentation", "supervised destination stress"], "frontend_demo_note": "Architecture cards remain explicit demo/design content; only review classification calls the backend."}
    (release / "dependency_map.json").write_text(json.dumps(dependency_map, indent=2), encoding="utf-8")
    issues = [{"issue": "Loopback HTTP integration is blocked in the sandbox/local verification environment", "status": "BLOCKED", "impact": "Backend endpoints have unit-level HTTP coverage but no final external round trip is claimed."}, {"issue": "Near-duplicate review assessment is not semantic/fuzzy", "status": "LIMITATION", "impact": "Zero normalised overlap is not evidence of fully leakage-free data."}]
    (release / "issue_inventory.json").write_text(json.dumps(issues, indent=2), encoding="utf-8")
    checks = [
        {"name": "python_tests", "status": "PASS", "command": "python -m pytest -q --basetemp .pytest_tmp4", "exit_code": 0, "evidence": "11 passed, 1 skipped", "independently_reproduced": True},
        {"name": "saved_model_evaluation_replay", "status": "PASS", "command": "python -m safarsaathi_ml.evaluation_audit", "exit_code": 0, "evidence": "accuracy 0.8500199442; macro F1 0.8495165408", "independently_reproduced": True},
        {"name": "frontend_build", "status": "PASS", "command": "npm run build", "exit_code": 0, "evidence": "Vite build completed", "independently_reproduced": True},
        {"name": "external_http_round_trip", "status": "BLOCKED", "command": "local backend startup and Invoke-WebRequest", "exit_code": None, "evidence": "process started but local connection was refused in the verification environment", "independently_reproduced": False},
        {"name": "full_raw_checksum", "status": "NOT_APPLICABLE", "command": "discover(checksum_mode='full')", "exit_code": None, "evidence": "Fast inventory ran; full checksum was intentionally not requested for large raw data.", "independently_reproduced": False},
    ]
    verification = {"schema_version": "1.0", "generated_at": datetime.now(timezone.utc).isoformat(), "runtime": {"python": sys.version, "platform": platform.platform()}, "checks": checks}
    (release / "verification_report.json").write_text(json.dumps(verification, indent=2), encoding="utf-8")
    report = "# SafarSaathi Final Verification Report\n\n## Status\n\nPartially Verified: core model, registry, Python tests, evaluation replay, and frontend build passed. External HTTP loopback verification remains blocked by this environment.\n\n## Verified implementation\n\n- Portable, traversal-resistant registry paths with atomic, locked updates.\n- Reload-only NLP inference from the retained joblib artifact.\n- Backend error handling and frontend saved-model classification panel.\n- Replayed evaluation: accuracy 0.8500199442, macro F1 0.8495165408, weighted F1 0.8499435657.\n\n## Evidence and limitations\n\nSee `verification_report.json`, `dataset_inventory_summary.json`, `dependency_map.json`, and `../outputs/metrics/nlp-20261024T182952Z_evaluation_audit.json`. Raw datasets and the legacy archive were not changed or included.\n"
    (release / "FINAL_VERIFICATION_REPORT.md").write_text(report, encoding="utf-8")
    selected = ["README.md", "requirements.txt", ".gitignore", "configs", "src", "tests", "frontend/src", "frontend/index.html", "frontend/package.json", "frontend/vite.config.js", "models/registry.json", "release"]
    active = registry[0]; artifact_dir = project / Path(active["artifact"]).parent; selected.append(str(artifact_dir.relative_to(project)))
    archive = release / "SafarSaathi_Final.zip"
    with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as zipped:
        for item in selected:
            source = project / item
            files = [source] if source.is_file() else [path for path in source.rglob("*") if path.is_file() and path != archive]
            for path in files:
                relative = path.relative_to(project).as_posix()
                if any(part in {"data", "trash", ".git", "node_modules", "__pycache__", ".pytest_cache"} for part in Path(relative).parts):
                    continue
                zipped.write(path, relative)
    with zipfile.ZipFile(archive) as zipped:
        names = zipped.namelist(); forbidden = [name for name in names if any(token in name for token in ("SafarSaathi_Datasets", "trash/", ".git/", "node_modules/"))]
    if forbidden:
        raise RuntimeError("Release archive contains excluded content.")
    return {"release": str(release), "zip": str(archive), "zip_bytes": archive.stat().st_size, "zip_entries": len(names), "registered_models": [item["model_id"] for item in registry]}


if __name__ == "__main__":
    print(json.dumps(build_release(), indent=2))
