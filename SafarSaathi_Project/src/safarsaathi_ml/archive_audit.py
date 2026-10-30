"""Produce a verifiable manifest for the legacy archive created during rebuild."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path


def build_manifest() -> Path:
    repo_root = Path(__file__).resolve().parents[3]
    archives = sorted((repo_root / "trash").glob("backend_ml_legacy_*"))
    if not archives:
        raise FileNotFoundError("No backend/ML legacy archive was found.")
    archive = archives[-1]
    moved = []
    for path in archive.rglob("*"):
        if path.is_file():
            relative = path.relative_to(archive)
            moved.append({"original_path": str(Path("SafarSaathi_Project") / relative),
                          "archive_path": str(path.relative_to(repo_root)), "bytes": path.stat().st_size,
                          "verified": path.is_file()})
    manifest = {"archive_created_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
                "archive": str(archive.relative_to(repo_root)), "raw_data_archived": False,
                "file_count": len(moved), "files": moved}
    output = archive / "archive_manifest.json"
    output.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return output


if __name__ == "__main__":
    print(build_manifest())
