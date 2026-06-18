#!/usr/bin/env python3
"""
BrandKit Baseline Runner — 纯 Prompt 基线对照
M1: 用纯 Prompt 方式生成等质量内容，对比 BrandKit 管线

输出: output/baseline/{campaign}/
       + baseline-report.json (耗时/模型调用/人工操作/质量对比)
"""

import json
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
try:
    from copy_generator import call_llm
    HAS_LLM = True
except ImportError:
    HAS_LLM = False


def run_baseline(campaign_path, output_dir, provider="sensenova"):
    """Run pure-prompt baseline for a campaign."""
    import yaml

    with open(campaign_path) as f:
        campaign = yaml.safe_load(f)

    campaign_name = campaign.get("campaign", {}).get("name", "unknown")
    product_ref = campaign.get("campaign", {}).get("product_ref", "")

    # Load product facts
    product = {}
    if product_ref:
        with open(product_ref) as f:
            product = yaml.safe_load(f)

    product_name = product.get("product", {}).get("name", "Product")
    facts = product.get("product", {}).get("facts", {})

    outputs = campaign.get("outputs", {})
    baseline_dir = output_dir / "baseline" / campaign_name
    baseline_dir.mkdir(parents=True, exist_ok=True)

    results = []
    total_start = time.time()

    # Build pure prompt for each output
    for output in outputs.get("visual", []):
        ch = output.get("channel", "")
        scene = output.get("type", "hero")
        fmt = output.get("format", "png")

        prompt = f"""Generate a {scene} product image for {product_name}.

Brand: Aether (premium audio, urban professionals)
Style: Minimal, precise, calm
Colors: Dark navy primary, warm gold accent, off-white background
Product: {product_name}

Facts:
{json.dumps(facts, indent=2)}

Channel: {ch}
Format: {fmt}

Generate a high-quality product image that follows the brand guidelines."""

        start = time.time()
        if HAS_LLM:
            try:
                response = call_llm(
                    "You are a product image prompt generator. Generate detailed image generation prompts.",
                    prompt, provider,
                )
                llm_time = time.time() - start
            except Exception as e:
                response = f"[ERROR] {e}"
                llm_time = time.time() - start
        else:
            response = f"[SIMULATED] Prompt for {product_name} {scene} on {ch}"
            llm_time = 0.5  # Simulated

        result = {
            "type": "visual",
            "channel": ch,
            "scene": scene,
            "format": fmt,
            "prompt": prompt,
            "response": response,
            "llm_time_s": round(llm_time, 2),
            "llm_calls": 1,
        }
        results.append(result)

    for output in outputs.get("content", []):
        ch = output.get("channel", "")
        content_type = output.get("type", "")

        prompt = f"""Write {content_type} for {product_name} on {ch}.

Brand: Aether (premium audio, urban professionals)
Tone: Restrained, precise, confident
Product: {product_name}

Facts:
{json.dumps(facts, indent=2)}

For {ch}:
- tmall: direct conversion style, parameter-focused
- xiaohongshu: experience story style, first-person

Write the {content_type} following brand voice."""

        start = time.time()
        if HAS_LLM:
            try:
                response = call_llm(
                    "You are a brand copywriter. Generate content following brand guidelines.",
                    prompt, provider,
                )
                llm_time = time.time() - start
            except Exception as e:
                response = f"[ERROR] {e}"
                llm_time = time.time() - start
        else:
            response = f"[SIMULATED] {content_type} for {product_name} on {ch}"
            llm_time = 0.5

        result = {
            "type": "content",
            "channel": ch,
            "content_type": content_type,
            "prompt": prompt,
            "response": response,
            "llm_time_s": round(llm_time, 2),
            "llm_calls": 1,
        }
        results.append(result)

    total_time = time.time() - total_start

    # Write baseline report
    report = {
        "campaign": campaign_name,
        "total_time_s": round(total_time, 2),
        "total_llm_calls": sum(r["llm_calls"] for r in results),
        "total_llm_time_s": round(sum(r["llm_time_s"] for r in results), 2),
        "outputs": results,
    }

    report_path = baseline_dir / "baseline-report.json"
    with open(report_path, "w") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    print(f"[OK] Baseline report → {report_path}")

    return report


