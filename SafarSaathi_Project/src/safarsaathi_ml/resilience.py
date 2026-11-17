"""Destination digital twin, Destination Stress Index, anomaly detection and hotspots.

Built from two local sources only:
  * UTDB annual visitor counts for 28 destinations (data/processed/utdb_destinations), and
  * NASA POWER daily climate for the matching source points (data/raw_v2/weather_power).
`build_features` condenses both into data/processed/resilience/features.json so the
server never parses raw files on request. Every output field carries a data-status
label (observed / derived / simulated) as the project report requires.
"""
from __future__ import annotations

import hashlib
import json
import math
import random
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path

from .utdb import DESTINATIONS, load_visits

COVID_YEARS = {2020, 2021}  # excluded from growth baselines so the post-COVID rebound is not read as growth
HEAVY_RAIN_MM = 30.0  # a "heavy rain day" in the 0.5° NASA POWER grid (grid values smooth local cloudbursts)
CHAR_DHAM_2013 = {"kedarnath", "badrinath", "rudraprayag", "gopeshwar", "joshimath", "hemkund-sahib",
                  "valley-of-flowers", "gangotri", "yamunotri", "uttarkashi", "auli"}

COMPONENTS = {
    "visitor_load": {"label": "Visitor load", "status": "derived", "default_weight": 0.35,
                     "definition": "log10 of annual visitors, scaled 0–1 between the smallest and largest destination-year in 2000–2024."},
    "growth_pressure": {"label": "Growth pressure", "status": "derived", "default_weight": 0.20,
                        "definition": "Visitors this year ÷ mean of the previous five years (2020–21 COVID years skipped). 0 when not growing, 1 when doubled or more."},
    "monsoon_exposure": {"label": "Monsoon exposure", "status": "derived", "default_weight": 0.20,
                         "definition": "June–September rainfall total at the climate point, scaled 0–1 across all destination-years."},
    "extreme_rain": {"label": "Heavy-rain days", "status": "derived", "default_weight": 0.15,
                     "definition": f"Days with ≥{HEAVY_RAIN_MM:g} mm rain in the year, scaled by the highest count observed."},
    "altitude_fragility": {"label": "Altitude fragility", "status": "derived", "default_weight": 0.10,
                           "definition": "Elevation of the climate point ÷ 4,000 m: a proxy for fragile, hard-to-reach terrain."},
}
BANDS = [(0.35, "Low"), (0.55, "Moderate"), (0.70, "High"), (1.01, "Severe")]
LIMITATIONS = [
    "The index is a transparent composite of proxies. There is no observed crowding or carrying-capacity data to validate it against, so it ranks relative pressure; it does not measure it.",
    "Visitor counts are annual UTDB totals, not daily or seasonal footfall. Haridwar and Rishikesh include large religious gatherings.",
    "Climate values come from the 0.5° NASA POWER grid, which smooths local cloudbursts and valley effects; nearby destinations (e.g. Haridwar and Rishikesh) can share one grid cell.",
    "Band thresholds (Low / Moderate / High / Severe) are display cut-offs, not validated risk levels.",
    "Scenario values are simulated: they apply your assumptions to observed data and are not forecasts.",
]


# ---------------------------------------------------------------- features
def build_features(project: Path) -> dict:
    visits = load_visits(project)
    power = project / "data/raw_v2/weather_power"
    by_id = {}
    for name, dest_id in DESTINATIONS:
        by_id[dest_id] = {"id": dest_id, "name": name, "visits": {}, "indian": {}, "foreign": {}}
    for row in visits:
        d = by_id[row["id"]]
        d["visits"][row["year"]] = row["total"]; d["indian"][row["year"]] = row["indian"]; d["foreign"][row["year"]] = row["foreign"]
    files = {}
    for file in sorted(power.glob("POWER_*.json")):
        data = json.loads(file.read_text(encoding="utf-8"))
        name = data["_safarsaathi_query"]["destination"]
        pid = "".join(c if c.isalnum() else "-" for c in name.lower()).strip("-")
        while "--" in pid: pid = pid.replace("--", "-")
        files[pid] = (file, data)
    for dest_id, d in by_id.items():
        file, data = files[dest_id]
        lon, lat, elev = data["geometry"]["coordinates"][:3]
        fill = data.get("header", {}).get("fill_value", -999.0)
        rain = data["properties"]["parameter"]["PRECTOTCORR"]
        jjas, heavy, maxday = {}, {}, {}
        for stamp, v in rain.items():
            if v is None or v == fill: continue
            y, m = int(stamp[:4]), int(stamp[4:6])
            if 6 <= m <= 9: jjas[y] = jjas.get(y, 0.0) + v
            heavy[y] = heavy.get(y, 0) + (1 if v >= HEAVY_RAIN_MM else 0)
            maxday[y] = max(maxday.get(y, 0.0), v)
        d.update({"lat": lat, "lon": lon, "elevation_m": elev, "climate_file": file.name,
                  "monsoon_mm": {y: round(v, 1) for y, v in jjas.items()}, "heavy_days": heavy,
                  "max_day_mm": {y: round(v, 1) for y, v in maxday.items()}})
    out = {"built_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
           "heavy_rain_mm": HEAVY_RAIN_MM, "destinations": list(by_id.values())}
    target = project / "data/processed/resilience"
    target.mkdir(parents=True, exist_ok=True)
    text = json.dumps(out)
    (target / "features.json").write_text(text, encoding="utf-8")
    (target / "provenance.json").write_text(json.dumps({
        "built_utc": out["built_utc"], "features_sha256": hashlib.sha256(text.encode()).hexdigest(),
        "sources": ["data/processed/utdb_destinations/visits.csv", "data/raw_v2/weather_power/POWER_*.json"]}, indent=2), encoding="utf-8")
    return out


