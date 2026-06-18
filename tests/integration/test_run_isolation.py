import json
import subprocess
import sys
import uuid
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]


def test_compile_writes_only_to_explicit_run_directories(tmp_path):
    runs = []
    for run_id, campaign in (
        ("run-a", "campaigns/618-launch.yaml"),
        ("run-b", "campaigns/acme-launch.yaml"),
    ):
        run_root = tmp_path / run_id
        build_dir = run_root / "build"
        manifest = run_root / "manifest.json"
        result = subprocess.run(
            [
                sys.executable,
                "scripts/compile.py",
                campaign,
                "--build-dir",
                str(build_dir),
                "--manifest",
                str(manifest),
                "--run-id",
                run_id,
                "--mode",
                "offline",
            ],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, result.stderr + result.stdout
        runs.append((build_dir, manifest))

    first_resolved = json.loads((runs[0][0] / "resolved-task.json").read_text())
    second_resolved = json.loads((runs[1][0] / "resolved-task.json").read_text())
    assert first_resolved["campaign"]["name"] == "618-launch"
    assert second_resolved["campaign"]["name"] == "acme-launch"
    assert json.loads(runs[0][1].read_text())["run_id"] == "run-a"
    assert json.loads(runs[1][1].read_text())["run_id"] == "run-b"


def test_concurrent_cli_builds_are_fully_run_scoped():
    run_a = f"test-a-{uuid.uuid4().hex[:8]}"
    run_b = f"test-b-{uuid.uuid4().hex[:8]}"
    commands = [
        ["bash", "scripts/brandkit", "build", "campaigns/618-launch.yaml", "--offline", "--skip-png", "--run-id", run_a],
        ["bash", "scripts/brandkit", "build", "campaigns/acme-launch.yaml", "--offline", "--skip-png", "--run-id", run_b],
    ]
    processes = [
        subprocess.Popen(command, cwd=REPO_ROOT, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        for command in commands
    ]
    results = [process.communicate(timeout=60) + (process.returncode,) for process in processes]
    for stdout, stderr, returncode in results:
        assert returncode == 0, stderr + stdout

    for run_id, expected_campaign in ((run_a, "618-launch"), (run_b, "acme-launch")):
        run_root = REPO_ROOT / ".build" / "runs" / run_id
        manifest = json.loads((run_root / "manifest.json").read_text())
        resolved = json.loads((run_root / "build" / "resolved-task.json").read_text())
        assert manifest["campaign"] == expected_campaign
        assert resolved["campaign"]["name"] == expected_campaign
        assert (run_root / "verify" / "visual-report.json").exists()
        assert (run_root / "verify" / "content-report.json").exists()
        assert (run_root / "verify" / "channel-diff-report.json").exists()
        for artifact_path, metadata in manifest["artifacts"].items():
            if metadata["category"] != "compiled":
                assert f"output/runs/{run_id}/" in artifact_path
            assert len(metadata["sha256"]) == 64
        for report in manifest["reports"].values():
            assert f".build/runs/{run_id}/verify/" in report["path"]


def test_verify_fails_when_manifest_declared_provenance_is_missing():
    run_id = f"missing-prov-{uuid.uuid4().hex[:8]}"
    build = subprocess.run(
        ["bash", "scripts/brandkit", "build", "campaigns/acme-launch.yaml", "--offline", "--skip-png", "--run-id", run_id],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )
    assert build.returncode == 0, build.stderr + build.stdout

    run_root = REPO_ROOT / ".build" / "runs" / run_id
    manifest_path = run_root / "manifest.json"
    manifest = json.loads(manifest_path.read_text())
    provenance = next(
        REPO_ROOT / path
        for path, metadata in manifest["artifacts"].items()
        if metadata["category"] == "content_provenance"
    )
    provenance.unlink()

    verify = subprocess.run(
        [
            sys.executable,
            "scripts/verify.py",
            "--resolved",
            str(run_root / "build" / "resolved-task.json"),
            "--message-plan",
            str(run_root / "build" / "message-plan.json"),
            "--output-dir",
            str(REPO_ROOT / "output" / "runs" / run_id),
            "--verify-dir",
            str(run_root / "verify"),
            "--manifest",
            str(manifest_path),
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )
    assert verify.returncode != 0
    assert "Manifest artifact missing" in verify.stdout
