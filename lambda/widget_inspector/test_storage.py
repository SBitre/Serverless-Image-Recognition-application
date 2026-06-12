# --- Prefix mapping tests (added to fix the inspected/fail vs inspected/failed bug) ---

from storage import build_result_key


def test_build_result_key_pass_uses_passed_prefix():
    key = build_result_key("PASS", "2026-06-12T19:45:55.000Z", "test-uuid")
    assert key == "inspected/passed/2026/06/12/test-uuid.json"


def test_build_result_key_fail_uses_failed_prefix():
    key = build_result_key("FAIL", "2026-06-12T19:45:55.000Z", "test-uuid")
    assert key == "inspected/failed/2026/06/12/test-uuid.json"


def test_build_result_key_needs_review_uses_dashed_prefix():
    key = build_result_key("NEEDS_REVIEW", "2026-06-12T19:45:55.000Z", "test-uuid")
    assert key == "inspected/needs-review/2026/06/12/test-uuid.json"


def test_build_result_key_unknown_status_raises():
    with pytest.raises(ValueError, match="Unknown status"):
        build_result_key("WEIRD", "2026-06-12T19:45:55.000Z", "test-uuid")