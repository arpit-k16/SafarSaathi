"""Destination-level visitor counts from Uttarakhand Tourism (UTDB) statistics PDFs.

Each PDF holds a table of 28 major destinations with Indian, foreign and total
visitors per year. Rows always appear in the same order, so values are read in
order and every row is checked: Indian + foreign must equal the printed total.
"""
from __future__ import annotations

import csv
import hashlib
import json
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path

# Official UTDB destination rows, in table order, mapped to the NASA POWER location ids used by the console.
DESTINATIONS = [
    ("Dehradun", "dehradun"), ("Rishikesh", "rishikesh"), ("Mussoorie", "mussoorie"), ("Pauri", "pauri"),
    ("Srinagar (Garhwal)", "srinagar-pauri-garhwal"), ("Kotdwar", "kotdwar"),
    ("Rudraprayag (excl. Kedarnath)", "rudraprayag"), ("Kedarnath", "kedarnath"), ("Gopeshwar", "gopeshwar"),
    ("Joshimath", "joshimath"), ("Badrinath", "badrinath"), ("Auli", "auli"), ("Hemkund Sahib", "hemkund-sahib"),
    ("Valley of Flowers", "valley-of-flowers"), ("Tehri", "tehri"), ("Uttarkashi", "uttarkashi"),
    ("Gangotri", "gangotri"), ("Yamunotri", "yamunotri"), ("Haridwar", "haridwar"), ("Almora", "almora"),
    ("Ranikhet", "ranikhet"), ("Kausani & Bageshwar", "kausani"), ("Pithoragarh", "pithoragarh"),
    ("Champawat", "champawat"), ("Nainital", "nainital"), ("Kathgodam", "kathgodam"),
    ("Corbett National Park", "corbett-national-park"), ("Udham Singh Nagar", "udham-singh-nagar"),
]
SOURCES = ["UKD_stats_2000_2020.pdf", "UKD_stats_2021_2023.pdf", "UKD_stats_2024.pdf"]
CROSS_CHECKS = ["UKD_stats_2000_2002.pdf", "UKD_stats_2021.pdf"]
SKIP = re.compile(r"Statistics|Indian|Name of|^\s*Sl\.|^\s*No\.|^\s*S\.No", re.I)


def _text(pdf: Path) -> str:
    return subprocess.run(["pdftotext", "-layout", str(pdf), "-"], check=True, capture_output=True,
                          text=True, encoding="utf-8", errors="replace").stdout


def parse_pdf(pdf: Path) -> dict[int, list[dict]]:
    """Return {year: [row per destination]} after validating every Indian+foreign=total triple."""
    blocks, current = [], None
    for line in _text(pdf).splitlines():
        years = [int(y) for y in re.findall(r"Year\s*(\d{4})", line)]
        if years:
            if current is not None and not current["numbers"]:
                current["years"] = years  # second header line of the same table
            else:
                current = {"years": years, "numbers": []}; blocks.append(current)
            continue
        if current is None or not line.strip() or SKIP.search(line) or line.strip().lower().startswith("total"):
            continue
        body = re.sub(r"^\s*\d{1,2}(?=\s|$)", " ", line, count=1)  # drop the serial number
        current["numbers"].extend(int(n) for n in re.findall(r"(?<![\d.])\d+(?![\d.])", body))
    out: dict[int, list[dict]] = {}
    for block in blocks:
        width = 3 * len(block["years"])
        nums = block["numbers"]
        if len(nums) != width * len(DESTINATIONS):
            raise ValueError(f"{pdf.name} {block['years']}: expected {width * len(DESTINATIONS)} values, found {len(nums)}")
        for r, (name, dest_id) in enumerate(DESTINATIONS):
            row = nums[r * width:(r + 1) * width]
            for k, year in enumerate(block["years"]):
                indian, foreign, total = row[3 * k:3 * k + 3]
                out.setdefault(year, []).append({"year": year, "destination": name, "id": dest_id, "indian": indian,
                                                 "foreign": foreign, "total": total, "sum_check": indian + foreign == total})
    return out


def build(project: Path) -> dict:
    raw = project / "data/raw_v2/tourism_utdb"
    out_dir = project / "data/processed/utdb_destinations"
    out_dir.mkdir(parents=True, exist_ok=True)
    rows, files = {}, {}
    for name in SOURCES:
        parsed = parse_pdf(raw / name)
        files[name] = {"sha256": hashlib.sha256((raw / name).read_bytes()).hexdigest(), "years": sorted(parsed)}
        for year, rs in parsed.items():
            rows.setdefault(year, rs)
    checks = []
    for name in CROSS_CHECKS:
        if (raw / name).exists():
            try:
                parsed = parse_pdf(raw / name)
            except ValueError as exc:
                checks.append({"file": name, "skipped": str(exc)}); continue
            for year, rs in parsed.items():
                if year in rows:
                    diff = sum(a["total"] != b["total"] for a, b in zip(rs, rows[year]))
                    checks.append({"file": name, "year": year, "rows_differing": diff})
    flat = [r for y in sorted(rows) for r in rows[y]]
    with open(out_dir / "visits.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(flat[0])); w.writeheader(); w.writerows(flat)
    bad = [f"{r['year']} {r['destination']}" for r in flat if not r["sum_check"]]
    prov = {"built_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"), "source": "Uttarakhand Tourism Development Board, Tourist Statistics of Major Tourist Destinations",
            "files": files, "years": [min(rows), max(rows)], "rows": len(flat), "destinations": len(DESTINATIONS),
            "sum_check_failures": bad, "cross_checks": checks,
            "csv_sha256": hashlib.sha256((out_dir / "visits.csv").read_bytes()).hexdigest(),
            "limitations": ["Annual counts reported by UTDB; not daily or seasonal footfall.",
                            "Kausani and Bageshwar are reported together; mapped to the Kausani climate point.",
                            "Haridwar and Rishikesh totals include large religious gatherings (e.g. Kanwar, Kumbh)."]}
    (out_dir / "provenance.json").write_text(json.dumps(prov, indent=2), encoding="utf-8")
    return prov


def load_visits(project: Path) -> list[dict]:
    path = project / "data/processed/utdb_destinations/visits.csv"
    with open(path, encoding="utf-8") as fh:
        return [{**r, "year": int(r["year"]), "indian": int(r["indian"]), "foreign": int(r["foreign"]), "total": int(r["total"])} for r in csv.DictReader(fh)]


if __name__ == "__main__":
    import sys
    print(json.dumps(build(Path(sys.argv[1] if len(sys.argv) > 1 else ".")), indent=2))
