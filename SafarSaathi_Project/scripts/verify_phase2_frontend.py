"""Audit authorized integration edits against the complete pre-Phase-2 backup."""
import hashlib
import json
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[1]
ALLOWED = {
    'package.json', 'vite.config.js', 'src/App.jsx', 'src/components/Header.jsx',
    'src/components/Sidebar.jsx', 'src/pages/AuxiliaryView.jsx',
    'src/pages/OverviewDashboard.jsx', 'src/pages/DestinationDigitalTwin.jsx',
    'src/pages/DisasterMode.jsx', 'src/pages/WhatIfSimulator.jsx', 'src/pages/LandingPage.jsx',
}


def hashes(root):
    result = {}
    for file in root.rglob('*'):
        if file.is_file():
            with file.open('rb') as stream:
                result[file.relative_to(root).as_posix()] = hashlib.file_digest(stream, 'sha256').hexdigest()
    return result


def main():
    original = {r['path']: r['sha256'] for r in json.loads((PROJECT / 'integration_docs/frontend_phase2_original.json').read_text())}
    current = hashes(PROJECT / 'frontend')
    backup = hashes(PROJECT / 'integration_docs/phase2_frontend_backup_20261030_082633/frontend')
    removed = sorted(original.keys() - current.keys())
    modified = sorted(k for k in original.keys() & current.keys() if original[k] != current[k])
    unexpected = sorted(set(modified) - ALLOWED)
    result = {
        'original_files': len(original), 'current_files': len(current),
        'modified_original_files': modified, 'added_files': sorted(current.keys() - original.keys()),
        'removed_original_files': removed, 'unexpected_modified_files': unexpected,
        'backup_matches_original_sha256': backup == original,
        'all_css_assets_lockfile_and_dependencies_unchanged': not unexpected and not removed,
        'passed': not removed and not unexpected and backup == original,
    }
    (PROJECT / 'integration_docs/phase2_frontend_verification.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
    print(json.dumps(result, indent=2))
    raise SystemExit(0 if result['passed'] else 1)


if __name__ == '__main__':
    main()
