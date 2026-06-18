"""
BrandKit Contract System — schema validation, override policy, evidence checks.

Beta stage 2: validates all six input types against versioned schemas,
enforces the explicit override allowlist, and checks evidence file existence.
"""
import json
import os
import sys
from pathlib import Path

import jsonschema
import yaml

# ── Schema directory ──
SCHEMA_DIR = Path(__file__).parent.parent / "schemas"

# ── Schema-type mapping ──
SCHEMA_FILES = {
    "brand-core": "brand-core.schema.json",
    "visual-spec": "visual-spec.schema.json",
    "content-spec": "content-spec.schema.json",
    "product": "product.schema.json",
    "channel": "channel.schema.json",
    "campaign": "campaign.schema.json",
}


# ── Only allowed override paths ──
OVERRIDE_PATHS = frozenset({
    "headline_max_chars",
    "headline_max_lines",
    "safe_margin_px",
    "product_title_max_chars",
    "bullet_count",
    "bullet_max_chars_each",
})

# Map each override to the target types it applies to
OVERRIDE_TARGET_MAP = {
    "headline_max_chars": {"visual", "product_title", "title"},
    "headline_max_lines": {"visual"},
    "safe_margin_px": {"visual"},
    "product_title_max_chars": {"product_title"},
    "bullet_count": {"bullet_points"},
    "bullet_max_chars_each": {"bullet_points"},
}


class ContractError(RuntimeError):
    """Structured contract violation with error code."""
    def __init__(self, code, detail):
        self.code = code
        self.detail = detail
        super().__init__(f"[{code}] {detail}")


def load_schema(name):
    """Load and cache a JSON schema by document type."""
    path = SCHEMA_DIR / SCHEMA_FILES[name]
    if not path.exists():
        raise ContractError("schema_not_found", f"Schema file not found: {path}")
    with open(path) as f:
        return json.load(f)


def validate_document(schema_name, document, name_hint=""):
    """Validate a document against its versioned schema. Returns errors list."""
    try:
        schema = load_schema(schema_name)
        validator = jsonschema.Draft7Validator(schema)
        errors = list(validator.iter_errors(document))
        return [
            {
                "path": ".".join(str(p) for p in e.absolute_path),
                "message": e.message,
                "code": "schema_violation",
            }
            for e in errors
        ]
    except Exception as e:
        return [{"path": name_hint, "message": str(e), "code": "schema_validation_error"}]


def validate_document_or_raise(schema_name, document, name_hint=""):
    """Validate a document against its versioned schema. Raises on first error."""
    errors = validate_document(schema_name, document, name_hint)
    if errors:
        raise ContractError(
            f"schema_{schema_name}_violation",
            f"Validation of '{name_hint}' failed: {errors[0]['message']}",
        )


def apply_overrides(resolved, overrides):
    """Apply campaign overrides to resolved task, rejecting unknown paths."""
    if not overrides:
        return resolved

    unknown = set(overrides.keys()) - OVERRIDE_PATHS
    if unknown:
        raise ContractError(
            "unknown_override",
            f"Unknown override path(s): {sorted(unknown)}",
        )

    result = dict(resolved)
    result["overrides"] = dict(overrides)

    # Apply known overrides to output targets — field-to-target mapping
    output_targets = result.get("output_targets", [])
    for target in output_targets:
        target_type = (
            target.get("content_type")
            if target.get("type") == "content"
            else target.get("type") or target.get("scene") or ""
        )
        for key, value in overrides.items():
            allowed_targets = OVERRIDE_TARGET_MAP.get(key, set())
            if not allowed_targets or target_type in allowed_targets:
                if "constraints" not in target:
                    target["constraints"] = {}
                target["constraints"][key] = value

    return result


def require_file(project_root, ref_path, code="missing_evidence"):
    """Check a file exists relative to project root. Raise if missing."""
    full_path = Path(project_root) / ref_path
    if not full_path.exists():
        raise ContractError(code, f"Required file not found: {ref_path} (resolved: {full_path})")
    if full_path.suffix in {".yaml", ".yml"}:
        try:
            metadata = yaml.safe_load(full_path.read_text()) or {}
        except (OSError, yaml.YAMLError) as exc:
            raise ContractError("invalid_evidence_fixture", f"Cannot parse {ref_path}: {exc}")
        if metadata.get("evidence_type") == "synthetic_fixture":
            required = ("issuer", "issued_at", "method", "fact_ids")
            missing = [key for key in required if not metadata.get(key)]
            if missing:
                raise ContractError(
                    "invalid_evidence_fixture",
                    f"Synthetic evidence {ref_path} is missing metadata: {missing}",
                )
    return str(full_path)


def check_output_targets_nonempty(output_targets, campaign_name):
    """Reject empty output target lists."""
    if not output_targets:
        raise ContractError(
            "empty_output_targets",
            f"Campaign '{campaign_name}' has no output targets — nothing to generate.",
        )


