#!/usr/bin/env python3
"""Run the five Beta modification trials in isolated offline workspaces."""

import argparse
import hashlib
import json
import shutil
import subprocess
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path

import yaml


REPO_ROOT = Path(__file__).resolve().parent.parent
CAMPAIGN = "acme-launch"


def copy_workspace(destination):
    shutil.copytree(
        REPO_ROOT,
        destination,
        ignore=shutil.ignore_patterns(".git", ".build", "output", ".pytest_cache", "__pycache__", "._*"),
    )


def update_yaml(path, mutator):
    data = yaml.safe_load(path.read_text())
    mutator(data)
    path.write_text(yaml.safe_dump(data, sort_keys=False, allow_unicode=True))


def build(workspace, run_id):
    result = subprocess.run(
        [
            "bash",
            "scripts/brandkit",
            "build",
            "campaigns/acme-launch.yaml",
            "--offline",
            "--skip-png",
            "--run-id",
            run_id,
        ],
        cwd=workspace,
        capture_output=True,
        text=True,
        timeout=60,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr + result.stdout)
    manifest = json.loads((workspace / ".build" / "runs" / run_id / "manifest.json").read_text())
    return manifest


def artifact_map(manifest, workspace):
    artifacts = {}
    marker = f"/{CAMPAIGN}/"
    for path, metadata in manifest.get("artifacts", {}).items():
        if metadata.get("category") == "compiled" or marker not in path:
            continue
        logical_path = path.split(marker, 1)[1]
        artifact_path = workspace / path
        digest = metadata["sha256"]
        if artifact_path.suffix in {".html", ".md", ".json"} and artifact_path.exists():
            normalized = artifact_path.read_text().replace(str(workspace.resolve()), "<WORKSPACE>")
            digest = hashlib.sha256(normalized.encode()).hexdigest()
        artifacts[logical_path] = {
            "sha256": digest,
            "category": metadata["category"],
        }
    return artifacts


def changed_categories(before, after):
    keys = set(before) | set(after)
    changed = [key for key in sorted(keys) if before.get(key) != after.get(key)]
    categories = {
        (after.get(key) or before.get(key))["category"].split("_", 1)[0]
        for key in changed
    }
    return changed, categories


def trial_specs():
    return [
        {
            "id": "brand-primary-color",
            "mutation": "Set Acme primary color to #D94B1F",
            "expected_categories": {"visual"},
            "online_model_budget": {"copy": 0, "image": 0},
            "mutate": lambda root: update_yaml(
                root / "brands/acme/brand-core.yaml",
                lambda data: data["colors"].update(primary="#D94B1F"),
            ),
        },
        {
            "id": "primary-benefit",
            "mutation": "Change the primary benefit to 阳光柑橘气泡",
            "expected_categories": {"visual", "content"},
            "online_model_budget": {"copy": 2, "image": 0},
            "mutate": lambda root: update_yaml(
                root / "brands/acme/content-spec.yaml",
                lambda data: data["content"]["message_hierarchy"].update(primary_benefit="阳光柑橘气泡"),
            ),
        },
        {
            "id": "remove-unsupported-claim",
            "mutation": "Remove natural_ingredients fact and 自然原料 message",
            "expected_categories": {"content"},
            "online_model_budget": {"copy": 2, "image": 0},
            "mutate": remove_claim,
        },
        {
            "id": "tmall-to-xiaohongshu",
            "mutation": "Replace the Tmall product title target with Xiaohongshu title",
            "expected_categories": {"content"},
            "online_model_budget": {"copy": 2, "image": 0},
            "mutate": switch_channel,
        },
        {
            "id": "replace-background",
            "mutation": "Replace the lifestyle background prompt",
            "expected_categories": {"visual"},
            "online_model_budget": {"copy": 0, "image": 1},
            "mutate": lambda root: update_yaml(
                root / "brands/acme/visual-spec.yaml",
                lambda data: data["scene_policy"]["lifestyle"].update(
                    background_prompt="Citrus grove picnic at golden hour with open compositing space"
                ),
            ),
        },
    ]


def remove_claim(root):
    update_yaml(
        root / "brands/acme/products/drink1.yaml",
        lambda data: data["product"]["facts"].pop("natural_ingredients"),
    )
    update_yaml(
        root / "brands/acme/content-spec.yaml",
        lambda data: data["content"]["message_hierarchy"].update(
            secondary_benefits=[
                item
                for item in data["content"]["message_hierarchy"]["secondary_benefits"]
                if item != "自然原料"
            ]
        ),
    )


def switch_channel(root):
    update_yaml(
        root / "campaigns/acme-launch.yaml",
        lambda data: data["outputs"]["content"].__setitem__(
            0, {"type": "title", "channel": "xiaohongshu"}
        ),
    )


def run_trials(output_path):
    with tempfile.TemporaryDirectory(prefix="brandkit-beta-") as temp_dir:
        temp_root = Path(temp_dir)
        baseline_root = temp_root / "baseline"
        copy_workspace(baseline_root)
        baseline = artifact_map(build(baseline_root, "baseline"), baseline_root)

        trials = []
        for spec in trial_specs():
            started_at = time.monotonic()
            workspace = temp_root / spec["id"]
            copy_workspace(workspace)
            spec["mutate"](workspace)
            after = artifact_map(build(workspace, spec["id"]), workspace)
            changed, categories = changed_categories(baseline, after)
            passed = bool(changed) and categories == spec["expected_categories"]
            trials.append({
                "id": spec["id"],
                "mutation": spec["mutation"],
                "status": "pass" if passed else "fail",
                "expected_changed_categories": sorted(spec["expected_categories"]),
                "actual_changed_categories": sorted(categories),
                "changed_artifacts": changed,
                "unchanged_artifacts": sorted(set(baseline) & set(after) - set(changed)),
                "before_hashes": {key: value["sha256"] for key, value in baseline.items()},
                "after_hashes": {key: value["sha256"] for key, value in after.items()},
                "actual_model_calls": 0,
                "elapsed_seconds": round(time.monotonic() - started_at, 3),
                "online_model_budget": spec["online_model_budget"],
            })

    passed_count = sum(trial["status"] == "pass" for trial in trials)
    report = {
        "campaign": CAMPAIGN,
        "generated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "mode": "offline",
        "summary": {
            "total": len(trials),
            "passed": passed_count,
            "failed": len(trials) - passed_count,
        },
        "synthetic_evidence_only": True,
        "trials": trials,
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, indent=2, ensure_ascii=False, sort_keys=True))
    return all(trial["status"] == "pass" for trial in trials)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    raise SystemExit(0 if run_trials(args.output) else 1)


if __name__ == "__main__":
    main()
