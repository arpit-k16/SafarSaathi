"""Compare every protected file against the initial manifest, without raw writes."""
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path


def verify(project):
    protected = project / 'frontend'
    expected = {r['path']: r for r in json.loads(
        (project / 'integration_docs/frontend_sha256_original.json').read_text(encoding='utf-8-sig'))}
    actual = {}
    for file in protected.rglob('*'):
        if file.is_file():
            with file.open('rb') as stream:
                digest = hashlib.file_digest(stream, 'sha256').hexdigest()
            actual[file.relative_to(protected).as_posix()] = {
                'size': file.stat().st_size, 'sha256': digest}
    added, removed = sorted(actual.keys() - expected.keys()), sorted(expected.keys() - actual.keys())
    changed = sorted(k for k in actual.keys() & expected.keys()
                     if actual[k]['sha256'] != expected[k]['sha256'] or actual[k]['size'] != expected[k]['size'])
    return {'verified_utc': datetime.now(timezone.utc).isoformat(),
            'original_files': len(expected), 'current_files': len(actual),
            'added': added, 'removed': removed, 'changed': changed,
            'unchanged': not (added or removed or changed)}


if __name__ == '__main__':
    root = Path(__file__).resolve().parents[1]
    result = verify(root)
    (root / 'integration_docs/frontend_verification.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
    print(json.dumps(result, indent=2))
    raise SystemExit(0 if result['unchanged'] else 1)
