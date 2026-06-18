#!/usr/bin/env python3
"""
BrandKit Content Renderer (v0.3.0)
FIXES:
- Reads message-plan.json for primary_benefit/theme (不再本地重构)
- Outputs to output/{campaign}/content/
- Falls through to template fallback only with --dry-run
"""

import hashlib
import json
import sys
from pathlib import Path

from run_context import file_sha256

sys.path.insert(0, str(Path(__file__).parent))
try:
    from copy_generator import generate_copy
    HAS_COPY_GEN = True
except ImportError:
    HAS_COPY_GEN = False


def render_content(resolved, output_dir, message_plan, dry_run=False):
    """Generate content from message-plan (single source of truth)."""
    campaign = resolved.get("campaign", {})
    brand = resolved.get("brand", {})
    content_spec = resolved.get("content_spec", {})
    product = resolved.get("product", {})
    output_targets = resolved.get("output_targets", [])

    facts = product.get("facts", {})
    product_name = product.get("name", "Product")

    # Read from message-plan (NOT locally reconstructed)
    primary_benefit = message_plan.get("primary_benefit", {}).get("statement", "")
    secondary_benefits = [b.get("statement", "") for b in message_plan.get("secondary_benefits", [])]
    campaign_theme = message_plan.get("campaign_theme", "")
    brand_name = message_plan.get("brand_name", brand.get("name", "Brand"))

    claim_rules = content_spec.get("claim_rules", {})

    content_targets = [t for t in output_targets if t["type"] == "content"]
    campaign_name = campaign.get("name", "default")
    out_dir = output_dir / campaign_name / "content"
    out_dir.mkdir(parents=True, exist_ok=True)

    rendered = []

    for target in content_targets:
        content_type = target.get("content_type", "")
        channel = target.get("channel", "unknown")
        constraints = target.get("constraints", {})

        # Build proof points from message plan
        proof_points = message_plan.get("proof_points", [])

        # Try Copy Generator unless --dry-run
        claims = []
        if HAS_COPY_GEN and not dry_run:
            try:
                copy_result = generate_copy(
                    message_plan, facts, claim_rules, constraints,
                    content_type, channel, "sensenova",
                )
                if copy_result and copy_result.get("text"):
                    text = copy_result["text"]
                    claims = copy_result.get("claims", [])
                else:
                    raise RuntimeError("Copy generator returned empty text")
            except Exception as e:
                print(f"[FAIL] Copy generator failed for {channel}-{content_type}: {e}")
                sys.exit(1)
        else:
            # Template fallback (only in --dry-run mode)
            if content_type == "product_title":
                title = f"{product_name} {primary_benefit} — 限时特惠"
                title_max = constraints.get("product_title", {}).get("max_chars", 60)
                if len(title) > title_max:
                    title = title[:title_max-3] + "..."
                text = title
                for fact_key, fact_data in facts.items():
                    claims.append({
                        "claim": f"{fact_data.get('value', '')}{fact_data.get('unit', '')}",
                        "fact_ref": f"facts.{fact_key}",
                        "source_ref": fact_data.get("source", {}).get("ref", "unknown"),
                        "status": fact_data.get("status", "unknown"),
                    })
                    break

            elif content_type == "bullet_points":
                bullet_count = constraints.get("bullets", {}).get("count", 5)
                bullets = []
                for fact_key, fact_data in facts.items():
                    val = fact_data.get("value", "")
                    unit = fact_data.get("unit", "")
                    source_type = fact_data.get("source", {}).get("type", "feature")
                    bullets.append(f"【{source_type}】{primary_benefit}：{val}{unit}")
                    claims.append({
                        "claim": f"{val}{unit}",
                        "fact_ref": f"facts.{fact_key}",
                        "source_ref": fact_data.get("source", {}).get("ref", "unknown"),
                        "status": fact_data.get("status", "unknown"),
                    })
                    break
                for b in secondary_benefits:
                    bullets.append(f"· {b}")
                for fact_key, fact_data in list(facts.items())[1:]:
                    val = fact_data.get("value", "")
                    unit = fact_data.get("unit", "")
                    cond = fact_data.get("conditions", fact_key)
                    bullets.append(f"· {cond}：{val}{unit}")
                    claims.append({
                        "claim": f"{val}{unit}",
                        "fact_ref": f"facts.{fact_key}",
                        "source_ref": fact_data.get("source", {}).get("ref", "unknown"),
                        "status": fact_data.get("status", "unknown"),
                    })
                while len(bullets) < bullet_count:
                    # Don't pad with generic filler — stop at available facts
                    break
                bullets = bullets[:bullet_count]
                text = "\n".join(bullets)

            elif content_type == "note":
                facts_text = "、".join([f"{k.replace('_', ' ')}" for k in facts.keys()])
                # Brand-neutral note template — no hardcoded Aether/audio content
                secondary = secondary_benefits[0] if secondary_benefits else "卓越体验"
                benefit_lines = []
                for i, sb in enumerate(secondary_benefits[:3]):
                    benefit_lines.append(f"• {sb}")
                while len(benefit_lines) < 3:
                    benefit_lines.append(f"• {primary_benefit}，{secondary}")
                text = (
                    f"{primary_benefit}，{secondary}。\n\n"
                    f"核心亮点：\n"
                    f"{chr(10).join(benefit_lines)}\n\n"
                    f"参数：{facts_text}\n\n"
                    f"#{primary_benefit.replace(' ', '')}"
                )
                for fact_key, fact_data in facts.items():
                    claims.append({
                        "claim": f"{fact_data.get('value', '')}{fact_data.get('unit', '')}",
                        "fact_ref": f"facts.{fact_key}",
                        "source_ref": fact_data.get("source", {}).get("ref", "unknown"),
                        "status": fact_data.get("status", "unknown"),
                    })

            elif content_type == "title":
                title = f"{primary_benefit} | {product_name}"
                title_max = constraints.get("note_title", {}).get("max_chars", 20)
                if len(title) > title_max:
                    title = title[:title_max-3] + "..."
                text = title
                for fact_key, fact_data in facts.items():
                    claims.append({
                        "claim": f"{fact_data.get('value', '')}{fact_data.get('unit', '')}",
                        "fact_ref": f"facts.{fact_key}",
                        "source_ref": fact_data.get("source", {}).get("ref", "unknown"),
                        "status": fact_data.get("status", "unknown"),
                    })
                    break

            else:
                text = f"# {product_name}\n\n{primary_benefit}"

        # Write content
        filename = f"{channel}-{content_type}.md"
        content_path = out_dir / filename
        with open(content_path, "w") as f:
            f.write(text + "\n")
        print(f"[OK] Content → {content_path}")

        # Write provenance
        prov_filename = f"{channel}-{content_type}.provenance.json"
        prov_path = out_dir / prov_filename
        with open(prov_path, "w") as f:
            json.dump({
                "file": filename,
                "channel": channel,
                "content_type": content_type,
                "primary_benefit_source": "message-plan.json",
                "claims": claims,
            }, f, indent=2, ensure_ascii=False)
        print(f"[OK] Provenance → {prov_path}")

        rendered.append({
            "channel": channel,
            "content_type": content_type,
            "file": str(content_path),
            "claims_count": len(claims),
            "generation_mode": "copy_generator" if (HAS_COPY_GEN and not dry_run) else ("dry_run_fallback" if dry_run else "template_fallback"),
        })

    return rendered


