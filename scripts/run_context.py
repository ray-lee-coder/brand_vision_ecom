"""
BrandKit Run Context — per-campaign build isolation and manifest management.

Each brandkit build produces an isolated directory with a manifest JSON
that declares inputs, targets, artifacts, and SHA-256 hashes for deterministic
verification. No timestamps in canonical hash inputs.
"""
import hashlib
import json
import re
import uuid
from dataclasses import dataclass
from pathlib import Path


RUN_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")


class ManifestError(RuntimeError):
    """Raised when a required run manifest cannot be consumed."""


def validate_run_id(run_id: str) -> str:
    """Return a safe run ID or raise before it can influence a path."""
    if not isinstance(run_id, str) or not RUN_ID_PATTERN.fullmatch(run_id):
        raise ValueError(
            "Invalid run ID: use 1-128 ASCII letters, digits, dots, underscores, or hyphens; "
            "the first character must be alphanumeric"
        )
    return run_id


@dataclass(frozen=True)
class RunContext:
    """Immutable context for a single campaign build."""
    run_id: str
    campaign_name: str
    root: Path                       # Project root
    mode: str = "offline"            # "offline" or "online"

    @property
    def build_dir(self) -> Path:
        return self.root / ".build" / "runs" / self.run_id / "build"

    @property
    def output_dir(self) -> Path:
        return self.root / "output" / "runs" / self.run_id

    @property
    def verify_dir(self) -> Path:
        return self.root / ".build" / "runs" / self.run_id / "verify"

    def manifest_path(self) -> Path:
        return self.root / ".build" / "runs" / self.run_id / "manifest.json"


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

    def write(self, path=None):
        """Write manifest to build directory."""
        path = Path(path) if path is not None else self.ctx.manifest_path()
        write_json(path, self.data)
        return path


def create_run_context(campaign_name: str, root: Path, mode: str = "offline", run_id=None) -> RunContext:
    """Create a RunContext with a unique or caller-supplied run ID."""
    run_id = f"{campaign_name}-{uuid.uuid4().hex[:12]}" if run_id is None else run_id
    validate_run_id(run_id)
    return RunContext(run_id=run_id, campaign_name=campaign_name, root=root, mode=mode)


def get_or_create_manifest(ctx: RunContext) -> dict:
    """Read existing manifest or create a new one."""
    mpath = ctx.manifest_path()
    if mpath.exists():
        return read_json(mpath)
    builder = ManifestBuilder(ctx)
    builder.write()
    return builder.data


def read_manifest(path: Path, required: bool = False) -> dict:
    """Read a manifest, failing closed when the caller supplied it explicitly."""
    path = Path(path)
    if not path.exists():
        if required:
            raise ManifestError(f"Required manifest not found: {path}")
        return {}
    try:
        manifest = read_json(path)
    except (json.JSONDecodeError, OSError) as exc:
        if required:
            raise ManifestError(f"Invalid manifest {path}: {exc}") from exc
        return {}
    if not isinstance(manifest, dict):
        if required:
            raise ManifestError(f"Invalid manifest {path}: root must be an object")
        return {}
    return manifest


def manifest_artifact_paths(manifest: dict, root: Path, category=None):
    """Resolve declared artifact paths, optionally filtered by category."""
    root = Path(root).resolve()
    paths = []
    for rel_path, metadata in manifest.get("artifacts", {}).items():
        if category is not None and metadata.get("category") != category:
            continue
        path = (root / rel_path).resolve()
        try:
            path.relative_to(root)
        except ValueError:
            continue
        paths.append(path)
    return sorted(paths)


def write_canonical_json(data, path):
    """Write JSON with sorted keys, no trailing spaces — for deterministic comparison."""
    write_json(path, data)