@lru_cache(maxsize=2)
def _features_cached(path: str, mtime: float) -> dict:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    for d in data["destinations"]:
        for key in ("visits", "indian", "foreign", "monsoon_mm", "heavy_days", "max_day_mm"):
            d[key] = {int(k): v for k, v in d[key].items()}
    return data


def features(project: Path) -> dict:
    path = project / "data/processed/resilience/features.json"
    if not path.exists():
        build_features(project)
    return _features_cached(str(path), path.stat().st_mtime)


def _years(f: dict) -> list[int]:
    return sorted(set.intersection(*[set(d["visits"]) & set(d["monsoon_mm"]) for d in f["destinations"]]))


def _scales(f: dict) -> dict:
    vis = [v for d in f["destinations"] for v in d["visits"].values() if v > 0]
    mon = [v for d in f["destinations"] for v in d["monsoon_mm"].values()]
    hv = [v for d in f["destinations"] for v in d["heavy_days"].values()]
    return {"log_min": math.log10(min(vis)), "log_max": math.log10(max(vis)),
            "mon_min": min(mon), "mon_max": max(mon), "heavy_max": max(hv) or 1}


def _clip(x: float) -> float:
    return 0.0 if x < 0 else 1.0 if x > 1 else x


def _components(d: dict, year: int, s: dict, demand_mult: float = 1.0, rain_mult: float = 1.0) -> tuple[dict, dict]:
    v = d["visits"][year] * demand_mult
    prior = [y for y in range(year - 1, 1999, -1) if y in d["visits"] and y not in COVID_YEARS]
    prev = [d["visits"][y] for y in prior[:5]]
    base = sum(prev) / len(prev) if prev else None
    growth = v / base if base else None
    mon = d["monsoon_mm"][year] * rain_mult
    heavy = d["heavy_days"][year] * rain_mult
    comps = {
        "visitor_load": _clip((math.log10(max(v, 1)) - s["log_min"]) / (s["log_max"] - s["log_min"])),
        "growth_pressure": _clip(growth - 1.0) if growth is not None else 0.0,
        "monsoon_exposure": _clip((mon - s["mon_min"]) / (s["mon_max"] - s["mon_min"])),
        "extreme_rain": _clip(heavy / s["heavy_max"]),
        "altitude_fragility": _clip(d["elevation_m"] / 4000.0),
    }
    raw = {"visitors": round(v), "five_year_mean": round(base) if base else None,
           "growth_ratio": round(growth, 3) if growth is not None else None,
           "monsoon_mm": round(mon, 1), "heavy_days": round(heavy, 1), "elevation_m": round(d["elevation_m"])}
    return comps, raw


def _weights(given) -> dict:
    w = {k: c["default_weight"] for k, c in COMPONENTS.items()}
    if given is not None:
        if not isinstance(given, dict) or set(given) - set(COMPONENTS):
            raise ValueError(f"weights must be an object with keys from: {', '.join(COMPONENTS)}.")
        for k, v in given.items():
            if type(v) not in (int, float) or not math.isfinite(v) or v < 0:
                raise ValueError("Each weight must be a non-negative number.")
            w[k] = float(v)
    total = sum(w.values())
    if total <= 0:
        raise ValueError("At least one weight must be above zero.")
    return {k: v / total for k, v in w.items()}


