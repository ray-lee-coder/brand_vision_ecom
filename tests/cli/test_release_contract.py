import subprocess
import sys
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "scripts"))


def run_brandkit(*args):
    return subprocess.run(
        ["bash", "scripts/brandkit", *args],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )


@pytest.mark.parametrize("command", ["render", "verify", "validate"])
def test_unsupported_direct_commands_fail_with_actionable_message(command):
    result = run_brandkit(command)

    assert result.returncode != 0
    assert "not supported" in (result.stdout + result.stderr).lower()
    assert "unbound variable" not in (result.stdout + result.stderr).lower()


def test_help_does_not_advertise_unsupported_direct_commands():
    result = run_brandkit("help")

    assert result.returncode == 0
    assert "brandkit render <visual|content" not in result.stdout
    assert "brandkit verify" not in result.stdout
    assert "brandkit validate" not in result.stdout


@pytest.mark.parametrize("run_id", ["../escape", "nested/run", "", "x" * 129])
def test_cli_rejects_unsafe_explicit_run_id(run_id):
    result = run_brandkit(
        "build",
        "campaigns/acme-launch.yaml",
        "--offline",
        "--skip-png",
        "--run-id",
        run_id,
    )

    assert result.returncode != 0
    assert "invalid run id" in (result.stdout + result.stderr).lower()


@pytest.mark.parametrize("run_id", ["../escape", "nested/run", "", "x" * 129])
def test_run_context_rejects_unsafe_run_id(tmp_path, run_id):
    from run_context import create_run_context

    with pytest.raises(ValueError, match="Invalid run ID"):
        create_run_context("campaign", tmp_path, run_id=run_id)


def test_compile_fails_when_explicit_manifest_cannot_be_written(tmp_path):
    manifest_directory = tmp_path / "manifest.json"
    manifest_directory.mkdir()

    result = subprocess.run(
        [
            sys.executable,
            "scripts/compile.py",
            "campaigns/acme-launch.yaml",
            "--build-dir",
            str(tmp_path / "build"),
            "--manifest",
            str(manifest_directory),
            "--run-id",
            "manifest-write-test",
            "--mode",
            "offline",
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )

    assert result.returncode != 0
    assert "manifest" in (result.stdout + result.stderr).lower()


@pytest.mark.parametrize("contents", [None, "{not-json"])
def test_verify_fails_for_missing_or_invalid_explicit_manifest(tmp_path, contents):
    manifest_path = tmp_path / "manifest.json"
    if contents is not None:
        manifest_path.write_text(contents)

    result = subprocess.run(
        [sys.executable, "scripts/verify.py", "--manifest", str(manifest_path)],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )

    assert result.returncode != 0
    assert "manifest" in (result.stdout + result.stderr).lower()