def compare_with_brandkit(baseline_report, brandkit_build_dir):
    """Compare baseline with BrandKit build results."""
    # Load BrandKit build metrics
    verify_dir = Path(brandkit_build_dir) / "verify"
    brandkit_metrics = {
        "total_time_s": 0,
        "total_llm_calls": 0,
    }

    # BrandKit: compile (0 LLM) + render_visual (0 LLM for HTML, 2 for PNG via Playwright) + render_content (4 LLM calls for copy gen) + verify (0 LLM)
    # Count from output targets — try campaign-scoped paths first
    resolved_path = Path(brandkit_build_dir) / "resolved-task.json"
    if not resolved_path.exists():
        # Try to find campaign-scoped variant
        build_parent = Path(brandkit_build_dir).parent
        for d in build_parent.iterdir():
            if d.is_dir() and not d.name.startswith("."):
                candidate = d / "resolved-task.json"
                if candidate.exists():
                    resolved_path = candidate
                    break
    if resolved_path.exists():
        with open(resolved_path) as f:
            resolved = json.load(f)
        targets = resolved.get("output_targets", [])
        # Content targets use Copy Generator = 1 LLM call each
        content_count = len([t for t in targets if t["type"] == "content"])
        brandkit_metrics["total_llm_calls"] = content_count

    comparison = {
        "baseline": {
            "total_time_s": baseline_report.get("total_time_s", 0),
            "total_llm_calls": baseline_report.get("total_llm_calls", 0),
        },
        "brandkit": brandkit_metrics,
        "improvement": {
            "llm_calls_reduction_pct": 0,
            "time_reduction_pct": 0,
        },
    }

    if brandkit_metrics["total_llm_calls"] > 0 and baseline_report.get("total_llm_calls", 0) > 0:
        comparison["improvement"]["llm_calls_reduction_pct"] = round(
            (1 - brandkit_metrics["total_llm_calls"] / baseline_report["total_llm_calls"]) * 100, 1
        )

    return comparison


def main():
    import argparse
    parser = argparse.ArgumentParser(description="BrandKit Baseline Runner")
    parser.add_argument("campaign", help="Campaign YAML file")
    parser.add_argument("--output-dir", default="output", help="Output directory")
    parser.add_argument("--build-dir", default=".build", help="Build directory")
    parser.add_argument("--provider", default="sensenova")
    parser.add_argument("--dry-run", action="store_true", help="Simulated baseline, no API calls")
    args = parser.parse_args()

    if args.dry_run:
        # Override to simulate
        global HAS_LLM
        HAS_LLM = False

    output_dir = Path(args.output_dir)

    print(f"[BASELINE] Running pure-prompt baseline for: {args.campaign}")
    baseline = run_baseline(args.campaign, output_dir, args.provider)

    print(f"\n[BASELINE] Total time: {baseline['total_time_s']}s")
    print(f"[BASELINE] Total LLM calls: {baseline['total_llm_calls']}")

    # Compare with BrandKit
    comparison = compare_with_brandkit(baseline, args.build_dir)
    print(f"\n[COMPARISON] BrandKit LLM calls: {comparison['brandkit']['total_llm_calls']}")
    print(f"[COMPARISON] Baseline LLM calls: {comparison['baseline']['total_llm_calls']}")
    if comparison["improvement"]["llm_calls_reduction_pct"] > 0:
        print(f"[COMPARISON] LLM call reduction: {comparison['improvement']['llm_calls_reduction_pct']}%")

    # Write comparison
    comp_path = output_dir / "baseline" / Path(args.campaign).stem / "comparison.json"
    comp_path.parent.mkdir(parents=True, exist_ok=True)
    with open(comp_path, "w") as f:
        json.dump(comparison, f, indent=2, ensure_ascii=False)
    print(f"[OK] Comparison → {comp_path}")


if __name__ == "__main__":
    main()