def _band(x: float) -> str:
    return next(label for cut, label in BANDS if x < cut)


def _score(comps: dict, w: dict) -> float:
    return sum(comps[k] * w[k] for k in w)


def _rank_intervals(rows: list[dict], w: dict, draws: int = 300, seed: int = 7) -> dict:
    """Uncertainty from weight choice: rank of each destination under weights resampled ±50% around the chosen ones."""
    rng = random.Random(seed)
    ranks = {r["id"]: [] for r in rows}
    for _ in range(draws):
        ww = {k: v * rng.uniform(0.5, 1.5) for k, v in w.items()}
        t = sum(ww.values()); ww = {k: v / t for k, v in ww.items()}
        order = sorted(rows, key=lambda r: -_score(r["_c"], ww))
        for i, r in enumerate(order, 1): ranks[r["id"]].append(i)
    out = {}
    for k, rs in ranks.items():
        rs.sort(); out[k] = (rs[int(0.05 * (len(rs) - 1))], rs[int(0.95 * (len(rs) - 1))])
    return out


def _spearman(a: list[float], b: list[float]) -> float:
    def rank(x):
        order = sorted(range(len(x)), key=lambda i: x[i]); r = [0] * len(x)
        for pos, i in enumerate(order): r[i] = pos
        return r
    ra, rb = rank(a), rank(b); n = len(a)
    return 1 - 6 * sum((p - q) ** 2 for p, q in zip(ra, rb)) / (n * (n * n - 1))


def _state_rows(f, year, w, s, demand_mult=1.0, rain_mult=1.0, only=None):
    rows = []
    for d in f["destinations"]:
        dm = demand_mult if (only is None or d["id"] in only) else 1.0
        rm = rain_mult if (only is None or d["id"] in only) else 1.0
        c, raw = _components(d, year, s, dm, rm)
        idx = _score(c, w)
        rows.append({"id": d["id"], "name": d["name"], "lat": d["lat"], "lon": d["lon"], "_c": c, "raw": raw,
                     "stress_index": round(idx, 4), "band": _band(idx)})
    rows.sort(key=lambda r: -r["stress_index"])
    for i, r in enumerate(rows, 1): r["rank"] = i
    return rows


def _public(r: dict, w: dict, status: str, interval=None) -> dict:
    contributions = sorted(({"component": k, "label": COMPONENTS[k]["label"], "score": round(r["_c"][k], 4),
                             "weight": round(w[k], 4), "contribution": round(r["_c"][k] * w[k], 4)} for k in w),
                           key=lambda x: -x["contribution"])
    fields = {"visitors": status, "five_year_mean": "observed", "growth_ratio": "derived" if status == "observed" else "simulated",
              "monsoon_mm": status, "heavy_days": status, "elevation_m": "observed"}
    return {k: v for k, v in r.items() if k != "_c"} | {"contributions": contributions, "field_status": fields,
                                                       "index_status": "derived" if status == "observed" else "simulated",
                                                       **({"rank_interval_90": list(interval)} if interval else {})}


# ---------------------------------------------------------------- public API
def metadata(project: Path) -> dict:
    f = features(project)
    prov_path = project / "data/processed/utdb_destinations/provenance.json"
    prov = json.loads(prov_path.read_text(encoding="utf-8")) if prov_path.exists() else {}
    return {"status": "DERIVED_INDEX", "years": _years(f), "default_year": max(_years(f)),
            "destinations": [{"id": d["id"], "name": d["name"], "lat": d["lat"], "lon": d["lon"]} for d in f["destinations"]],
            "components": COMPONENTS, "bands": [{"below": c, "label": l} for c, l in BANDS],
            "sources": {"visitors": prov.get("source"), "visitor_years": prov.get("years"),
                        "visitor_sum_check_failures": len(prov.get("sum_check_failures", [])),
                        "climate": "NASA POWER daily reanalysis, 2000–2024"},
            "features_built_utc": f["built_utc"], "limitations": LIMITATIONS}


