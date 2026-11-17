import json, math, sys
from collections import Counter, defaultdict
import numpy as np
from shapely.geometry import LineString
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import connected_components

ways = json.load(open("ways.json"))
CLS = ["motorway", "trunk", "primary", "secondary", "tertiary", "unclassified"]
def base(hw): return hw.replace("_link", "")
count = Counter()
for w in ways:
    refs = [p[0] for p in w["pts"]]
    count.update(set(refs)); count[refs[0]] += 1; count[refs[-1]] += 1
def hav(a, b):
    la1, lo1, la2, lo2 = map(math.radians, (a[0], a[1], b[0], b[1]))
    h = math.sin((la2-la1)/2)**2 + math.cos(la1)*math.cos(la2)*math.sin((lo2-lo1)/2)**2
    return 2*6371.0*math.asin(math.sqrt(h))
node_id, node_ll = {}, []
def nid(ref, lat, lon):
    if ref not in node_id: node_id[ref] = len(node_ll); node_ll.append((lat, lon))
    return node_id[ref]
edges = []  # u, v, km, cls, oneway, name, coords
names = {"": 0}; name_list = [""]
for w in ways:
    pts = w["pts"]; seg = [pts[0]]
    for p in pts[1:]:
        seg.append(p)
        if count[p[0]] >= 2 or p is pts[-1]:
            if len(seg) >= 2 and seg[0][0] != seg[-1][0]:
                km = sum(hav(seg[i][1:], seg[i+1][1:]) for i in range(len(seg)-1))
                nm = w["name"]
                if nm not in names: names[nm] = len(name_list); name_list.append(nm)
                coords = [(s[1], s[2]) for s in seg]
                if len(coords) > 2:
                    simp = LineString([(c[1], c[0]) for c in coords]).simplify(0.0003)  # ~30 m
                    coords = [(y, x) for x, y in simp.coords]
                edges.append((nid(*seg[0]), nid(*seg[-1]), km, CLS.index(base(w["hw"])), w["oneway"], names[nm], coords))
            seg = [p]
n = len(node_ll)
u = np.array([e[0] for e in edges]); v = np.array([e[1] for e in edges])
g = coo_matrix((np.ones(len(edges)), (u, v)), shape=(n, n))
ncomp, lab = connected_components(g, directed=False)
big = np.bincount(lab).argmax()
keep_nodes = np.where(lab == big)[0]; remap = -np.ones(n, dtype=np.int64); remap[keep_nodes] = np.arange(len(keep_nodes))
E = [e for e in edges if lab[e[0]] == big]
lat = np.array([node_ll[i][0] for i in keep_nodes], dtype=np.float32); lon = np.array([node_ll[i][1] for i in keep_nodes], dtype=np.float32)
flat, offs = [], [0]
for e in E:
    flat.extend(e[6]); offs.append(len(flat))
geo = np.array(flat, dtype=np.float32)
np.savez_compressed("road_graph.npz", node_lat=lat, node_lon=lon,
    edge_u=remap[[e[0] for e in E]].astype(np.int32), edge_v=remap[[e[1] for e in E]].astype(np.int32),
    edge_km=np.array([e[2] for e in E], dtype=np.float32), edge_class=np.array([e[3] for e in E], dtype=np.int8),
    edge_oneway=np.array([e[4] for e in E], dtype=bool), edge_name=np.array([e[5] for e in E], dtype=np.int32),
    geo=geo, geo_offsets=np.array(offs, dtype=np.int64), names=np.array(name_list), classes=np.array(CLS))
print("nodes", n, "->", len(keep_nodes), "edges", len(edges), "->", len(E), "components", ncomp, "geo pts", len(geo))
print("km total", round(sum(e[2] for e in E)), "by class", Counter(CLS[e[3]] for e in E))