def main():
    import argparse
    parser = argparse.ArgumentParser(description="BrandKit Content Renderer (v0.3.0)")
    parser.add_argument("--resolved", default=".build/resolved-task.json")
    parser.add_argument("--message-plan", default=".build/message-plan.json")
    parser.add_argument("--output-dir", default="output")
    parser.add_argument("--manifest", help="Explicit run manifest path")
    parser.add_argument("--dry-run", action="store_true", help="Use template fallback instead of LLM")
    args = parser.parse_args()

    # Resolve campaign-scoped path — try default first, fallback to scoped
    resolved_path = Path(args.resolved)
    if not resolved_path.exists():
        candidate_dirs = [d for d in Path("output").iterdir() if d.is_dir() and not d.name.startswith(".")]
        if candidate_dirs:
            campaign_name = candidate_dirs[0].name
            scoped = Path(f".build/{campaign_name}/resolved-task.json")
            if scoped.exists():
                resolved_path = scoped
                args.resolved = str(scoped)
    if not resolved_path.exists():
        print(f"[ERROR] Resolved task not found: {resolved_path}")
        sys.exit(1)

    with open(resolved_path) as f:
        resolved = json.load(f)

    # Determine campaign name from resolved task for scoped paths
    campaign_name = resolved.get("campaign", {}).get("name", "")

    # Load message-plan — try scoped path
    msg_path = Path(args.message_plan)
    if not msg_path.exists() and campaign_name:
        scoped_msg = Path(f".build/{campaign_name}/message-plan.json")
        if scoped_msg.exists():
            msg_path = scoped_msg
    message_plan = {}
    if msg_path.exists():
        with open(msg_path) as f:
            message_plan = json.load(f)
    else:
        print(f"[WARN] message-plan.json not found, using fallback")
        content_spec = resolved.get("content_spec", {})
        mh = content_spec.get("message_hierarchy", {})
        message_plan = {
            "primary_benefit": {"statement": mh.get("primary_benefit", "")},
            "secondary_benefits": [{"statement": b} for b in mh.get("secondary_benefits", [])],
        }

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Extract campaign name for manifest path
    campaign_name = resolved.get("campaign", {}).get("name", "default")

    mode = "dry-run fallback" if args.dry_run else "copy generator (LLM)"
    print(f"[INFO] Content mode: {mode}")
    rendered = render_content(resolved, output_dir, message_plan, args.dry_run)

    total_claims = sum(r.get("claims_count", 0) for r in rendered)
    gen_modes = set(r.get("generation_mode", "") for r in rendered)
    print(f"\n[OK] Content render: {len(rendered)} output(s), {total_claims} claim(s)")
    print(f"     Generation mode(s): {', '.join(gen_modes)}")

    # Append rendered artifacts to manifest
    manifest_path = Path(args.manifest) if args.manifest else Path(f".build/manifest-{campaign_name}.json")
    if manifest_path.exists():
        try:
            manifest = json.loads(manifest_path.read_text())
        except (json.JSONDecodeError, OSError):
            manifest = {}
        if "artifacts" not in manifest:
            manifest["artifacts"] = {}
        for r in rendered:
            content_path = Path(r["file"]).resolve()
            if content_path.exists():
                rel = str(content_path.relative_to(Path.cwd().resolve()))
                manifest["artifacts"][rel] = {
                    "sha256": file_sha256(content_path),
                    "category": "content",
                    "content_type": r.get("content_type", ""),
                }
            # Also record provenance file
            prov_path = content_path.with_suffix(".provenance.json")
            if prov_path.exists():
                prov_rel = str(prov_path.relative_to(Path.cwd().resolve()))
                manifest["artifacts"][prov_rel] = {
                    "sha256": file_sha256(prov_path),
                    "category": "content_provenance",
                    "content_type": r.get("content_type", ""),
                }
        manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False))
        print(f"[OK] Manifest updated: {len(rendered)} content artifact(s)")


if __name__ == "__main__":
    main()
