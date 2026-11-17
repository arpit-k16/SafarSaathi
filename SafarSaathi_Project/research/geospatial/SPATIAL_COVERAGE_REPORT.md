# Actual geographic coverage

The audit bbox is (77.24, 28.61, 81.45, 31.63) in longitude/latitude. All 29 POWER points are inside it; archived dates are retained per point in COORDINATE_VALIDATION.csv. The available full PBF data are northern-zone (223,511,106 bytes) and central-zone (351,565,542 bytes). Other regional .poly boundaries are not road datasets. There is no full-India or Nepal-specific operational road/hazard/exposure dataset integrated here.

The northern-zone file is the actual source of the derived pilot road/river/hospital audit; do not extrapolate these counts to India, or apply them to Rasuwagadhi in Nepal. OSM attribution: (c) OpenStreetMap contributors, ODbL 1.0; preserve attribution and applicable derived-database share-alike terms. Hospitals/roads are OSM-tagged objects, not independently surveyed contemporary infrastructure.

Satellite scene footprints and actual data footprints have individual coverage checks in SCENE_INVENTORY.csv. A scene intersecting the pilot bbox does not cover every tourism point, and a catalogue wrapper name does not establish pixel coverage or processing-baseline equivalence.
