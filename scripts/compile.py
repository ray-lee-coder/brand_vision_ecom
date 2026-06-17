#!/usr/bin/env python3
"""
BrandKit Compiler — Spec 合并 + 冲突检测 + 编译输出
M0-A: Compiler Spine

读取: brand-core / visual-spec / content-spec / product-facts / channels / campaign
输出: .build/resolved-task.json + .build/message-plan.json
"""

import json
import os
import sys
from pathlib import Path
import yaml


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
    Returns list of conflict dicts.
    """
    conflicts = []

    # Check forbidden colors
    brand_forbidden = set(resolved.get("brand", {}).get("colors", {}).get("forbidden", []))
    campaign_overrides = sources.get("campaign", {}).get("override", {})

    # Check claims against product facts
    brand_claims = resolved.get("brand", {}).get("claims", {}).get("require_evidence", [])
    product_facts = resolved.get("product", {}).get("facts", {})

    # Check if campaign asks for forbidden claims
    # (campaign override might contain forbidden patterns)
    for key, val in campaign_overrides.items():
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

    return conflicts


def compile_specs(brand_dir, campaign_path, channels_dir, build_dir):
    """Main compile function."""
    # Load campaign
    campaign = load_yaml(campaign_path)
    campaign_name = campaign["campaign"]["name"]

    # Resolve brand ref
    brand_ref = campaign["campaign"]["brand_ref"]
    brand_dir_resolved = Path(brand_ref).parent
    brand_core = load_yaml(brand_ref)

    # Load visual-spec + content-spec
    visual_spec = load_yaml(str(brand_dir_resolved / "visual-spec.yaml"))
    content_spec = load_yaml(str(brand_dir_resolved / "content-spec.yaml"))

    # Load product facts
    product_ref = campaign["campaign"]["product_ref"]
    product_facts = load_yaml(product_ref)

    # Load channels
    channels = {}
    outputs = campaign.get("outputs", {})
    for output in outputs.get("visual", []) + outputs.get("content", []):
        ch = output.get("channel")
        if ch and ch not in channels:
            ch_path = Path(channels_dir) / f"{ch}.yaml"
            if ch_path.exists():
                channels[ch] = load_yaml(str(ch_path))

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
    resolved["visual_spec"] = visual_spec.get("visual", {})
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
                print(f"[CONFLICT] {c['field']}: '{c['value']}' conflicts with {c['conflict_with']}")
        return {"status": "failed", "conflicts": conflicts}

    # ── Build message plan ──
    primary_benefit_id = content_spec.get("content", {}).get("message_hierarchy", {}).get("primary_benefit", "")
    secondary_benefits = content_spec.get("content", {}).get("message_hierarchy", {}).get("secondary_benefits", [])

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
        "campaign_theme": "quiet_precision",
        "primary_benefit": {
            "id": primary_benefit_id,
            "statement": primary_benefit_id,
        },
        "secondary_benefits": [{"id": b, "statement": b} for b in secondary_benefits],
        "proof_points": proof_points,
        "call_to_action": {
            "tmall": "立即了解",
            "xiaohongshu": "查看通勤实测",
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

    return {"status": "ok", "resolved": resolved, "message_plan": message_plan}


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
