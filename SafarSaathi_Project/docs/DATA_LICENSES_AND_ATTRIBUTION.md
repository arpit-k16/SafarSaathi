# Licences and Attribution — SafarSaathi Raw Dataset Collection

**Collection date:** 2026-10-03
**Scope:** every dataset under `raw/` in this folder.

This file is a plain-language summary of what each source allows. It is not legal
advice. Read the original licence text linked for each source before publishing
results, and reproduce the attributions below verbatim in any publication,
model card, dashboard or thesis chapter that uses these data.

---

## 1. Ministry of Tourism, Government of India — `raw/tourism_india/`

- **Attribution:** *Source: Ministry of Tourism, Government of India — Research &
  Analytics Division, India Tourism Data Portal (`data.tourism.gov.in`).*
- **Terms:** Published by the Government of India for public use. Content is
  generally available under the **Government Open Data Licence – India (GODL)**
  where the portal applies it, and is otherwise a Government work under the
  Copyright and Related Rights Act, 1957 (Section 52 permits reproduction of
  Government works). Individual publications may carry additional statements —
  check the publication itself before reuse.
- **Restrictions:** None identified for research use. Do not present the data as
  your own; always name the Ministry as the source.

---

## 2. NASA POWER — `raw/weather_nasa_power/`

- **Attribution:** *Data obtained from the NASA POWER project
  (power.larc.nasa.gov), NASA Langley Research Center. Underlying data:
  MERRA-2 reanalysis.*
- **Terms:** NASA Earth science data are **free, full and open**, with no
  restrictions on use or redistribution (NASA ESDIS data-use policy).
- **Restrictions:** None. Please cite the POWER project and the underlying
  reanalysis product (MERRA-2) when publishing.

---

## 3. OpenStreetMap via Geofabrik — `raw/osm_india/`

- **Attribution (mandatory):** *(c) OpenStreetMap contributors.*
- **Terms:** **Open Database License (ODbL) v1.0** —
  <https://opendatacommons.org/licenses/odbl/1-0/>
- **What ODbL requires you to do:**
  1. **Attribute** OpenStreetMap contributors on any public use (website, map,
     report, figure).
  2. **Share-alike:** if you produce a derived database from this data, you must
     release that derived database under the ODbL too.
- **Note:** Geofabrik strips user name, user id and changeset id from its
  extracts for data-protection reasons. The full metadata history is available
  to registered OpenStreetMap contributors only.
- **Geofabrik ask:** consider supporting the OpenStreetMap Foundation.

---

## 4. UNDRR Datum — `raw/disaster_undrr/`

- **Attribution:** *Source: United Nations Office for Disaster Risk Reduction
  (UNDRR), Datum platform — Hazard Information Profiles v1.0.0.*
- **Terms:** Per UNDRR's published terms, all data and metadata are available
  **free of charge** and may be **copied, duplicated and further distributed**
  provided UNDRR is cited as the reference. Third-party content and imagery
  remain under their original copyright and must be respected.
- **Restrictions:** None beyond attribution.

---

## 5. Copernicus Sentinel-1 and Sentinel-2 — `raw/sentinel1/`, `raw/sentinel2/`

- **Attribution:** *Contains modified Copernicus Sentinel data 20XX, processed by
  ESA / processed by [AWS Open Data mirror operator], [year of retrieval].*
- **Terms:** Sentinel data are **free, full and open** to all users under the
  **Copernicus Sentinel Data Legal Notice**:
  <https://sentinels.copernicus.eu/documents/247904/690755/Sentinel_Data_Legal_Notice>
  No fee is charged; there is no restriction on use, reproduction, distribution
  or exploitation, including commercial use.
- **IMPORTANT — SOURCE DEVIATION:** these products were **not** downloaded from
  the Copernicus Data Space Ecosystem. That service requires a registered
  account and an OAuth token (anonymous requests return
  `HTTP 401 DAT-ZIP-604 "Token not found"`). With the project owner's explicit
  approval they were taken from the **AWS Open Data** mirror instead:
  - `sentinel-s2-l2a` — Level-2A, original `.jp2` band data
  - `sentinel-s1-l1c` — Sentinel Hub / Element 84 distribution of GRD as
    **cloud-optimised GeoTIFF**, *not* the original SAFE structure
  The AWS copies are distributed under the same Copernicus open terms. Files
  were written under their official product names; object payloads were not
  altered. See `raw/sentinel1/SOURCE_INFO.txt` and `raw/sentinel2/SOURCE_INFO.txt`.

---

## 6. Tourism / hotel review datasets — `raw/reviews/`

These carry **per-dataset** licences and they differ. Check each row of
`DATA_MANIFEST.csv` and the bundled dataset cards before use.

| Dataset | Licence | Consequence |
|---|---|---|
| `argilla/tripadvisor-hotel-reviews` | **CC-BY-NC-4.0** | **Non-commercial use only.** Cannot be used for a commercial product. |
| `crawlfeeds/Booking-Hotel-Reviews-Dataset` | **CC-BY-NC-4.0** | **Non-commercial use only.** |
| `Aditya1010/17k-hotel-reviews-dataset` | **Apache-2.0** | Commercial use permitted, with attribution and notice. |

- **Attribution:** Cite the Hugging Face dataset repository for each dataset.
- **Note on provenance:** these originate from TripAdvisor and Booking.com
  review content collected by third parties. SafarSaathi did **not** scrape
  those sites — scraping them would breach their terms of service. Verify that
  your intended use is compatible with the upstream platform's terms as well as
  the declared dataset licence.
- **NC datasets:** if SafarSaathi ever becomes a commercial or
  government-deployed product, the two CC-BY-NC-4.0 corpora must be replaced.

---

## 7. World Bank / UN Tourism — `raw/worldbank_un_tourism/`

- **Attribution:** *Source: World Bank Open Data — World Development
  Indicators. Tourism indicators are compiled by the World Bank from UN Tourism
  (formerly UNWTO) source data.*
- **Terms:** **CC BY 4.0** (and CC BY 4.0 IGO where the World Bank applies the
  IGO variant). Free to share and adapt with attribution.
- **UN Tourism's own tables** were not collected: the UN Tourism Tourism
  Statistics Database sits behind a registration / request-access wall.

---

## Summary of obligations

| Source | Attribution required | Share-alike | Non-commercial |
|---|---|---|---|
| Ministry of Tourism | Yes | No | No |
| NASA POWER | Yes (cite) | No | No |
| OpenStreetMap | **Yes** | **Yes (ODbL)** | No |
| UNDRR Datum | **Yes** | No | No |
| Copernicus Sentinel-1/2 | **Yes (cite ESA/Copernicus)** | No | No |
| TripAdvisor reviews (HF) | Yes | No | **Yes** |
| Booking.com reviews (HF) | Yes | No | **Yes** |
| Hotel reviews (HF, Apache) | Yes + notice | No | No |
| World Bank | Yes | No | No |

**Only two obligations are easy to miss:** the ODbL share-alike on anything
derived from OpenStreetMap, and the **non-commercial** restriction on two of the
three review datasets.