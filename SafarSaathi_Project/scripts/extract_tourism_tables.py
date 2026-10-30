"""Offline official-PDF extraction audit. Uses optional pypdf/pdfplumber tooling only."""
import argparse
import hashlib
import json
from pathlib import Path
import re

from pypdf import PdfReader


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--project', type=Path, required=True)
    args = parser.parse_args()
    source = args.project.parent / 'SafarSaathi_Datasets/raw/tourism_india'
    output = args.project / 'data/interim/tourism_pdf_audit_20261025'
    output.mkdir(parents=True, exist_ok=True)
    names = ['India Tourism Data Compendium 2025_1.pdf', 'India Tourism Data Compendium 2024.pdf',
             'India Tourism Statistics 2023-English (1).pdf', 'INDIA TOURISM STATISTICS 2022 (master-tourism.digifootprint.gov.in).pdf']
    for name in names:
        destination = output / (Path(name).stem + '.json')
        if destination.exists():
            print('Existing immutable extraction:', name, flush=True); continue
        path = source / name
        reader = PdfReader(path)
        selected = []
        for index in range(min(90, len(reader.pages))):
            text = reader.pages[index].extract_text() or ''
            upper = text.upper()
            if (('MONTH' in upper and ('ARRIVAL' in upper or 'FTA' in upper)) or
                ('1981' in text and '2024' in text) or ('1981' in text and '2023' in text) or
                ('1991' in text and '2024' in text and 'NRI' in upper)):
                selected.append({'pdf_page': index + 1, 'text': text})
        with destination.open('x', encoding='utf-8') as handle:
            json.dump({'source': path.name, 'source_sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
                       'page_count': len(reader.pages), 'pages_scanned': min(90, len(reader.pages)), 'selected_pages': selected}, handle, indent=2)
        print(name, 'selected PDF pages', [p['pdf_page'] for p in selected], flush=True)


if __name__ == '__main__': main()
