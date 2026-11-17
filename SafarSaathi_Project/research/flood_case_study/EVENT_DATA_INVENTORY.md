# Event data inventory

The source-verification result does **not** establish that suitable numerical event inputs and labels are installed. `local_event_inventory.json` records executed local checks, source CSV hashes and the coverage used below.

| Evidence class | Actual availability | Suitability for this case |
|---|---|---|
| Government/scientific event records | Primary web pages directly opened; links/statuses in event_sources.json | Establish the date/corridor and uncertainty, not machine-readable hydrology or labels. |
| Raw local Sentinel-1/2 collection | Original product IDs and manifest coverage inspected; zero product IDs containing 2026 | Declared Uttarakhand footprint is 77.24–81.45°E, 28.61–31.63°N. No event-bracketing Nepal acquisition was identified. |
| STURM Sentinel-1 metadata | **21,602** rows; acquisitions 2017-12-12 through 2022-10-12; **0** Nepal-country rows and **0** rows on the event date | Benchmark data are not 2026 Rasuwagadhi observations or labels. |
| STURM Sentinel-2 metadata | **2,675** rows; acquisitions 2018-04-13 through 2022-08-31; **0** Nepal-country rows and **0** rows on the event date | Same temporal/geographic mismatch. |
| Local weather/source locations | Archived Uttarakhand regional/named-location sources | Not Nepal event gauges or observed rainfall. No forcing series transplanted. |
| Roads, rivers, hospitals, tourism points | Northern India sources exist; no dedicated Nepal-named event data path found in baseline inventory | Filename discovery is not exhaustive content proof. No Nepal asset layer, topology or route state has been validated for this case. |
| National tourism statistics | All-country World Bank sources may include Nepal annual figures | Cannot be converted into event-day tourist presence/exposure. |
| Candidate reference mapping | EMSR927 and UNOSAT product 4257 identified as remote leads | Activation page timed out; UNOSAT page was a JavaScript shell. No original vectors, CRS, label semantics or imagery alignment were loaded/validated locally. |
| Ground-truth hydrographs, flood masks, damage/closure inventories | Not loaded for this event | Quantitative skill, overlap, exposure and accessibility calculations remain blocked. |

## Reproduce

From the application root: `python scripts/phase3_event_sources.py`. This reads source manifests/metadata only and writes derived inventory evidence under this directory. It does not download imagery, alter raw data, or claim fresh remote verification. Web pages may change after the recorded retrieval date.

Input paths and provenance: sibling `SafarSaathi_Datasets/DATA_MANIFEST.csv`; `data/external/sturm_flood/12748983/Sentinel1_metadata.csv`; `Sentinel2_metadata.csv`; and `research/_baseline/dataset_inventory.json`. Exact hashes, mission dates and country lists are in the JSON evidence. No large satellite product was downloaded for this case study.
