#!/usr/bin/env python3
"""
BrandKit Compiler — Spec 合并 + 冲突检测 + 编译输出
M0-A: Compiler Spine

读取: brand-core / visual-spec / content-spec / product-facts / channels / campaign
输出: .build/resolved-task.json + .build/message-plan.json

Beta Stage 2: adds contract validation via contracts.py
"""
import json
import os
import sys
from pathlib import Path
import yaml


# ── Run Context ──
try:
    from run_context import RunContext, ManifestBuilder, create_run_context
    HAS_RUN_CONTEXT = True
except ImportError:
    HAS_RUN_CONTEXT = False


# ── Schema validation via contracts system ──
try:
    from contracts import (
        validate_document,
        apply_overrides,
        require_file,
        check_output_targets_nonempty,
        ContractError,
        SCHEMA_DIR,
    )
    HAS_CONTRACTS = SCHEMA_DIR.exists()
except ImportError:
    HAS_CONTRACTS = False


# ── 约束类型 ──────────────────────────────────────────────
HARD = "hard"
SOFT = "soft"

CONSTRAINT_TAG = {
    # brand-core hard
    "colors.primary": HARD,
    "colors.forbidden": HARD,
    "logo.forbidden": HARD,
    "claims.require_evidence": HARD,
    "voice.avoid": HARD,
    # product facts hard
    "facts.*.source": HARD,
    # channel hard
    "content.forbidden_patterns": HARD,
    "visual.ratios": HARD,
    # everything else is soft
}

# ── 编译优先级 ─────────────────────────────────────────────
PRIORITY = [
    "global_safety",
    "brand_hard",
    "product_facts",
    "channel_hard",
    "campaign",
    "brand_soft",
    "channel_soft",
    "renderer_defaults",
]


def load_yaml(path):
    with open(path, "r") as f:
        return yaml.safe_load(f)


def deep_merge(base, override, path=""):
    """Merge override into base. Lists are replaced, dicts are recursed."""
    if not isinstance(base, dict) or not isinstance(override, dict):
        return override
    result = dict(base)
    for k, v in override.items():
        if k in result and isinstance(result[k], dict) and isinstance(v, dict):
            result[k] = deep_merge(result[k], v, f"{path}.{k}")
        else:
            result[k] = v
    return result


def get_constraint_type(key_path):
    """Determine if a key path is hard or soft constraint."""
    for pattern, ctype in CONSTRAINT_TAG.items():
        if pattern.endswith("*"):
            prefix = pattern.rstrip(".*")
            if key_path.startswith(prefix):
                return ctype
        elif key_path == pattern:
            return ctype
    return SOFT


def detect_conflicts(resolved, sources):
    """
    Detect hard constraint conflicts across spec layers.
    Checks:
    - forbidden colors in overrides
    - unknown channel references
    - product facts without source
    - campaign claims without supporting facts
    - channel hard rules vs campaign override conflicts
    """
    conflicts = []
    brand = resolved.get("brand", {})
    product = resolved.get("product", {})
    campaign_data = sources.get("campaign", {})
    campaign_override = campaign_data.get("override", {})
    outputs = sources.get("campaign", {}).get("outputs", {})
    channels = resolved.get("channels", {})

    # 1. Forbidden colors in overrides
    brand_forbidden = set(brand.get("colors", {}).get("forbidden", []))
    for key, val in campaign_override.items():
        if isinstance(val, str):
            for forbidden in brand_forbidden:
                if forbidden.lower() in val.lower():
                    conflicts.append({
                        "type": "hard_constraint_violation",
                        "field": f"override.{key}",
                        "value": val,
                        "conflict_with": f"brand.colors.forbidden: {forbidden}",
                        "severity": "error",
                    })

    # 2. Unknown channel references
    for output_list in [outputs.get("visual", []), outputs.get("content", [])]:
        for out in output_list:
            ch = out.get("channel", "")
            if ch and ch not in channels:
                conflicts.append({
                    "type": "unknown_channel",
                    "field": f"outputs.{out.get('type', 'unknown')}.channel",
                    "value": ch,
                    "detail": f"Channel '{ch}' not found in channels/ directory",
                    "severity": "error",
                })

    # 3. Product facts without source
    facts = product.get("facts", {})
    for fact_key, fact_data in facts.items():
        source = fact_data.get("source", {})
        if not source.get("ref"):
            conflicts.append({
                "type": "missing_source",
                "field": f"product.facts.{fact_key}.source.ref",
                "value": fact_key,
                "detail": f"Fact '{fact_key}' has no source reference",
                "severity": "warning",
            })

    # 4. require_evidence claims without matching facts
    require_evidence = brand.get("claims", {}).get("require_evidence", [])
    # Check if campaign content text (title, description) uses require_evidence terms
    campaign_text = str(campaign_data.get("campaign", {}))
    for evidence_term in require_evidence:
        if evidence_term.lower() in campaign_text.lower():
            # Check if any product fact supports this
            has_evidence = any(
                fact_data.get("source", {}).get("ref")
                for fact_data in facts.values()
            )
            if not has_evidence:
                conflicts.append({
                    "type": "unsupported_claim",
                    "field": f"campaign.{evidence_term}",
                    "value": evidence_term,
                    "detail": f"'{evidence_term}' requires evidence but product facts have no sources",
                    "severity": "error",
                })

    # 5. unknown template
    import os
    for out in outputs.get("visual", []):
        scene = out.get("type", "")
        template_path = f"templates/{scene}.html"
        if not os.path.exists(template_path):
            conflicts.append({
                "type": "unknown_template",
                "field": f"outputs.visual.type",
                "value": scene,
                "detail": f"Template not found: {template_path}",
                "severity": "error",
            })

    return conflicts


