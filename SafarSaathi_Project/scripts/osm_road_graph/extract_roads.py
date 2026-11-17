"""Extract Uttarakhand drivable main roads from a Geofabrik .osm.pbf into a compact graph."""
import json, math, sys, time
import osmium
import numpy as np

PBF = sys.argv[1]; OUT = sys.argv[2]
BBOX = (77.55, 28.70, 81.05, 31.47)  # lon_min, lat_min, lon_max, lat_max
CLASSES = {"motorway": 80, "trunk": 50, "primary": 40, "secondary": 32, "tertiary": 26, "unclassified": 20,
           "motorway_link": 40, "trunk_link": 35, "primary_link": 30, "secondary_link": 25, "tertiary_link": 20}
t0 = time.time()
fp = osmium.FileProcessor(PBF).with_locations("flex_mem").with_filter(osmium.filter.KeyFilter("highway"))
ways = []
for obj in fp:
    if not obj.is_way(): continue
    hw = obj.tags.get("highway")
    if hw not in CLASSES: continue
    pts = []
    for n in obj.nodes:
        if not n.location.valid(): continue
        lon, lat = n.location.lon, n.location.lat
        pts.append((n.ref, lat, lon))
    if not pts: continue
    if not any(BBOX[0] <= p[2] <= BBOX[2] and BBOX[1] <= p[1] <= BBOX[3] for p in pts): continue
    ms = obj.tags.get("maxspeed", "")
    try: speed = float(ms.split()[0]) if ms else None
    except ValueError: speed = None
    ways.append({"hw": hw, "name": obj.tags.get("name:en") or obj.tags.get("name") or obj.tags.get("ref") or "", "ref": obj.tags.get("ref", ""),
                 "oneway": obj.tags.get("oneway") == "yes", "speed": speed, "pts": pts})
print("ways", len(ways), round(time.time() - t0), "s", flush=True)
json.dump(ways, open(OUT, "w"))
