"""Risk-aware routing between Uttarakhand destinations (project report §11).

Route cost per road segment, in minutes:
    cost = α·travel_time + (β·hazard + γ·vulnerability + δ·congestion + ε·uncertainty) · length_km
Each risk term is a 0–1 proxy, so a coefficient reads as "extra minutes per km at full intensity".
The shortest-time baseline is the same search with β = γ = δ = ε = 0.

Road network: OpenStreetMap (© OpenStreetMap contributors, ODbL), motorway to unclassified roads,
extracted by scripts/osm_road_graph. Proxies come from NASA POWER climate points and UTDB visitors.
"""
from __future__ import annotations

import math
from functools import lru_cache
from pathlib import Path

import numpy as np

from .resilience import _years, features

CLASS_SPEED = {"motorway": 80, "trunk": 50, "primary": 40, "secondary": 32, "tertiary": 26, "unclassified": 20}
CLASS_VULN = {"motorway": 0.10, "trunk": 0.20, "primary": 0.35, "secondary": 0.50, "tertiary": 0.65, "unclassified": 0.80}
HILL_M = 1000.0
DEFAULT_WEIGHTS = {"alpha": 1.0, "beta": 3.0, "gamma": 1.0, "delta": 0.5, "epsilon": 0.5}
TERMS = {
    "alpha": "Travel time: segment length ÷ class speed (×0.6 above 1,000 m).",
    "beta": "Hazard exposure: heavy-rain days and monsoon total at nearby NASA POWER points, interpolated to the road.",
    "gamma": "Infrastructure vulnerability: road class (unclassified most fragile), raised in hill terrain.",
    "delta": "Congestion: visitor load of destinations within ~15 km (UTDB), decaying with distance.",
    "epsilon": "Uncertainty: distance from the road to the nearest climate point (sparser data, less certain).",
}
LIMITATIONS = [
    "Every risk term is a proxy built from public data. There is no landslide-susceptibility, live road-status or traffic data in this project.",
    "Travel times use road-class speeds with a hill factor; real mountain travel is slower and varies by season.",
    "Destinations reached on foot (Kedarnath, Hemkund Sahib, Yamunotri, Valley of Flowers) snap to the nearest road head; the trek is not routed.",
    "Coefficients express priorities. Document them and test them; do not tune them to get a preferred route.",
    "Decision support only: real closures and evacuations need verified road status and authorised decisions.",
]


def _equi_km(lat1, lon1, lat2, lon2):
    x = (lon2 - lon1) * np.cos(np.radians((lat1 + lat2) / 2)) * 111.32
    y = (lat2 - lat1) * 110.57
    return np.sqrt(x * x + y * y)