def twin_state(project: Path, payload: object) -> dict:
    if not isinstance(payload, dict):
        raise ValueError("Expected a JSON object.")
    allowed = {"year", "weights", "scenario"}
    if set(payload) - allowed:
        raise ValueError(f"Unknown fields; allowed: {', '.join(sorted(allowed))}.")
    f = features(project); years = _years(f)
    year = payload.get("year", max(years))
    if type(year) is not int or year not in years:
        raise ValueError(f"year must be an integer from {years[0]} to {years[-1]}.")
    w = _weights(payload.get("weights")); s = _scales(f)
    base = _state_rows(f, year, w, s)
    intervals = _rank_intervals(base, w)
    out = {"status": "DIGITAL_TWIN_STATE", "year": year, "weights": w,
           "baseline": [_public(r, w, "observed", intervals[r["id"]]) for r in base]}
    # robustness of the ranking to the weighting choice (report §14: uncertainty and sensitivity)
    rng = random.Random(11); rhos = []
    default_scores = [r["stress_index"] for r in base]
    for _ in range(200):
        ww = {k: v * rng.uniform(0.5, 1.5) for k, v in w.items()}; t = sum(ww.values()); ww = {k: v / t for k, v in ww.items()}
        rhos.append(_spearman(default_scores, [_score(r["_c"], ww) for r in base]))
    rhos.sort()
    out["sensitivity"] = {"method": "Spearman rank correlation between the chosen weighting and 200 weightings resampled ±50%",
                          "median_rho": round(rhos[100], 3), "p5_rho": round(rhos[10], 3)}
    sc = payload.get("scenario")
    if sc is not None:
        if not isinstance(sc, dict) or set(sc) - {"demand_change_pct", "rainfall_change_pct", "destinations"}:
            raise ValueError("scenario allows demand_change_pct, rainfall_change_pct and destinations.")
        dpct = sc.get("demand_change_pct", 0); rpct = sc.get("rainfall_change_pct", 0)
        for v in (dpct, rpct):
            if type(v) not in (int, float) or not -90 <= v <= 300:
                raise ValueError("Scenario percentages must be numbers between -90 and 300.")
        only = sc.get("destinations")
        ids = {d["id"] for d in f["destinations"]}
        if only is not None and (not isinstance(only, list) or not only or set(only) - ids):
            raise ValueError("scenario.destinations must be a non-empty list of destination ids.")
        rows = _state_rows(f, year, w, s, 1 + dpct / 100, 1 + rpct / 100, set(only) if only else None)
        base_by = {r["id"]: r for r in base}
        out["scenario"] = {"assumptions": {"demand_change_pct": dpct, "rainfall_change_pct": rpct, "destinations": only or "all"},
                           "rows": [_public(r, w, "simulated") | {"delta_index": round(r["stress_index"] - base_by[r["id"]]["stress_index"], 4),
                                                                 "baseline_rank": base_by[r["id"]]["rank"]} for r in rows],
                           "band_changes": sum(r["band"] != base_by[r["id"]]["band"] for r in rows)}
    out["limitations"] = LIMITATIONS
    out["provenance"] = {"visitors": f"UTDB {year}", "climate": f"NASA POWER {year}", "features_built_utc": f["built_utc"]}
    return out


