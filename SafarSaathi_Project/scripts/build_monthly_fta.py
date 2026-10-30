"""Extract reconciled monthly FTA observations from immutable local official tables."""
import argparse
import csv
import hashlib
import json
from pathlib import Path
import re

from pypdf import PdfReader

MONTHS = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December']
TABLES = [
    ('INDIA TOURISM STATISTICS 2022 (master-tourism.digifootprint.gov.in).pdf', [36], [2019, 2020, 2021], '2.3.1'),
    ('India Tourism Statistics 2023-English (1).pdf', [31], [2020, 2021, 2022], '2.3.1'),
    ('India Tourism Data Compendium 2024.pdf', [52, 53], [2021, 2022, 2023], '2.3.1'),
    ('India Tourism Data Compendium 2025_1.pdf', [48], [2019, 2023, 2024], '2.2.1'),
]


def extract(project):
    raw = project.parent / 'SafarSaathi_Datasets/raw/tourism_india'
    destination = project / 'data/processed/tourism_monthly_fta/20261025'
    destination.mkdir(parents=True, exist_ok=False)
    observations, audits = {}, []
    pattern = re.compile(r'^(' + '|'.join(MONTHS) + r')\s+([\d,]+)\s+([\d,]+)\s+([\d,]+)\b', re.MULTILINE)
    for name, pages, years, table in TABLES:
        path = raw / name
        reader = PdfReader(path)
        text = '\n'.join(reader.pages[p - 1].extract_text() or '' for p in pages)
        # Keep just the first table's rows through its first total, excluding following NRI tables.
        total = re.search(r'^\s*Total\s+([\d,]+)\s+([\d,]+)\s+([\d,]+)\b', text, re.MULTILINE)
        if not total: raise ValueError('Missing printed total in ' + name)
        rows = pattern.findall(text[:total.start()])
        if len(rows) != 12 or [r[0] for r in rows] != MONTHS: raise ValueError('Incomplete/ambiguous monthly table: ' + name)
        counts = [[int(value.replace(',', '')) for value in row[1:]] for row in rows]
        expected = [int(v.replace(',', '')) for v in total.groups()]
        if [sum(r[i] for r in counts) for i in range(3)] != expected:
            raise ValueError('Monthly rows do not reconcile to printed annual totals: ' + name)
        source = {'path': path.relative_to(project.parent).as_posix(), 'sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
                  'bytes': path.stat().st_size, 'pdf_pages': pages, 'table': table, 'years': years,
                  'monthly_sum_matches_printed_total': True}
        audits.append(source)
        for month, values in enumerate(counts, 1):
            for year, value in zip(years, values):
                date = f'{year}-{month:02d}'
                if date in observations and observations[date]['arrivals'] != value:
                    raise ValueError('Conflicting official vintages for ' + date)
                if date not in observations: observations[date] = {'destination': 'IND', 'date': date, 'arrivals': value, 'sources': []}
                observations[date]['sources'].append({'pdf': name, 'pages': pages, 'table': table})
    dates = sorted(observations)
    if dates != [f'{year}-{month:02d}' for year in range(2019, 2025) for month in range(1, 13)]:
        raise ValueError('Expected exactly 72 contiguous observed months, 2019–2024.')
    csv_path = destination / 'monthly_fta.csv'
    with csv_path.open('x', newline='', encoding='utf-8') as handle:
        writer = csv.DictWriter(handle, fieldnames=['destination', 'date', 'arrivals'])
        writer.writeheader(); writer.writerows({k: observations[d][k] for k in writer.fieldnames} for d in dates)
    report = {'target': 'Foreign Tourist Arrivals (FTAs), excluding non-resident Indian arrivals',
              'units': 'arrivals per calendar month; repeated arrivals count separately', 'geography': 'India national total',
              'frequency': 'monthly', 'first_observed': dates[0], 'last_observed': dates[-1], 'rows': len(dates),
              'missing_periods': [], 'duplicate_keys_after_reconciliation': 0, 'conflicting_values': 0, 'imputation': 'none',
              'sources': audits, 'observation_provenance': {d: observations[d]['sources'] for d in dates},
              'derived_csv_sha256': hashlib.sha256(csv_path.read_bytes()).hexdigest(),
              'target_separation': 'Do not splice into World Bank ITA totals: ministry ITA includes FTA+NRI from 2014; pre-2014 World Bank series has a definition discontinuity.',
              'publication': 'Official 2022/2023 tourism statistics and 2024/2025 compendiums, Bureau of Immigration via Ministry of Tourism.',
              'license': 'Project-local source documentation identifies Government of India public-use/GODL where applicable; retain attribution and check publication restrictions.',
              'attribution': 'Source: Ministry of Tourism, Government of India — Research & Analytics Division; underlying data: Bureau of Immigration.',
              'limitations': ['Revised publication vintages, not real-time vintage backtests.', 'National counts, not destination stress or occupancy labels.',
                             'COVID disruptions dominate 2020–2022; only six annual cycles available.', 'No observations after December 2024 were inferred or filled.']}
    with (destination / 'provenance.json').open('x', encoding='utf-8') as handle: json.dump(report, handle, indent=2)
    print(json.dumps({k: report[k] for k in ['rows', 'first_observed', 'last_observed', 'conflicting_values', 'target']}, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(); parser.add_argument('--project', type=Path, required=True)
    extract(parser.parse_args().project)
