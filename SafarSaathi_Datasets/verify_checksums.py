#!/usr/bin/env python3
"""
Verify the integrity of the SafarSaathi raw dataset collection.

Usage (from the folder that contains CHECKSUMS.txt):

    python verify_checksums.py            # verify everything
    python verify_checksums.py --sample 20

Recomputes the SHA-256 of every listed file and compares it with the recorded
digest. It only READS the data files; it never writes, moves or modifies them.

Exit code 0 = everything verified, 1 = at least one mismatch or missing file.
"""
import argparse
import hashlib
import os
import random
import sys

BUF = 1024 * 1024


def parse(path):
    rows = []
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            if line.startswith("#") or not line.strip():
                continue
            parts = line.rstrip("\n").split("  ", 3)
            if len(parts) != 4:
                continue
            digest, size, mtime, rel = parts
            rows.append((digest, int(size), mtime, rel))
    return rows


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        while True:
            b = fh.read(BUF)
            if not b:
                break
            h.update(b)
    return h.hexdigest()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("checksum_file", nargs="?", default="CHECKSUMS.txt")
    ap.add_argument("--sample", type=int, default=0,
                    help="randomly verify only N files (faster smoke test)")
    a = ap.parse_args()

    if not os.path.exists(a.checksum_file):
        print(f"cannot find {a.checksum_file}")
        return 1

    rows = parse(a.checksum_file)
    if not rows:
        print("no checksum records found")
        return 1

    if a.sample and a.sample < len(rows):
        random.seed(20261003)
        rows = random.sample(rows, a.sample)
        print(f"sampling {len(rows)} of the recorded files\n")
    else:
        print(f"verifying {len(rows)} files\n")

    bad, missing, mismatched_size, ok = [], [], [], 0
    for digest, size, _mtime, rel in rows:
        if not os.path.exists(rel):
            missing.append(rel)
            continue
        actual_size = os.path.getsize(rel)
        if actual_size != size:
            mismatched_size.append((rel, size, actual_size))
        if sha256(rel) == digest:
            ok += 1
        else:
            bad.append(rel)

    for rel in missing:
        print(f"MISSING   {rel}")
    for rel, exp, act in mismatched_size:
        print(f"SIZE      {rel}  recorded={exp} actual={act}")
    for rel in bad:
        print(f"MISMATCH  {rel}")

    print(f"\nverified OK : {ok}")
    print(f"missing     : {len(missing)}")
    print(f"size differs: {len(mismatched_size)}")
    print(f"hash differs: {len(bad)}")
    return 1 if (missing or bad or mismatched_size) else 0


if __name__ == "__main__":
    sys.exit(main())