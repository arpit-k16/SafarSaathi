# Scenario tests

Run `python scripts/phase3_research.py` for the CSV and independent formula checks. Run `python -m pytest tests/test_integration_adapters.py tests/test_research_hardening.py -q` for bounds, missing keys, conservation, invalid/boolean/nonfinite/extreme inputs and safe model output handling. Final executed test counts are recorded centrally in research/end_to_end/END_TO_END_TEST_REPORT.md; this file does not assert unexecuted tests passed.
