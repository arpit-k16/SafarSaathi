"""Release gate for SafarSaathi v1.0 (project report §12.4 M7 and §14.3).

A registered model is released as FINAL_V1 only if it passes three checks:
  G1 artifact integrity: the saved file matches its recorded SHA-256 and passed a reload test;
  G2 baseline: on held-out TEST data (never used for selection) it is at least as good as a naive baseline;
  G3 documentation: scope and limitations are recorded.
The registry itself is never edited; the result is frozen in models/release_v1.json.
Passing means "frozen, reproducible and baseline-checked within its documented scope",
not "operationally validated".
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path

RELEASE = "v1.0"
STATUS = "FINAL_V1"


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _entries(project: Path) -> list[dict]:
    r = json.loads((project / "models/registry.json").read_text(encoding="utf-8"))
    items = r if isinstance(r, list) else r.get("models", r)
    return list(items.values()) if isinstance(items, dict) else items


def _baseline(m: dict) -> dict:
    mid, met = m["model_id"], m.get("metrics") or {}
    if m.get("task") == "review classification":
        rep = met["classification_report"]
        labels = [k for k, v in rep.items() if isinstance(v, dict) and "support" in v and k not in ("macro avg", "weighted avg")]
        sup = [rep[k]["support"] for k in labels]
        majority = max(sup) / sum(sup)
        return {"metric": "accuracy (higher is better)", "model": met["accuracy"], "baseline": majority,
                "baseline_name": "always predict the majority class", "passed": met["accuracy"] > majority}
    if mid == "tourism_demand_forecaster":
        a, b = met["by_horizon"]["1"]["MAE"], m["baseline_metrics"]["by_horizon"]["1"]["MAE"]
        return {"metric": "1-year-ahead MAE, arrivals (lower is better)", "model": a, "baseline": b,
                "baseline_name": "naive: repeat last year", "passed": a <= b}
    if mid == "tourism_monthly_fta_forecaster":
        sel = met["selected_method"]; t = met["test"]
        a, b = t[sel]["1"]["MAE"], t["persistence"]["1"]["MAE"]
        return {"metric": "1-month-ahead MAE, arrivals (lower is better)", "model": a, "baseline": b,
                "baseline_name": "naive: repeat last month", "passed": a <= b, "baseline_model": sel == "persistence",
                "note": "The selected model is the persistence baseline itself: it was chosen on validation data over drift, seasonal-naive and ridge."}
    if mid in ("north_indian_cyclone_count_forecaster", "india_pm25_exposure_forecaster"):
        meths = met["methods"]; sel = met["selected_method"]
        naive = "constant_mean" if "constant_mean" in meths else "naive"
        a, b = meths[sel]["test"]["MAE"], meths[naive]["test"]["MAE"]
        return {"metric": "test MAE (lower is better)", "model": a, "baseline": b,
                "baseline_name": "constant mean" if naive == "constant_mean" else "naive: repeat last year", "passed": a <= b}
    if mid == "flood_segmentation_model":
        a = met["test"]["IoU"]; b = met["always_negative_baseline"]["reference_positive_IoU"]
        return {"metric": "test IoU on unseen countries (higher is better)", "model": a, "baseline": b,
                "baseline_name": "predict no water anywhere", "passed": a > b,
                "note": f"Validation IoU {met['validation']['IoU']:.2f} drops to {a:.2f} on test countries: generalisation to new regions is limited."}
    return {"passed": False, "reason": "No baseline comparison recorded."}


def run_gate(project: Path) -> dict:
    integrity = json.loads((project / "models/artifact_integrity.json").read_text(encoding="utf-8")).get("artifacts", {})
    models = []
    for m in _entries(project):
        art = project / m["artifact"]
        recorded = m.get("artifact_sha256") or integrity.get(m["artifact"].replace("\\", "/"))
        g1 = bool(art.exists() and recorded and _sha(art) == recorded and m.get("persistence_test_passed", False))
        g2 = _baseline(m)
        lim = m.get("limitations")
        g3 = bool(lim) and (isinstance(lim, str) or len(lim) > 0)
        ok = g1 and g2.get("passed") and g3
        models.append({"model_id": m["model_id"], "task": m.get("task"), "release": RELEASE if ok else None,
                       "status": STATUS if ok else m.get("quality_status", "TRAINED_BUT_EXPERIMENTAL"),
                       "gates": {"G1_artifact_integrity": g1, "G2_beats_or_matches_naive_baseline": g2, "G3_limitations_documented": g3},
                       "previous_status": m.get("quality_status")})
    out = {"release": RELEASE, "frozen_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
           "definition": "FINAL_V1 = frozen, checksum-verified, reload-tested, and at least as good as a naive baseline on held-out test data, within the documented scope. It does not mean operationally validated for real-world decisions.",
           "passed": sum(1 for m in models if m["release"]), "total": len(models), "models": models}
    (project / "models/release_v1.json").write_text(json.dumps(out, indent=2), encoding="utf-8")
    return out


@lru_cache(maxsize=2)
def _load(path: str, mtime: float) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def release(project: Path) -> dict | None:
    p = project / "models/release_v1.json"
    return _load(str(p), p.stat().st_mtime) if p.exists() else None


def status_for(project: Path, model_id: str, default: str) -> str:
    r = release(project)
    if not r:
        return default
    hit = next((m for m in r["models"] if m["model_id"] == model_id), None)
    return hit["status"] if hit and hit["release"] else default


if __name__ == "__main__":
    import sys
    res = run_gate(Path(sys.argv[1] if len(sys.argv) > 1 else "."))
    for m in res["models"]:
        g = m["gates"]["G2_beats_or_matches_naive_baseline"]
        print(f"{m['model_id']:42s} {m['status']:26s} G1={m['gates']['G1_artifact_integrity']} G2={g.get('passed')} ({g.get('model'):.4g} vs {g.get('baseline'):.4g}) G3={m['gates']['G3_limitations_documented']}")
    print(res["passed"], "of", res["total"], "released as", res["release"])
