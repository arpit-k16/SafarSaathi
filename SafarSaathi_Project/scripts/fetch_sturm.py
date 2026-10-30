"""User-approved bounded STURM-Flood download. Never modifies original datasets."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import time
from urllib.request import Request, urlopen

URL = 'https://zenodo.org/api/records/12748983'


def main():
    parser = argparse.ArgumentParser(); parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--download-approved', action='store_true')
    args = parser.parse_args(); args.output.mkdir(parents=True, exist_ok=True)
    with urlopen(Request(URL, headers={'User-Agent': 'SafarSaathi research data validation'}), timeout=45) as response:
        metadata = json.load(response)
    info = args.output / 'zenodo_record_12748983.json'
    if not info.exists(): info.write_text(json.dumps(metadata, indent=2), encoding='utf-8')
    entry = next(f for f in metadata['files'] if f['key'] == 'Dataset.zip')
    print(json.dumps({'size': entry['size'], 'checksum': entry['checksum'], 'license': metadata['metadata'].get('license'), 'url': entry['links']['self']}, indent=2), flush=True)
    if not args.download_approved: return
    size = entry['size']
    if size > 4_500_000_000: raise ValueError('Download exceeds approved approximately 4 GB scope.')
    # Train by streaming members directly from this archive; do not extract a second full copy.
    if shutil.disk_usage(args.output).free < size + 1_000_000_000:
        raise ValueError('Insufficient free disk for archive plus a 1 GB working reserve.')
    print('Archive-only storage; full extraction disabled. Members will be read in bounded batches.', flush=True)
    archive = args.output / 'Dataset.zip'
    if archive.exists():
        print('Existing completed archive retained; no overwrite.', flush=True); return
    partial = args.output / 'Dataset.zip.part'
    offset = partial.stat().st_size if partial.exists() else 0
    headers = {'User-Agent': 'SafarSaathi research data validation'}
    if offset: headers['Range'] = f'bytes={offset}-'
    digest, strong = hashlib.md5(), hashlib.sha256()
    if offset:
        with partial.open('rb') as existing:
            for block in iter(lambda: existing.read(1024 * 1024), b''): digest.update(block); strong.update(block)
    with urlopen(Request(entry['links']['self'], headers=headers), timeout=90) as response:
        if offset and response.status != 206: raise ValueError('Publisher did not honor resume range; original partial retained.')
        with partial.open('ab' if offset else 'xb') as handle:
            total, reported = offset, offset
            while block := response.read(1024 * 1024):
                total += len(block)
                if total > size: raise ValueError('Download exceeds publisher size.')
                handle.write(block); digest.update(block); strong.update(block)
                if total - reported >= 128 * 1024 * 1024:
                    print(f'Downloaded {total}/{size} bytes', flush=True); reported = total
    if total != size or f'md5:{digest.hexdigest()}' != entry['checksum']:
        raise ValueError('Publisher size/checksum validation failed; partial retained untrusted.')
    partial.rename(archive)
    (args.output / 'download_verification.json').write_text(json.dumps({'source': URL, 'bytes': total, 'md5': digest.hexdigest(), 'sha256': strong.hexdigest(), 'publisher_checksum_matched': True,
        'approval': 'User explicitly approved the approximately 4 GB download in this chat; no pretrained weights.'}, indent=2), encoding='utf-8')
    print('Download and publisher checksum PASS', flush=True)


if __name__ == '__main__': main()
