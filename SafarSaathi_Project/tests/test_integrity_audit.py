from safarsaathi_ml.pipeline import discover


def test_fast_and_full_checksum_policy(tmp_path):
    root = tmp_path / "raw" / "reviews"; root.mkdir(parents=True)
    (root / "small.txt").write_text("safe", encoding="utf-8")
    (root / "large.bin").write_bytes(b"x" * 20)
    fast = discover(raw_roots=(tmp_path / "raw",), hash_max_bytes=10)
    assert set(fast.hash_status) == {"verified", "skipped_size_limit"}
    full = discover(raw_roots=(tmp_path / "raw",), checksum_mode="full")
    assert set(full.hash_status) == {"verified"}
    assert full.sha256.notna().all()
