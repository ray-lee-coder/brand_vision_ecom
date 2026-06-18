import json
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]


def test_five_beta_modification_trials_produce_boundary_evidence(tmp_path):
    report_path = tmp_path / "modification-report.json"
    result = subprocess.run(
        [
            sys.executable,
            "scripts/run_beta_modifications.py",
            "--output",
            str(report_path),
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        timeout=120,
    )

    assert result.returncode == 0, result.stderr + result.stdout
    report = json.loads(report_path.read_text())
    assert report["campaign"] == "acme-launch"
    assert report["generated_at"].endswith("Z")
    assert report["summary"] == {"total": 5, "passed": 5, "failed": 0}
    assert len(report["trials"]) == 5
    assert all(trial["status"] == "pass" for trial in report["trials"])
    assert all(trial["actual_model_calls"] == 0 for trial in report["trials"])
    assert all(trial["elapsed_seconds"] > 0 for trial in report["trials"])
    assert all(trial["mutation"] for trial in report["trials"])
    assert {trial["id"] for trial in report["trials"]} == {
        "brand-primary-color",
        "primary-benefit",
        "remove-unsupported-claim",
        "tmall-to-xiaohongshu",
        "replace-background",
    }
