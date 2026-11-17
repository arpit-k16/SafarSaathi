# End-to-end verification

The requested empirical chain is only partially supported. Each connection is separately recorded in SYSTEM_VALIDATION_MATRIX.csv. A passing software test is not geographic or event validation.

Before modifications: 153 backend tests passed, no skips; 9 frontend tests passed, no skips; build and lint passed. Checkpoint and logs are in ../_baseline.

Final backend XML counts:

```json
{
  "tests": 181,
  "failures": 0,
  "errors": 0,
  "skipped": 0
}
```

Final frontend results: ../frontend_tests.log; build: ../frontend_build.log; lint: ../frontend_lint.log. The first frontend rerun skipped its server-dependent case; the subsequent configured API run supersedes it. New optimization/HTTP/hardening tests initially passed 28/28. Final full-suite XML is authoritative.

Geographic checks:

```json
{
  "checks_passed": [
    "finite/ranged coordinate acceptance and invalid rejection",
    "ellipsoidal zero and known one-degree longitude distance",
    "native lon-lat pilot geometry validity/containment",
    "shared-node component union/find"
  ],
  "status": "PASS",
  "coordinate_rows": 29,
  "all_native_points_valid": true,
  "all_query_points_valid": true,
  "source_md5_match": true,
  "satellite_checksum_mismatches": 0,
  "runtime_seconds": 310.29969189999974
}
```

Controlled tests cover missing/infeasible/invalid/nonfinite inputs, unavailable metadata and malformed flood outputs. Model audit recomputed all six stored metric sets. Scenario audit independently checked 21 sensitivity cases; optimizer audit ran 18 primary cases with repeated seeds and six budget checks. Neither test suite connects Nepal observations to local tourist stress: those aligned inputs are absent.