def _robust_z(values: list[float]) -> list[float]:
    s = sorted(values); n = len(s)
    med = s[n // 2] if n % 2 else (s[n // 2 - 1] + s[n // 2]) / 2
    dev = sorted(abs(v - med) for v in values)
    mad = dev[n // 2] if n % 2 else (dev[n // 2 - 1] + dev[n // 2]) / 2
    scale = 1.4826 * mad if mad > 0 else 1e-9
    return [(v - med) / scale for v in values]


def anomalies(project: Path, z_threshold: float = 3.5) -> dict:
    f = features(project)
    visitor_flags, rain_flags, all_points = [], [], []
    for d in f["destinations"]:
        ys = sorted(d["visits"])
        pairs = [(y, math.log(d["visits"][y] / d["visits"][y - 1])) for y in ys if y - 1 in d["visits"] and d["visits"][y - 1] > 0 and d["visits"][y] > 0]
        zs = _robust_z([p[1] for p in pairs])
        for (y, ch), z in zip(pairs, zs):
            pct = (math.exp(ch) - 1) * 100
            all_points.append((d["id"], y, abs(z) >= z_threshold, abs(pct) >= 50))
            if abs(z) >= z_threshold:
                visitor_flags.append({"id": d["id"], "name": d["name"], "year": y, "visitors": d["visits"][y],
                                      "previous": d["visits"][y - 1], "change_pct": round(pct, 1), "robust_z": round(z, 2),
                                      "direction": "drop" if ch < 0 else "surge"})
        my = sorted(d["max_day_mm"]); mz = _robust_z([d["max_day_mm"][y] for y in my])
        jz = _robust_z([d["monsoon_mm"][y] for y in my])
        for y, a, b in zip(my, mz, jz):
            if a >= 3.0 or abs(b) >= 3.0:
                rain_flags.append({"id": d["id"], "name": d["name"], "year": y, "max_day_mm": d["max_day_mm"][y],
                                   "monsoon_mm": d["monsoon_mm"][y], "max_day_z": round(a, 2), "monsoon_z": round(b, 2)})
    known = {(i, y) for i in CHAR_DHAM_2013 for y in (2013, 2014)} | {(d["id"], y) for d in f["destinations"] for y in (2020, 2021, 2022)}

    def score(flag_index):
        flagged = [(i, y) for i, y, *flags in all_points if flags[flag_index]]
        tp = sum(p in known for p in flagged)
        reachable = [p for p in known if any(p == (i, y) for i, y, *_ in all_points)]
        return {"flags": len(flagged), "in_known_event_years": tp,
                "precision": round(tp / len(flagged), 3) if flagged else None,
                "recall": round(sum(p in set(flagged) for p in reachable) / len(reachable), 3) if reachable else None}
    visitor_flags.sort(key=lambda r: (r["year"], r["robust_z"]))
    return {"status": "HISTORICAL_ANOMALIES",
            "visitor_method": f"Year-on-year log change in UTDB visitors, robust z-score against each destination's own history (median and MAD); flagged at |z| ≥ {z_threshold}.",
            "rain_method": "Wettest day and June–September total per year at each climate point, robust z-score against that point's 2000–2024 history; flagged at z ≥ 3.",
            "visitor_anomalies": visitor_flags,
            "series": {d["id"]: [{"year": y, "total": d["visits"][y]} for y in sorted(d["visits"])] for d in f["destinations"]}, "rain_anomalies": sorted(rain_flags, key=lambda r: (-r["max_day_z"])),
            "evaluation": {"reference_events": "June 2013 Char Dham disaster and the suppressed 2014 yatra (11 Garhwal destinations) and 2020–2022 COVID disruption and rebound (all destinations).",
                           "robust_z": score(0), "baseline_50pct_change": score(1),
                           "note": "Precision = share of flags that fall in a reference event year; recall = share of reference destination-years flagged. Reference events are a small hand-made list, so treat these as indicative."},
            "limitations": ["Annual totals hide within-year disruptions; a flagged year means the whole-year total moved unusually.",
                            "A flag says a value is unusual for that place, not why. Check the event before acting on it.",
                            "Climate flags use a 0.5° grid and can miss very local cloudbursts."]}


def _haversine_km(a, b):
    lat1, lon1, lat2, lon2 = map(math.radians, (a[0], a[1], b[0], b[1]))
    h = math.sin((lat2 - lat1) / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin((lon2 - lon1) / 2) ** 2
    return 2 * 6371.0 * math.asin(math.sqrt(h))


def hotspots(project: Path, query: dict) -> dict:
    import numpy as np
    from sklearn.cluster import DBSCAN, KMeans
    from sklearn.metrics import silhouette_score
    f = features(project); years = _years(f)
    try:
        year = int(query.get("year", max(years))); method = query.get("method", "dbscan")
        eps_km = float(query.get("eps_km", 35)); min_samples = int(query.get("min_samples", 2)); k = int(query.get("k", 4))
    except (TypeError, ValueError):
        raise ValueError("year, eps_km, min_samples and k must be numbers.")
    if year not in years or method not in ("dbscan", "kmeans") or not 5 <= eps_km <= 150 or not 1 <= min_samples <= 10 or not 2 <= k <= 10:
        raise ValueError(f"Use year {years[0]}–{years[-1]}, method dbscan|kmeans, eps_km 5–150, min_samples 1–10, k 2–10.")
    ds = f["destinations"]
    coords = np.array([[d["lat"], d["lon"]] for d in ds]); logv = np.array([math.log10(max(d["visits"][year], 1)) for d in ds])
    if method == "dbscan":
        labels = DBSCAN(eps=eps_km / 6371.0, min_samples=min_samples, metric="haversine").fit_predict(np.radians(coords))
        feats = np.radians(coords); metric = "haversine"
        params = {"eps_km": eps_km, "min_samples": min_samples}
    else:
        x = np.column_stack([coords, logv]); x = (x - x.mean(0)) / x.std(0)
        labels = KMeans(n_clusters=k, n_init=20, random_state=0).fit_predict(x)
        feats = x; metric = "euclidean"; params = {"k": k}
    clustered = labels >= 0
    n_clusters = len(set(labels[clustered]))
    sil = None; base = None
    if n_clusters >= 2 and clustered.sum() > n_clusters:
        sil = float(silhouette_score(feats[clustered], labels[clustered], metric=metric))
        rng = np.random.default_rng(0); vals = []
        for _ in range(100):
            perm = rng.permutation(labels[clustered])
            if len(set(perm)) >= 2: vals.append(silhouette_score(feats[clustered], perm, metric=metric))
        base = float(np.mean(vals)) if vals else None
    s = _scales(f); w = _weights(None)
    clusters = []
    for lab in sorted(set(labels)):
        idx = [i for i in range(len(ds)) if labels[i] == lab]
        members = [ds[i] for i in idx]
        total = sum(m["visits"][year] for m in members)
        stress = [_score(_components(m, year, s)[0], w) for m in members]
        center = (float(np.mean(coords[idx, 0])), float(np.mean(coords[idx, 1])))
        clusters.append({"cluster": int(lab), "noise": bool(lab < 0), "members": [m["id"] for m in members],
                         "names": [m["name"] for m in members], "visitors": total,
                         "share_of_state": None, "mean_stress_index": round(sum(stress) / len(stress), 4),
                         "centroid": {"lat": round(center[0], 4), "lon": round(center[1], 4)},
                         "radius_km": round(max(_haversine_km(center, (m["lat"], m["lon"])) for m in members), 1)})
    state_total = sum(d["visits"][year] for d in ds)
    for c in clusters: c["share_of_state"] = round(c["visitors"] / state_total, 4)
    clusters.sort(key=lambda c: (c["noise"], -c["visitors"]))
    return {"status": "SPATIAL_CLUSTERS", "year": year, "method": method, "parameters": params,
            "points": [{"id": d["id"], "name": d["name"], "lat": d["lat"], "lon": d["lon"], "visitors": d["visits"][year],
                        "cluster": int(labels[i])} for i, d in enumerate(ds)],
            "clusters": clusters,
            "evaluation": {"silhouette": round(sil, 3) if sil is not None else None,
                           "random_label_baseline": round(base, 3) if base is not None else None,
                           "note": "Silhouette ranges −1 to 1; higher means tighter, better-separated clusters. The baseline shuffles the same labels at random."},
            "limitations": ["Clusters group the 28 UTDB destinations, not individual attractions or tourist GPS traces.",
                            "DBSCAN groups by distance only (cluster −1 is noise: isolated places). K-means also uses visitor volume.",
                            "Validate clusters against local knowledge before using them for planning."]}


# ---------------------------------------------------------------- intervention planning (report §10.3–10.4, §9.8)
DEFAULT_INTERVENTIONS = [
    {"id": "ked-badri", "type": "shift", "from": "kedarnath", "to": "badrinath", "pct": 15, "cost": 40, "label": "Promote Badrinath slots to shift 15% of Kedarnath pilgrims"},
    {"id": "ked-permit", "type": "cap", "from": "kedarnath", "pct": 10, "cost": 15, "label": "Daily permit cap at Kedarnath (−10%)"},
    {"id": "tehri-cap", "type": "cap", "from": "tehri", "pct": 15, "cost": 20, "label": "Lake-zone entry management at Tehri (−15%)"},
    {"id": "mussoorie-kausani", "type": "shift", "from": "mussoorie", "to": "kausani", "pct": 15, "cost": 25, "label": "Package tours shifting 15% of Mussoorie visitors to Kausani"},
    {"id": "nainital-ranikhet", "type": "shift", "from": "nainital", "to": "ranikhet", "pct": 20, "cost": 15, "label": "Shuttle and stay incentives: 20% of Nainital to Ranikhet"},
    {"id": "haridwar-cap", "type": "cap", "from": "haridwar", "pct": 5, "cost": 60, "label": "Crowd management at Haridwar ghats (−5%)"},
    {"id": "dehradun-cap", "type": "cap", "from": "dehradun", "pct": 10, "cost": 35, "label": "Peak-weekend traffic restrictions in Dehradun (−10%)"},
    {"id": "gangotri-uttarkashi", "type": "shift", "from": "gangotri", "to": "uttarkashi", "pct": 20, "cost": 15, "label": "Stage 20% of Gangotri visitors through Uttarkashi"},
    {"id": "auli-joshimath", "type": "shift", "from": "auli", "to": "joshimath", "pct": 20, "cost": 10, "label": "Day-trip model: 20% of Auli stays moved to Joshimath"},
    {"id": "rishikesh-kotdwar", "type": "shift", "from": "rishikesh", "to": "kotdwar", "pct": 10, "cost": 20, "label": "Promote Kotdwar circuits: 10% of Rishikesh visitors"},
]
INTERVENTION_LIMITATIONS = [
    "Intervention costs and effects are planning assumptions you supply (₹ lakh, % of annual visitors). There are no verified cost or effectiveness data in this project.",
    "Effects are applied to annual UTDB visitor totals and recomputed through the Destination Stress Index; real responses to incentives or caps are uncertain.",
    "Caps turn visitors away, which the objective counts as lost visits (a proxy for satisfaction and local income). Shifts move visitors without loss.",
    "Results are simulated decision support for comparing options, not an operational plan. Real interventions need local consultation and authorised decisions.",
]


def _index_with(f, year, w, s, mult: dict) -> dict:
    out = {}
    for d in f["destinations"]:
        c, raw = _components(d, year, s, mult.get(d["id"], 1.0), 1.0)
        out[d["id"]] = (_score(c, w), raw["visitors"])
    return out


def interventions(project: Path, payload: object) -> dict:
    import time
    if not isinstance(payload, dict) or set(payload) - {"year", "budget", "interventions", "lost_visit_weight", "threshold", "algorithm", "seed"}:
        raise ValueError("Allowed fields: year, budget, interventions, lost_visit_weight, threshold, algorithm, seed.")
    f = features(project); years = _years(f); ids = {d["id"] for d in f["destinations"]}
    year = payload.get("year", max(years)); budget = payload.get("budget", 100)
    lam = payload.get("lost_visit_weight", 2.0); thr = payload.get("threshold", 0.55)
    algorithm = payload.get("algorithm", "ga"); seed = payload.get("seed", 7)
    if type(year) is not int or year not in years: raise ValueError(f"year must be {years[0]}–{years[-1]}.")
    for name, v, lo, hi in (("budget", budget, 0, 10000), ("lost_visit_weight", lam, 0, 50), ("threshold", thr, 0.1, 0.95)):
        if type(v) not in (int, float) or not lo <= v <= hi: raise ValueError(f"{name} must be between {lo} and {hi}.")
    if algorithm not in ("ga", "pso") or type(seed) is not int: raise ValueError("algorithm must be ga or pso; seed an integer.")
    items = payload.get("interventions") or DEFAULT_INTERVENTIONS
    if not isinstance(items, list) or not 1 <= len(items) <= 16: raise ValueError("Give 1–16 interventions.")
    for it in items:
        if not isinstance(it, dict) or it.get("type") not in ("shift", "cap") or it.get("from") not in ids:
            raise ValueError("Each intervention needs type shift|cap and a valid 'from' destination id.")
        if it["type"] == "shift" and (it.get("to") not in ids or it["to"] == it["from"]):
            raise ValueError("A shift needs a different valid 'to' destination id.")
        if type(it.get("pct")) not in (int, float) or not 0 < it["pct"] <= 50: raise ValueError("pct must be in (0, 50].")
        if type(it.get("cost")) not in (int, float) or not 0 <= it["cost"] <= 5000: raise ValueError("cost must be 0–5000.")
    w = _weights(None); s = _scales(f)
    base_visits = {d["id"]: d["visits"][year] for d in f["destinations"]}
    total_visits = sum(base_visits.values())
    baseline = _index_with(f, year, w, s, {})

    def evaluate(mask):
        cost = sum(it["cost"] for it, m in zip(items, mask) if m)
        delta = {k: 0.0 for k in base_visits}; lost = 0.0
        for it, m in zip(items, mask):
            if not m: continue
            moved = base_visits[it["from"]] * it["pct"] / 100
            delta[it["from"]] -= moved
            if it["type"] == "shift": delta[it["to"]] += moved
            else: lost += moved
        mult = {k: max(0.05, (base_visits[k] + delta[k]) / base_visits[k]) for k in base_visits}
        idx = _index_with(f, year, w, s, mult)
        exceed = sum(max(0.0, v[0] - thr) for v in idx.values())
        lost_share = lost / total_visits
        obj = exceed + lam * lost_share
        return {"objective": obj, "exceedance": exceed, "lost_share": lost_share, "cost": cost, "feasible": cost <= budget, "index": idx}

    def fitness(mask):
        e = evaluate(mask)
        tie_break = 1e-3 * e["cost"] / max(budget, 1)  # among equally good plans, prefer the cheaper one
        return e["objective"] + tie_break + (0 if e["feasible"] else 10 + (e["cost"] - budget) / max(budget, 1))

    n = len(items); rng = random.Random(seed); t0 = time.perf_counter(); history = []
    if algorithm == "ga":
        pop = [[rng.random() < 0.3 for _ in range(n)] for _ in range(30)]
        best = min(pop, key=fitness)
        for _ in range(40):
            scored = sorted(pop, key=fitness); best = min(best, scored[0], key=fitness); history.append(round(fitness(best), 5))
            nxt = scored[:4]
            while len(nxt) < len(pop):
                a, b = (min(rng.sample(scored, 3), key=fitness) for _ in range(2))
                cut = rng.randrange(1, n) if n > 1 else 0
                child = a[:cut] + b[cut:]
                child = [(not g) if rng.random() < 1 / n else g for g in child]
                nxt.append(child)
            pop = nxt
    else:  # binary PSO with sigmoid velocities
        pos = [[rng.random() < 0.3 for _ in range(n)] for _ in range(30)]; vel = [[0.0] * n for _ in range(30)]
        pbest = [p[:] for p in pos]; best = min(pbest, key=fitness)
        for _ in range(40):
            for i in range(30):
                for j in range(n):
                    vel[i][j] = 0.7 * vel[i][j] + 1.5 * rng.random() * (pbest[i][j] - pos[i][j]) + 1.5 * rng.random() * (best[j] - pos[i][j])
                    vel[i][j] = max(-4, min(4, vel[i][j]))
                    pos[i][j] = rng.random() < 1 / (1 + math.exp(-vel[i][j]))
                if fitness(pos[i]) < fitness(pbest[i]): pbest[i] = pos[i][:]
            best = min(pbest + [best], key=fitness); history.append(round(fitness(best), 5))
    runtime = time.perf_counter() - t0
    chosen = evaluate(best)
    # baselines: do nothing, greedy by benefit per rupee, exhaustive optimum for small n
    nothing = evaluate([False] * n)
    gains = []
    for i in range(n):
        m = [False] * n; m[i] = True; e = evaluate(m)
        gains.append((nothing["objective"] - e["objective"]) / max(items[i]["cost"], 1e-6))
    greedy = [False] * n; spent = 0
    for i in sorted(range(n), key=lambda i: -gains[i]):
        if gains[i] > 0 and spent + items[i]["cost"] <= budget:
            trial = greedy[:]; trial[i] = True
            if evaluate(trial)["objective"] < evaluate(greedy)["objective"]: greedy = trial; spent += items[i]["cost"]
    greedy_e = evaluate(greedy)
    optimum = None
    if n <= 12:
        from itertools import product
        best_mask = min(product([False, True], repeat=n), key=fitness)
        optimum = evaluate(list(best_mask)); optimum["mask"] = list(best_mask)

    def pack(e, mask):
        changed = sorted(((k, baseline[k][0], e["index"][k][0]) for k in baseline if abs(e["index"][k][0] - baseline[k][0]) > 1e-4),
                         key=lambda x: x[2] - x[1])
        names = {d["id"]: d["name"] for d in f["destinations"]}
        return {"selected": [it["id"] for it, m in zip(items, mask) if m], "cost": e["cost"], "feasible": e["feasible"],
                "objective": round(e["objective"], 5), "exceedance": round(e["exceedance"], 5), "lost_visit_share": round(e["lost_share"], 5),
                "destinations_above_threshold": sum(1 for v in e["index"].values() if v[0] > thr),
                "changes": [{"id": k, "name": names[k], "before": round(a, 4), "after": round(b, 4)} for k, a, b in changed]}
    return {"status": "SIMULATED_INTERVENTION_PLAN", "year": year, "budget": budget, "algorithm": algorithm, "seed": seed,
            "objective_definition": f"Minimise Σ max(0, stress index − {thr}) over 28 destinations + {lam} × share of annual visitors turned away; total cost ≤ budget. Ties go to the cheaper plan.",
            "interventions": items, "plan": pack(chosen, best), "convergence": history, "runtime_ms": round(runtime * 1000),
            "baselines": {"do_nothing": pack(nothing, [False] * n), "greedy_benefit_per_cost": pack(greedy_e, greedy),
                          **({"exhaustive_optimum": pack(optimum, optimum["mask"])} if optimum else {})},
            "optimality_gap": (round(chosen["objective"] - optimum["objective"], 6) if optimum else None),
            "limitations": INTERVENTION_LIMITATIONS}