def compile_specs(brand_dir, campaign_path, channels_dir, build_dir):
    """Main compile function."""
    # Load campaign
    campaign = load_yaml(campaign_path)
    campaign_name = campaign["campaign"]["name"]

    # ── Contract validation (schema, refs, evidence) ──
    if HAS_CONTRACTS:
        # Campaign schema validation — check error list, not just exceptions
        campaign_errors = validate_document("campaign", campaign, str(campaign_path))
        if campaign_errors:
            for err in campaign_errors:
                print(f"[CONTRACT] Campaign schema: {err['path']}: {err['message']}")
            return {"status": "failed", "conflicts": [{"type": "schema_violation", "detail": campaign_errors[0]['message']}]}

    # Resolve brand ref
    brand_ref = campaign["campaign"]["brand_ref"]
    brand_dir_resolved = Path(brand_ref).parent
    brand_core = load_yaml(brand_ref)
    if HAS_CONTRACTS:
        brand_errors = validate_document("brand-core", brand_core, brand_ref)
        if brand_errors:
            for err in brand_errors:
                print(f"[CONTRACT] Brand-core schema: {err['path']}: {err['message']}")
            return {"status": "failed", "conflicts": [{"type": "schema_violation", "detail": brand_errors[0]['message']}]}

    # Load visual-spec + content-spec
    visual_spec = load_yaml(str(brand_dir_resolved / "visual-spec.yaml"))
    content_spec = load_yaml(str(brand_dir_resolved / "content-spec.yaml"))
    if HAS_CONTRACTS:
        vs_errors = validate_document("visual-spec", visual_spec, str(brand_dir_resolved / "visual-spec.yaml"))
        if vs_errors:
            for err in vs_errors:
                print(f"[CONTRACT] Visual-spec schema: {err['path']}: {err['message']}")
            return {"status": "failed", "conflicts": [{"type": "schema_violation", "detail": vs_errors[0]['message']}]}
        cs_errors = validate_document("content-spec", content_spec, str(brand_dir_resolved / "content-spec.yaml"))
        if cs_errors:
            for err in cs_errors:
                print(f"[CONTRACT] Content-spec schema: {err['path']}: {err['message']}")
            return {"status": "failed", "conflicts": [{"type": "schema_violation", "detail": cs_errors[0]['message']}]}

    # Load product facts
    product_ref = campaign["campaign"]["product_ref"]
    product_facts = load_yaml(product_ref)

    # ── Product schema validation ──
    if HAS_CONTRACTS:
        prod_errors = validate_document("product", product_facts, product_ref)
        if prod_errors:
            for err in prod_errors:
                print(f"[CONTRACT] Product schema: {err['path']}: {err['message']}")
            return {"status": "failed", "conflicts": [{"type": "schema_violation", "detail": prod_errors[0]['message']}]}
    # ── Evidence file existence check ──
    if HAS_CONTRACTS:
        product_data = product_facts.get("product", {})
        for fact_key, fact_data in product_data.get("facts", {}).items():
            source = fact_data.get("source", {})
            ev_ref = source.get("ref", "")
            if ev_ref:
                try:
                    require_file(Path.cwd(), ev_ref, f"missing_evidence:{fact_key}")
                except ContractError as e:
                    print(f"[CONTRACT] {e}")
                    return {"status": "failed", "conflicts": [{"type": "missing_evidence", "field": f"facts.{fact_key}", "detail": str(e)}]}

    # Load channels
    channels = {}
    outputs = campaign.get("outputs", {})
    for output in outputs.get("visual", []) + outputs.get("content", []):
        ch = output.get("channel")
        if ch and ch not in channels:
            ch_path = Path(channels_dir) / f"{ch}.yaml"
            if ch_path.exists():
                ch_data = load_yaml(str(ch_path))
                if HAS_CONTRACTS:
                    ch_errors = validate_document("channel", ch_data, str(ch_path))
                    if ch_errors:
                        for err in ch_errors:
                            print(f"[CONTRACT] Channel '{ch}' schema: {err['path']}: {err['message']}")
                        return {"status": "failed", "conflicts": [{"type": "schema_violation", "detail": ch_errors[0]['message']}]}
                channels[ch] = ch_data

    # ── Merge resolved task ──
    resolved = {}

    # Layer 1: brand core (brand_hard)
    resolved["brand"] = {}
    # brand-core.yaml has 'brand:' as a subsection, plus top-level keys (colors, identity, etc.)
    brand_section = brand_core.get("brand", {})
    if brand_section:
        resolved["brand"].update(brand_section)
    # Merge top-level keys (colors, typography, voice, claims, etc.)
    for top_key in ["colors", "typography", "logo", "voice", "claims", "identity", "references"]:
        if top_key in brand_core:
            resolved["brand"][top_key] = brand_core[top_key]

    # Layer 2: product facts
    resolved["product"] = product_facts.get("product", {})

    # Layer 3: visual-spec + content-spec (brand_soft)
    resolved["visual_spec"] = {
        "visual": visual_spec.get("visual", {}),
        "layout": visual_spec.get("layout", {}),
        "product_image": visual_spec.get("product_image", {}),
        "scene_policy": visual_spec.get("scene_policy", {}),
    }
    resolved["content_spec"] = content_spec.get("content", {})

    # Layer 4: channels (channel_hard + channel_soft)
    resolved["channels"] = {}
    for ch_name, ch_data in channels.items():
        resolved["channels"][ch_name] = ch_data

    # Layer 5: campaign overrides (campaign)
    resolved["campaign"] = campaign.get("campaign", {})
    override = campaign.get("override", {})
    if override:
        resolved["override"] = override

    # ── Conflict detection ──
    sources = {
        "campaign": campaign,
        "brand": brand_core,
    }
    conflicts = detect_conflicts(resolved, sources)

    if conflicts:
        for c in conflicts:
            if c["severity"] == "error":
                detail = c.get("conflict_with", c.get("detail", ""))
                print(f"[CONFLICT] {c['field']}: '{c['value']}' conflicts with {detail}")
        return {"status": "failed", "conflicts": conflicts}

    # ── Build message plan (single source of truth for visual + content) ──
    primary_benefit_id = content_spec.get("content", {}).get("message_hierarchy", {}).get("primary_benefit", "")
    secondary_benefits = content_spec.get("content", {}).get("message_hierarchy", {}).get("secondary_benefits", [])
    brand_name = brand_core.get("brand", {}).get("name", "Brand")
    campaign_obj = campaign.get("campaign", {})
    campaign_theme = f"{brand_name.lower()}_{campaign_name}"
    primary_benefit_statement = primary_benefit_id if primary_benefit_id else "premium quality"

    # Map benefit IDs to product facts
    proof_points = []
    for fact_key, fact_data in product_facts.get("product", {}).get("facts", {}).items():
        proof_points.append({
            "claim_ref": f"facts.{fact_key}",
            "value": f"{fact_data['value']}{fact_data.get('unit', '')}",
            "source_ref": fact_data.get("source", {}).get("ref", "unknown"),
            "status": fact_data.get("status", "unknown"),
        })

    message_plan = {
        "campaign_name": campaign_name,
        "campaign_theme": campaign_theme,
        "brand_name": brand_name,
        "primary_benefit": {
            "id": primary_benefit_id or "primary_benefit",
            "statement": primary_benefit_statement,
        },
        "secondary_benefits": [{"id": b, "statement": b} for b in secondary_benefits],
        "proof_points": proof_points,
        "call_to_action": {
            "tmall": "立即了解",
            "xiaohongshu": "查看通勤实测",
        },
        "visual": {
            "headline": primary_benefit_statement,
            "subtitle": f"{brand_name} — {primary_benefit_statement}",
            "cta": "立即了解",
        },
    }

    # ── Build output targets ──
    output_targets = []
    for v in outputs.get("visual", []):
        ch = v.get("channel", "")
        ch_data = channels.get(ch, {})
        ch_visual = ch_data.get("visual", {})
        ratios = ch_visual.get("ratios", ["1:1"])
        output_targets.append({
            "type": "visual",
            "scene": v["type"],
            "channel": ch,
            "format": v.get("format", "png"),
            "ratio": ratios[0] if ratios else "1:1",
            "constraints": {
                "product_coverage": ch_visual.get("product_coverage", "45%-60%"),
                "safe_margin_px": ch_visual.get("safe_margin_px", 48),
                "text_density": ch_visual.get("text_density", "low"),
            },
        })
    for c in outputs.get("content", []):
        ch = c.get("channel", "")
        ch_data = channels.get(ch, {})
        ch_content = ch_data.get("content", {})
        output_targets.append({
            "type": "content",
            "content_type": c["type"],
            "channel": ch,
            "format": "md",
            "constraints": ch_content,
        })

    resolved["output_targets"] = output_targets

    # ── Empty output targets check ──
    if HAS_CONTRACTS:
        try:
            check_output_targets_nonempty(output_targets, campaign_name)
        except ContractError as e:
            print(f"[CONTRACT] {e}")
            return {"status": "failed", "conflicts": [{"type": "empty_output_targets", "detail": str(e)}]}

    # ── Apply overrides via contracts system ──
    if HAS_CONTRACTS and override:
        try:
            resolved = apply_overrides(resolved, override)
        except ContractError as e:
            print(f"[CONTRACT] {e}")
            return {"status": "failed", "conflicts": [{"type": "unknown_override", "detail": str(e)}]}

    # ── Write outputs ──
    build_dir.mkdir(parents=True, exist_ok=True)

    resolved_path = build_dir / "resolved-task.json"
    with open(resolved_path, "w") as f:
        json.dump(resolved, f, indent=2, ensure_ascii=False)
    print(f"[OK] resolved-task.json → {resolved_path}")

    msg_path = build_dir / "message-plan.json"
    with open(msg_path, "w") as f:
        json.dump(message_plan, f, indent=2, ensure_ascii=False)
    print(f"[OK] message-plan.json → {msg_path}")

    # ── Build manifest ──
    if HAS_RUN_CONTEXT:
        try:
            ctx = create_run_context(campaign_name, Path.cwd())
            builder = ManifestBuilder(ctx)
            builder.add_input("campaign", str(campaign_path))
            builder.add_input("brand_core", brand_ref)
            builder.add_input("product_facts", product_ref)
            for target in output_targets:
                builder.add_target(target)
            builder.add_artifact(resolved_path, "compiled")
            builder.add_artifact(msg_path, "compiled")
            builder.write()
        except Exception as e:
            print(f"[WARN] Manifest not written: {e}")

    return {"status": "ok", "resolved": resolved, "message_plan": message_plan}


