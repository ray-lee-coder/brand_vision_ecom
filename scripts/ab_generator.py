#!/usr/bin/env python3
"""
BrandKit A/B Draft Generator — 多版本内容草稿
M1: 同一内容类型输出 2 个版本供选择
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
try:
    from copy_generator import generate_copy, build_system_prompt, build_user_prompt
    HAS_COPY_GEN = True
except ImportError:
    HAS_COPY_GEN = False


def generate_ab_drafts(message_plan, facts, claim_rules, channel_constraints, content_type, channel_name, provider="sensenova", dry_run=False):
    """Generate 2 variant drafts for the same content type."""
    if not HAS_COPY_GEN or dry_run:
        return generate_ab_fallback(message_plan, facts, claim_rules, channel_constraints, content_type, channel_name)

    drafts = []

    # Variant A: default style
    result_a = generate_copy(message_plan, facts, claim_rules, channel_constraints, content_type, channel_name, provider)
    if result_a and result_a.get("text"):
        drafts.append({
            "variant": "A",
            "style": "default",
            "text": result_a["text"],
            "claims": result_a.get("claims", []),
        })

    # Variant B: alternative style (adjust temperature or prompt)
    # Modify channel constraints slightly for variant B
    alt_constraints = dict(channel_constraints)
    if channel_name == "tmall":
        alt_constraints["style"] = "benefit_first"
    elif channel_name == "xiaohongshu":
        alt_constraints["style"] = "story_first"

    result_b = generate_copy(message_plan, facts, claim_rules, alt_constraints, content_type, channel_name, provider)
    if result_b and result_b.get("text"):
        drafts.append({
            "variant": "B",
            "style": "alternative",
            "text": result_b["text"],
            "claims": result_b.get("claims", []),
        })

    return drafts


def generate_ab_fallback(message_plan, facts, claim_rules, channel_constraints, content_type, channel_name):
    """Fallback A/B when copy generator is unavailable."""
    primary = message_plan.get("primary_benefit", {}).get("statement", "")
    secondary = message_plan.get("secondary_benefits", [])
    product_name = ""

    drafts = []

    # Variant A: benefit-first
    if content_type == "product_title":
        text_a = f"{product_name} {primary} — 限时特惠" if product_name else f"{primary} — 限时特惠"
        text_b = f"618必入 | {product_name} {primary}" if product_name else f"618必入 | {primary}"
    elif content_type == "bullet_points":
        text_a = f"· {primary}\n· {secondary[0] if secondary else ''}\n· {secondary[1] if len(secondary) > 1 else ''}"
        text_b = f"• 核心卖点：{primary}\n• {secondary[0] if secondary else ''}\n• {secondary[1] if len(secondary) > 1 else ''}"
    elif content_type == "note":
        text_a = f"{primary}，{secondary[0] if secondary else ''}。用了就回不去了。"
        text_b = f"终于找到{primary}的神器了！{secondary[0] if secondary else ''}真的绝。"
    elif content_type == "title":
        text_a = f"{primary}首选"
        text_b = f"{primary}？选它就对了"
    else:
        text_a = primary
        text_b = primary

    drafts.append({"variant": "A", "style": "benefit_first", "text": text_a, "claims": []})
    drafts.append({"variant": "B", "style": "alternative", "text": text_b, "claims": []})

    return drafts


def main():
    import argparse
    parser = argparse.ArgumentParser(description="BrandKit A/B Draft Generator")
    parser.add_argument("--resolved", default=".build/resolved-task.json")
    parser.add_argument("--message-plan", default=".build/message-plan.json")
    parser.add_argument("--content-type", default="product_title")
    parser.add_argument("--channel", default="tmall")
    parser.add_argument("--output-dir", default="output")
    parser.add_argument("--provider", default="sensenova")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    # Resolve campaign-scoped paths
    resolved_path = Path(args.resolved)
    if not resolved_path.exists():
        candidate_dirs = [d for d in Path("output").iterdir() if d.is_dir() and not d.name.startswith(".")]
        if candidate_dirs:
            camp = candidate_dirs[0].name
            scoped = Path(f".build/{camp}/resolved-task.json")
            if scoped.exists():
                resolved_path = scoped

    with open(resolved_path) as f:
        resolved = json.load(f)

    campaign_name = resolved.get("campaign", {}).get("name", "")

    msg_path = Path(args.message_plan)
    if not msg_path.exists() and campaign_name:
        scoped_msg = Path(f".build/{campaign_name}/message-plan.json")
        if scoped_msg.exists():
            msg_path = scoped_msg
    with open(msg_path) as f:
        message_plan = json.load(f)

    facts = resolved.get("product", {}).get("facts", {})
    content_spec = resolved.get("content_spec", {})
    claim_rules = content_spec.get("claim_rules", {})
    channels = resolved.get("channels", {})
    ch_data = channels.get(args.channel, {})
    ch_content = ch_data.get("content", {})

    drafts = generate_ab_drafts(
        message_plan, facts, claim_rules, ch_content,
        args.content_type, args.channel, args.provider, args.dry_run,
    )

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    for draft in drafts:
        filename = f"{args.channel}-{args.content_type}-{draft['variant']}.md"
        path = output_dir / filename
        with open(path, "w") as f:
            f.write(draft["text"] + "\n")
        print(f"[OK] A/B Draft {draft['variant']} → {path}")

    print(f"\n[OK] Generated {len(drafts)} draft(s)")


if __name__ == "__main__":
    main()