@lru_cache(maxsize=1)
def _graph(path: str, mtime: float) -> dict:
    g = dict(np.load(path))
    offs = g["geo_offsets"]; geo = g["geo"]
    mid = geo[(offs[:-1] + offs[1:]) // 2]
    g["mid_lat"], g["mid_lon"] = mid[:, 0].astype(np.float64), mid[:, 1].astype(np.float64)
    return g


def graph(project: Path) -> dict:
    path = project / "data/processed/routing/road_graph.npz"
    if not path.exists():
        raise OSError("Road graph is missing; run scripts/osm_road_graph.")
    return _graph(str(path), path.stat().st_mtime)


@lru_cache(maxsize=2)
def _attributes(project_str: str, gmtime: float, fbuilt: str) -> dict:
    project = Path(project_str); g = graph(project); f = features(project)
    ds = f["destinations"]; year = max(_years(f))
    plat = np.array([d["lat"] for d in ds]); plon = np.array([d["lon"] for d in ds]); pel = np.array([d["elevation_m"] for d in ds])
    heavy = np.array([np.mean(list(d["heavy_days"].values())) for d in ds]); mon = np.array([np.mean(list(d["monsoon_mm"].values())) for d in ds])
    norm = lambda a: (a - a.min()) / (a.max() - a.min())
    p_hazard = 0.5 * norm(heavy) + 0.5 * norm(mon)
    vis = np.array([d["visits"][year] for d in ds], dtype=float)
    load = (np.log10(vis) - np.log10(vis.min())) / (np.log10(vis.max()) - np.log10(vis.min()))
    mlat, mlon = g["mid_lat"], g["mid_lon"]
    dist = _equi_km(mlat[:, None], mlon[:, None], plat[None, :], plon[None, :])  # edges × points
    near = np.argsort(dist, axis=1)[:, :3]; dn = np.take_along_axis(dist, near, axis=1)
    w = 1.0 / np.maximum(dn, 1.0) ** 2; w /= w.sum(1, keepdims=True)
    hazard = (p_hazard[near] * w).sum(1); elev = (pel[near] * w).sum(1)
    uncertainty = np.clip(dn[:, 0] / 40.0, 0, 1)
    congestion = (load[None, :] * np.exp(-dist / 15.0)).max(1)
    classes = [str(c) for c in g["classes"]]; cls = g["edge_class"]
    hill = elev > HILL_M
    speed = np.array([CLASS_SPEED[c] for c in classes])[cls] * np.where(hill, 0.6, 1.0)
    vuln = np.clip(np.array([CLASS_VULN[c] for c in classes])[cls] + np.where(hill, 0.2, 0.0), 0, 1)
    km = g["edge_km"].astype(np.float64)
    # snap destinations to the nearest graph node
    nd = _equi_km(g["node_lat"][None, :].astype(np.float64), g["node_lon"][None, :].astype(np.float64), plat[:, None], plon[:, None])
    snap = nd.argmin(1); snap_km = nd[np.arange(len(ds)), snap]
    return {"km": km, "minutes": km / speed * 60.0, "hazard": hazard, "vuln": vuln, "congestion": congestion,
            "uncertainty": uncertainty, "elev": elev, "snap": snap, "snap_km": snap_km, "year": year,
            "places": [{"id": d["id"], "name": d["name"], "lat": d["lat"], "lon": d["lon"]} for d in ds]}


def _attrs(project: Path) -> dict:
    path = project / "data/processed/routing/road_graph.npz"
    graph(project)
    return _attributes(str(project), path.stat().st_mtime, features(project)["built_utc"])


def metadata(project: Path) -> dict:
    g = graph(project); a = _attrs(project)
    places = [{**p, "road_node_km": round(float(a["snap_km"][i]), 2), "trek_or_offroad": bool(a["snap_km"][i] > 2.0)}
              for i, p in enumerate(a["places"])]
    classes = [str(c) for c in g["classes"]]
    return {"status": "ROAD_GRAPH", "places": places, "default_weights": DEFAULT_WEIGHTS, "terms": TERMS,
            "formula": "cost (min) = α·time + (β·hazard + γ·vulnerability + δ·congestion + ε·uncertainty) · km",
            "graph": {"nodes": int(len(g["node_lat"])), "segments": int(len(g["edge_u"])),
                      "km_by_class": {c: round(float(a["km"][g["edge_class"] == i].sum())) for i, c in enumerate(classes)},
                      "source": "OpenStreetMap contributors (ODbL), Geofabrik central-zone extract"},
            "congestion_year": a["year"], "limitations": LIMITATIONS}


def _closures(spec, a, places_by_id) -> np.ndarray:
    blocked = np.zeros(len(a["km"]), dtype=bool)
    if spec is None:
        return blocked
    if not isinstance(spec, list) or len(spec) > 10:
        raise ValueError("closures must be a list of up to 10 items.")
    for c in spec:
        if not isinstance(c, dict):
            raise ValueError("Each closure must be an object.")
        r = c.get("radius_km", 5)
        if type(r) not in (int, float) or not 0.5 <= r <= 50:
            raise ValueError("radius_km must be between 0.5 and 50.")
        if "near" in c:
            p = places_by_id.get(c["near"])
            if p is None: raise ValueError("Unknown destination id in closure.")
            lat, lon = p["lat"], p["lon"]
        else:
            lat, lon = c.get("lat"), c.get("lon")
            if type(lat) not in (int, float) or type(lon) not in (int, float):
                raise ValueError("A closure needs 'near' (destination id) or lat and lon.")
        blocked |= _equi_km(a["_mlat"], a["_mlon"], lat, lon) <= r
    return blocked


def _search(g, a, cost, blocked, src, dst):
    from scipy.sparse import csr_matrix
    from scipy.sparse.csgraph import dijkstra
    ok = ~blocked
    u, v = g["edge_u"][ok], g["edge_v"][ok]; c = cost[ok]; idx = np.nonzero(ok)[0]
    two = ~g["edge_oneway"][ok]
    U = np.concatenate([u, v[two]]); V = np.concatenate([v, u[two]]); C = np.concatenate([c, c[two]]); I = np.concatenate([idx, idx[two]])
    order = np.lexsort((C, V, U))  # keep the cheapest of parallel segments
    U, V, C, I = U[order], V[order], C[order], I[order]
    first = np.ones(len(U), dtype=bool); first[1:] = (U[1:] != U[:-1]) | (V[1:] != V[:-1])
    U, V, C, I = U[first], V[first], C[first], I[first]
    n = len(g["node_lat"])
    m = csr_matrix((C + 1e-9, (U, V)), shape=(n, n))
    dist, pred = dijkstra(m, directed=True, indices=src, return_predecessors=True)
    if not np.isfinite(dist[dst]):
        return None
    lookup = {(int(a_), int(b_)): int(e) for a_, b_, e in zip(U, V, I)}
    path, node = [], dst
    while node != src:
        p = pred[node]; path.append(lookup[(int(p), int(node))]); node = p
    return path[::-1]


def _summary(g, a, path, names) -> dict:
    km = a["km"][path]; total = float(km.sum())
    wavg = lambda x: round(float((x[path] * km).sum() / total), 4) if total else 0.0
    offs = g["geo_offsets"]; geo = g["geo"]; coords = []
    nodes = [(g["edge_u"][e], g["edge_v"][e]) for e in path]
    prev_end = None
    for e, (eu, ev) in zip(path, nodes):
        seg = geo[offs[e]:offs[e + 1]].tolist()
        if prev_end is not None and prev_end == ev: seg = seg[::-1]  # traversed against stored direction
        elif prev_end is None and len(path) > 1 and eu in (g["edge_u"][path[1]], g["edge_v"][path[1]]): seg = seg[::-1]
        coords.extend(seg); prev_end = ev if seg[-1] == geo[offs[e + 1] - 1].tolist() else eu
    step = max(1, len(coords) // 1500)
    roads = {}
    for e in path:
        nm = names[g["edge_name"][e]] or "(unnamed road)"; roads[nm] = roads.get(nm, 0) + float(a["km"][e])
    return {"distance_km": round(total, 1), "time_min": round(float(a["minutes"][path].sum()), 1),
            "hazard_exposure": wavg(a["hazard"]), "exposure_km": round(float((a["hazard"][path] * km).sum()), 1),
            "vulnerability": wavg(a["vuln"]), "congestion": wavg(a["congestion"]), "uncertainty": wavg(a["uncertainty"]),
            "max_elevation_m": round(float(a["elev"][path].max())), "segments": len(path),
            "main_roads": [{"name": k, "km": round(v, 1)} for k, v in sorted(roads.items(), key=lambda x: -x[1])[:5]],
            "geometry": [[round(p[0], 5), round(p[1], 5)] for p in coords[::step]]}


def route(project: Path, payload: object) -> dict:
    if not isinstance(payload, dict) or set(payload) - {"from", "to", "weights", "closures"}:
        raise ValueError("Expected from, to, and optional weights and closures.")
    g = graph(project); a = dict(_attrs(project)); a["_mlat"], a["_mlon"] = g["mid_lat"], g["mid_lon"]
    places = {p["id"]: i for i, p in enumerate(a["places"])}
    src_id, dst_id = payload.get("from"), payload.get("to")
    if src_id not in places or dst_id not in places or src_id == dst_id:
        raise ValueError("from and to must be two different destination ids.")
    w = dict(DEFAULT_WEIGHTS)
    given = payload.get("weights") or {}
    if not isinstance(given, dict) or set(given) - set(w):
        raise ValueError("weights may set alpha, beta, gamma, delta, epsilon.")
    for k, v in given.items():
        if type(v) not in (int, float) or not 0 <= v <= 20: raise ValueError("Each coefficient must be between 0 and 20.")
        w[k] = float(v)
    if w["alpha"] <= 0: raise ValueError("alpha (travel time) must be above zero.")
    blocked = _closures(payload.get("closures"), a, {p["id"]: p for p in a["places"]})
    src, dst = int(a["snap"][places[src_id]]), int(a["snap"][places[dst_id]])
    names = [str(n) for n in g["names"]]
    risk = (w["beta"] * a["hazard"] + w["gamma"] * a["vuln"] + w["delta"] * a["congestion"] + w["epsilon"] * a["uncertainty"]) * a["km"]
    base_path = _search(g, a, w["alpha"] * a["minutes"], blocked, src, dst)
    risk_path = _search(g, a, w["alpha"] * a["minutes"] + risk, blocked, src, dst)
    out = {"status": "ROUTE_COMPARISON", "from": a["places"][places[src_id]], "to": a["places"][places[dst_id]],
           "weights": w, "closed_segments": int(blocked.sum()),
           "snap_km": {"from": round(float(a["snap_km"][places[src_id]]), 2), "to": round(float(a["snap_km"][places[dst_id]]), 2)}}
    if base_path is None or risk_path is None:
        out["status"] = "NO_ROUTE"
        out["detail"] = "The closures cut every road connection between these places. Reduce a closure radius or remove one."
        out["limitations"] = LIMITATIONS; return out
    sp, ra = _summary(g, a, base_path, names), _summary(g, a, risk_path, names)
    pct = lambda x, y: round((y - x) / x * 100, 1) if x else None
    out.update({"shortest_time": sp, "risk_aware": ra,
                "comparison": {"time_change_pct": pct(sp["time_min"], ra["time_min"]), "distance_change_pct": pct(sp["distance_km"], ra["distance_km"]),
                               "exposure_change_pct": pct(sp["exposure_km"], ra["exposure_km"]),
                               "same_route": base_path == risk_path},
                "explanation": {"formula": "cost (min) = α·time + (β·hazard + γ·vulnerability + δ·congestion + ε·uncertainty) · km",
                                "data": {"roads": "OpenStreetMap (ODbL), central-zone extract", "hazard": "NASA POWER 2000–2024 means",
                                         "congestion": f"UTDB visitors {a['year']}"}},
                "limitations": LIMITATIONS})
    return out