def compile_campaign(campaign_path_str):
    """
    Convenience wrapper: compile a campaign from its file path.
    Infers brand_dir, channels_dir, and build_dir from the file location.
    Changes working directory to the project root for path resolution.
    """
    campaign_file = Path(campaign_path_str).resolve()
    project_root = campaign_file.parent.parent
    orig_cwd = os.getcwd()
    os.chdir(str(project_root))
    try:
        return compile_specs(
            brand_dir=str(project_root / "brands"),
            campaign_path=str(campaign_file),
            channels_dir=str(project_root / "channels"),
            build_dir=project_root / ".build",
        )
    finally:
        os.chdir(orig_cwd)


def main():
    import argparse
    parser = argparse.ArgumentParser(description="BrandKit Compiler")
    parser.add_argument("campaign", help="Path to campaign YAML file")
    parser.add_argument("--brand-dir", default="brands", help="Brands directory")
    parser.add_argument("--channels-dir", default="channels", help="Channels directory")
    parser.add_argument("--build-dir", default=".build", help="Build output directory")
    args = parser.parse_args()

    result = compile_specs(
        brand_dir=args.brand_dir,
        campaign_path=args.campaign,
        channels_dir=args.channels_dir,
        build_dir=Path(args.build_dir),
    )

    if result["status"] == "failed":
        print(f"\n[FAIL] Build failed: {len(result['conflicts'])} conflict(s)")
        sys.exit(1)
    else:
        print(f"\n[OK] Build successful")
        print(f"     Output targets: {len(result['resolved']['output_targets'])}")
        sys.exit(0)


if __name__ == "__main__":
    main()
