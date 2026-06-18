"""
P1 failure tests: CLI flag routing, build-all aggregation.

Each test encodes a known P1 bug as a reproducible red test.
Tests fail with the current code and will pass when Stage 2 fixes are applied.
"""
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO_ROOT / "scripts"))


# --- P1-7: build-all --offline flag forwarding (brandkit:78-86) ---
# --offline is translated to --dry-run which the nested CLI doesn't understand.
# Child failures are swallowed.

@pytest.mark.xfail(reason="P1: build-all --offline forwards wrong flag; child failures swallowed")
def test_build_all_offline_no_api_calls():
    """build-all --offline must never make API calls (no credential = no network)."""
    result = subprocess.run(
        ["bash", "scripts/brandkit", "build-all", "--offline"],
        capture_output=True, text=True, cwd=REPO_ROOT,
        timeout=60,
    )
    stdout_lower = result.stdout.lower()
    stderr_lower = result.stderr.lower()
    # Offline mode should not mention API keys or provider URLs
    assert "api_key" not in stdout_lower
    assert "token" not in stdout_lower or "sensenova" not in stdout_lower


@pytest.mark.xfail(reason="P1: build-all child failures swallowed (brandkit:78-86)")
def test_build_all_returns_nonzero_on_child_fail():
    """build-all must return non-zero when any child campaign fails."""
    # Inject a broken campaign YAML temporarily
    tmp_campaign = REPO_ROOT / "campaigns" / "_tmp_fail.yaml"
    try:
        tmp_campaign.write_text("campaign:\n  bad: true")
        result = subprocess.run(
            ["bash", "scripts/brandkit", "build-all", "--offline"],
            capture_output=True, text=True, cwd=REPO_ROOT,
            timeout=60,
        )
        assert result.returncode != 0, "build-all must return non-zero when a child fails"
        assert "All campaigns built" not in result.stdout
    finally:
        if tmp_campaign.exists():
            tmp_campaign.unlink()


# --- P1-6: Background API failure silently becomes placeholder (background_generator.py:129-145) ---
# Online credential absence or API failure silently becomes a placeholder.
# This requires structural fix to the generator. Documented for Stage 2.
