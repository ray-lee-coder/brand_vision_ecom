#!/usr/bin/env python3
"""
BrandKit Content Renderer — Content Pipeline → Markdown
M0-A+: 使用 Copy Generator 替代模板拼接，全量 Claim Provenance
"""

import json
import os
import sys
from pathlib import Path

# Try to import copy generator
sys.path.insert(0, str(Path(__file__).parent))
try:
    from copy_generator import generate_copy
    HAS_COPY_GEN = True
except ImportError:
    HAS_COPY_GEN = False


def render_content(resolved, output_dir, provider="sensenova", dry_run=False):
    """Generate content from resolved task + message plan."""
    campaign = resolved.get("campaign", {})
    brand = resolved.get("brand", {})
    content_spec = resolved.get("content_spec", {})
    product = resolved.get("product", {})
    channels = resolved.get("channels", {})
    output_targets = resolved.get("output_targets", [])

    facts = product.get("facts", {})
    product_name = product.get("name", "Product")

    message_hierarchy = content_spec.get("message_hierarchy", {})
    primary_benefit = message_hierarchy.get("primary_benefit", "")
    secondary_benefits = message_hierarchy.get("secondary_benefits", [])

    claim_rules = content_spec.get("claim_rules", {})

    content_targets = [t for t in output_targets if t["type"] == "content"]

    rendered = []

    for target in content_targets:
        content_type = target.get("content_type", "")
        channel = target.get("channel", "unknown")
        constraints = target.get("constraints", {})

        # Build message plan for this output
        message_plan = {
            "campaign_theme": "quiet_precision",
            "primary_benefit": {
                "id": primary_benefit,
                "statement": primary_benefit,
            },
            "secondary_benefits": [{"id": b, "statement": b} for b in secondary_benefits],
            "proof_points": [],
            "call_to_action": {
                "tmall": "立即了解",
                "xiaohongshu": "查看通勤实测",
            },
        }

        # Build proof points from facts
        for fact_key, fact_data in facts.items():
            message_plan["proof_points"].append({
                "claim_ref": f"facts.{fact_key}",
                "value": f"{fact_data.get('value', '')}{fact_data.get('unit', '')}",
                "source_ref": fact_data.get("source", {}).get("ref", "unknown"),
                "status": fact_data.get("status", "unknown"),
            })

        # Try Copy Generator first
        copy_result = None
        if HAS_COPY_GEN and not dry_run:
            try:
                copy_result = generate_copy(
                    message_plan, facts, claim_rules, constraints,
                    content_type, channel, provider,
                )
            except Exception as e:
                print(f"[WARN] Copy generator failed for {channel}-{content_type}: {e}")
                copy_result = None

        if copy_result and copy_result.get("text"):
            text = copy_result["text"]
            claims = copy_result.get("claims", [])
        else:
            # Fallback: template stitching (same as before)
            claims = []
            if content_type == "product_title":
                title = f"{product_name} {primary_benefit} — 618限时特惠"
                title_max = constraints.get("product_title", {}).get("max_chars", 60)
                if len(title) > title_max:
                    title = title[:title_max-3] + "..."
                text = title
                # Provenance for title
                for fact_key, fact_data in facts.items():
                    claims.append({
                        "claim": f"{fact_data.get('value', '')}{fact_data.get('unit', '')}",
                        "fact_ref": f"facts.{fact_key}",
                        "source_ref": fact_data.get("source", {}).get("ref", "unknown"),
                        "status": fact_data.get("status", "unknown"),
                    })
                    break  # Just first fact

            elif content_type == "bullet_points":
                bullet_count = constraints.get("bullets", {}).get("count", 5)
                max_chars = constraints.get("bullets", {}).get("max_chars_each", 28)
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
                    bullets.append(f"· 品质保障，安心选购")
                bullets = bullets[:bullet_count]
                text = "\n".join(bullets)

            elif content_type == "note":
                facts_text = "、".join([f"{k.replace('_', ' ')}" for k in facts.keys()])
                text = (
                    f"通勤路上终于找到了我的降噪搭子✨\n\n"
                    f"{primary_benefit}，{secondary_benefits[0] if secondary_benefits else '舒适佩戴'}。\n\n"
                    f"用了两周最深的感受是：\n"
                    f"• 地铁上开降噪，世界瞬间安静\n"
                    f"• {secondary_benefits[1] if len(secondary_benefits) > 1 else '佩戴一整天也不累'}\n"
                    f"• {secondary_benefits[2] if len(secondary_benefits) > 2 else '连接稳定不断连'}\n\n"
                    f"参数党看这里：{facts_text}\n\n"
                    f"618活动入手性价比超高，通勤党可以冲。\n\n"
                    f"#降噪耳机 #通勤好物 #Aether"
                )
                # Provenance for note
                for fact_key, fact_data in facts.items():
                    claims.append({
                        "claim": f"{fact_data.get('value', '')}{fact_data.get('unit', '')}",
                        "fact_ref": f"facts.{fact_key}",
                        "source_ref": fact_data.get("source", {}).get("ref", "unknown"),
                        "status": fact_data.get("status", "unknown"),
                    })

            elif content_type == "title":
                title = f"{primary_benefit}的通勤神器"
                title_max = constraints.get("note_title", {}).get("max_chars", 20)
                if len(title) > title_max:
                    title = title[:title_max-3] + "..."
                text = title
                # Provenance for title
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
        content_path = output_dir / filename
        with open(content_path, "w") as f:
            f.write(text + "\n")
        print(f"[OK] Content → {content_path}")

        # Write provenance
        if claims:
            prov_filename = f"{channel}-{content_type}.provenance.json"
            prov_path = output_dir / prov_filename
            with open(prov_path, "w") as f:
                json.dump({
                    "file": filename,
                    "channel": channel,
                    "content_type": content_type,
                    "claims": claims,
                }, f, indent=2, ensure_ascii=False)
            print(f"[OK] Provenance → {prov_path}")

        rendered.append({
            "channel": channel,
            "content_type": content_type,
            "file": str(content_path),
            "claims_count": len(claims),
        })

    return rendered


def main():
    import argparse
    parser = argparse.ArgumentParser(description="BrandKit Content Renderer")
    parser.add_argument("--resolved", default=".build/resolved-task.json", help="Resolved task JSON")
    parser.add_argument("--output-dir", default="output", help="Output directory")
    parser.add_argument("--provider", default="sensenova", help="LLM provider for copy generation")
    parser.add_argument("--dry-run", action="store_true", help="Use template fallback, no API calls")
    args = parser.parse_args()

    resolved_path = Path(args.resolved)
    if not resolved_path.exists():
        print(f"[ERROR] Resolved task not found: {resolved_path}")
        print("        Run compile.py first.")
        sys.exit(1)

    with open(resolved_path) as f:
        resolved = json.load(f)

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    rendered = render_content(resolved, output_dir, args.provider, args.dry_run)
    total_claims = sum(r.get("claims_count", 0) for r in rendered)
    print(f"\n[OK] Content render complete: {len(rendered)} output(s), {total_claims} claim(s) with provenance")


if __name__ == "__main__":
    main()