def compile_campaign_with_contracts(campaign_path_str, project_root=None):
    """
    Full contract-enforcing compile flow.

    Input: campaign file path
    Returns: (resolved_task dict, message_plan dict) or raises ContractError
    """
    if project_root is None:
        project_root = Path(campaign_path_str).resolve().parent.parent

    campaign_path = Path(campaign_path_str)
    with open(campaign_path) as f:
        campaign = yaml.safe_load(f)

    # Validate campaign YAML
    validate_document_or_raise("campaign", campaign, str(campaign_path))

    campaign_data = campaign["campaign"]
    campaign_name = campaign_data["name"]

    # Resolve brand ref
    brand_ref = campaign_data["brand_ref"]
    brand_file = require_file(project_root, brand_ref, "missing_brand_ref")
    with open(brand_file) as f:
        brand_core = yaml.safe_load(f)
    validate_document_or_raise("brand-core", brand_core, brand_ref)

    brand_dir = Path(brand_file).parent

    # Load visual-spec + content-spec
    visual_spec_path = brand_dir / "visual-spec.yaml"
    if visual_spec_path.exists():
        with open(visual_spec_path) as f:
            visual_spec = yaml.safe_load(f)
        validate_document_or_raise("visual-spec", visual_spec, str(visual_spec_path))
    else:
        visual_spec = {}

    content_spec_path = brand_dir / "content-spec.yaml"
    if content_spec_path.exists():
        with open(content_spec_path) as f:
            content_spec = yaml.safe_load(f)
        validate_document_or_raise("content-spec", content_spec, str(content_spec_path))
    else:
        content_spec = {}

    # Load product facts
    product_ref = campaign_data["product_ref"]
    product_file = require_file(project_root, product_ref, "missing_product_ref")
    with open(product_file) as f:
        product_facts = yaml.safe_load(f)
    validate_document_or_raise("product", product_facts, product_ref)

    # Verify evidence files exist for each product fact
    product_data = product_facts.get("product", {})
    for fact_key, fact_data in product_data.get("facts", {}).items():
        source = fact_data.get("source", {})
        ev_ref = source.get("ref", "")
        if ev_ref:
            require_file(project_root, ev_ref, f"missing_evidence:{fact_key}")

    # Load channels referenced in outputs
    outputs = campaign.get("outputs", {})
    channels = {}
    for output in outputs.get("visual", []) + outputs.get("content", []):
        ch = output.get("channel")
        if ch and ch not in channels:
            ch_path = Path(project_root) / "channels" / f"{ch}.yaml"
            if ch_path.exists():
                with open(ch_path) as f:
                    ch_data = yaml.safe_load(f)
                validate_document_or_raise("channel", ch_data, str(ch_path))
                channels[ch] = ch_data

    # ── Build output targets list ──
    output_targets = []
    for vis in outputs.get("visual", []):
        output_targets.append({
            "type": "visual",
            "scene": vis["type"],
            "channel": vis["channel"],
            "format": vis.get("format", "png"),
            "ratio": vis.get("ratio", "1:1"),
            "constraints": {},
        })
    for cont in outputs.get("content", []):
        output_targets.append({
            "type": "content",
            "content_type": cont["type"],
            "channel": cont["channel"],
            "constraints": {},
        })

    check_output_targets_nonempty(output_targets, campaign_name)

    # ── Apply overrides ──
    overrides = campaign.get("override", {})
    output_targets = apply_overrides(output_targets, overrides)

    # ── Build resolved task ──
    brand_section = brand_core.get("brand", {})
    resolved = {
        "campaign": {
            "name": campaign_name,
            "objective": campaign_data.get("objective", ""),
            "audience": campaign_data.get("audience", ""),
        },
        "brand": dict(brand_section) if brand_section else {},
        "visual_spec": {
            "visual": visual_spec.get("visual", {}),
            "layout": visual_spec.get("layout", {}),
            "product_image": visual_spec.get("product_image", {}),
            "scene_policy": visual_spec.get("scene_policy", {}),
        },
        "content_spec": content_spec.get("content", {}),
        "product": product_data,
        "channels": channels,
        "output_targets": output_targets,
    }

    # Merge top-level brand keys
    for top_key in ["colors", "typography", "logo", "voice", "claims", "identity", "references"]:
        if top_key in brand_core:
            resolved["brand"][top_key] = brand_core[top_key]

    # ── Build message plan ──
    primary_benefit_id = content_spec.get("content", {}).get("message_hierarchy", {}).get("primary_benefit", "")
    secondary_benefits = content_spec.get("content", {}).get("message_hierarchy", {}).get("secondary_benefits", [])
    brand_name = brand_core.get("brand", {}).get("name", "Brand")

    proof_points = []
    for fact_key, fact_data in product_data.get("facts", {}).items():
        proof_points.append({
            "claim_ref": f"facts.{fact_key}",
            "value": fact_data.get("value"),
            "unit": fact_data.get("unit", ""),
            "source_ref": fact_data.get("source", {}).get("ref", ""),
        })

    message_plan = {
        "campaign_theme": f"{brand_name.lower()}_{campaign_name}",
        "primary_benefit": {
            "id": primary_benefit_id,
            "statement": primary_benefit_id if primary_benefit_id else "premium quality",
        },
        "secondary_benefits": secondary_benefits,
        "proof_points": proof_points,
        "call_to_action": {},
        "visual": {
            "headline": primary_benefit_id or campaign_name,
            "subtitle": brand_name,
        },
    }

    # CTA per channel
    for ch_name in channels:
        if ch_name == "tmall":
            message_plan["call_to_action"][ch_name] = "立即了解"
        elif ch_name == "xiaohongshu":
            message_plan["call_to_action"][ch_name] = "查看实测"

    return resolved, message_plan
