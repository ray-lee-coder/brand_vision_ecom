"""
BrandKit Run Context — per-campaign build isolation and manifest management.

Each brandkit build produces an isolated directory with a manifest JSON
that declares inputs, targets, artifacts, and SHA-256 hashes for deterministic
verification. No timestamps in canonical hash inputs.
"""
import hashlib
import json
import shutil
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Optional


@dataclass(frozen=True)
class RunContext:
    """Immutable context for a single campaign build."""
    run_id: str
    campaign_name: str
    root: Path                       # Project root
    mode: str = "offline"            # "offline" or "online"

    @property
    def build_dir(self) -> Path:
        return self.root / ".build"

    @property
    def output_dir(self) -> Path:
        return self.root / "output"

    def manifest_path(self) -> Path:
        return self.build_dir / "manifest.json"


def file_sha256(path) -> str:
    """Compute SHA-256 hex digest of a file."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def read_json(path) -> dict:
    with open(path) as f:
        return json.load(f)


def write_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        json.dump(data, f, indent=2, ensure_ascii=False, sort_keys=True)


class ManifestBuilder:
    """Build a campaign manifest incrementally."""

    def __init__(self, ctx: RunContext):
        self.ctx = ctx
        self.data = {
            "run_id": ctx.run_id,
            "campaign": ctx.campaign_name,
            "mode": ctx.mode,
            "inputs": {},
            "targets": [],
            "artifacts": {},
            "reports": {},
        }

    def add_input(self, name: str, path: str):
        """Record an input file (spec, facts, campaign YAML)."""
        self.data["inputs"][name] = {"path": path}

    def add_target(self, target: dict):
        """Record an output target from the resolved task."""
        self.data["targets"].append(target)

    def add_artifact(self, path: Path, category: str = "visual"):
        """Record a generated artifact with its SHA-256 hash."""
        path = Path(path).resolve()
        if path.exists():
            try:
                rel = str(path.relative_to(self.ctx.root.resolve()))
            except ValueError:
                rel = str(path)
            self.data["artifacts"][rel] = {
                "sha256": file_sha256(path),
                "category": category,
            }

    def add_report(self, name: str, path: Path):
        """Record a verification/validation report."""
        if path.exists():
            rel = str(path.relative_to(self.ctx.root))
            self.data["reports"][name] = {"path": rel}

    def write(self):
        """Write manifest to build directory."""
        path = self.ctx.manifest_path()
        write_json(path, self.data)
        return path


def create_run_context(campaign_name: str, root: Path, mode: str = "offline") -> RunContext:
    """Create a RunContext with a deterministic run_id for repeatability."""
    import hashlib
    # Deterministic run_id: campaign_name + mode hash
    seed = f"{campaign_name}:{mode}".encode()
    run_id = hashlib.sha256(seed).hexdigest()[:16]
    return RunContext(run_id=run_id, campaign_name=campaign_name, root=root, mode=mode)


def get_or_create_manifest(ctx: RunContext) -> dict:
    """Read existing manifest or create a new one."""
    mpath = ctx.manifest_path()
    if mpath.exists():
        return read_json(mpath)
    builder = ManifestBuilder(ctx)
    builder.write()
    return builder.data


def write_canonical_json(data, path):
    """Write JSON with sorted keys, no trailing spaces — for deterministic comparison."""
    write_json(path, data)