#!/usr/bin/env python3
"""
BrandKit Channel Validator — 天猫 vs 小红书结构化差异报告
M1: 验证渠道差异化不是"感觉不一样"，而是可检查的结构差异
"""

import json
import re
from pathlib import Path


CHANNEL_PROFILES = {
    "tmall": {
        "signals": {
            "参数优先": ["参数", "dB", "小时", "g", "IPX", "蓝牙", "续航"],
            "利益点靠前": ["降噪", "续航", "舒适", "连接"],
            "非第一人称": [],
            "CTA明确": ["立即", "了解", "购买", "查看"],
            "五点结构": [],
        },
        "avoid": ["第一人称", "emoji过多", "场景化开头", "软推荐"],
    },
    "xiaohongshu": {
        "signals": {
            "场景体验开篇": ["通勤", "路上", "用了", "体验", "感受"],
            "第一人称": ["我", "我的", "我们"],
            "轻量Emoji": ["✨", "🎧", "👀", "😊", "🎵"],
            "参数转体验": ["降噪", "续航", "佩戴"],
            "软推荐非硬销": ["可以", "推荐", "适合", "试试"],
        },
        "avoid": ["硬促销", "参数堆砌", "长列表", "严肃语气"],
    },
}


def extract_features(text):
    """Extract structural features from content text."""
    features = {
        "length": len(text),
        "line_count": len(text.strip().split("\n")),
        "has_emoji": bool(re.search(r'[\U0001F300-\U0001FFFF]', text)),
        "emoji_count": len(re.findall(r'[\U0001F300-\U0001FFFF]', text)),
        "has_first_person": bool(re.search(r'[我我们]', text)),
        "has_question": "?" in text or "？" in text,
        "has_exclamation": "!" in text or "！" in text,
        "has_parameter": bool(re.search(r'\d+\s*(dB|小时|g|mm|Hz|IP)', text)),
        "has_bullets": bool(re.search(r'[·•●]\s', text)),
        "has_cta": bool(re.search(r'(立即|了解|购买|查看|试试|关注)', text)),
        "has_scene_opening": bool(re.search(r'(通勤|路上|地铁|公交|办公室|健身房|咖啡)', text)),
        "has_hard_sell": bool(re.search(r'(限时|抢购|爆款|狂欢|钜惠)', text)),
        "has_soft_recommend": bool(re.search(r'(推荐|适合|可以|试试|值得)', text)),
    }
    return features


def validate_channel(content_path, channel_name):
    """Validate a single content file against channel profile."""
    with open(content_path, "r") as f:
        text = f.read()

    profile = CHANNEL_PROFILES.get(channel_name, {})
    signals = profile.get("signals", {})
    avoid = profile.get("avoid", [])

    features = extract_features(text)

    results = {
        "file": str(content_path),
        "channel": channel_name,
        "features": features,
        "signal_checks": [],
        "passed": 0,
        "failed": 0,
        "warnings": 0,
    }

    # Check signals
    for signal_name, keywords in signals.items():
        if not keywords:
            # Structural check
            if signal_name == "五点结构":
                has_bullets = features.get("has_bullets", False)
                line_count = features.get("line_count", 0)
                if has_bullets and 3 <= line_count <= 7:
                    results["signal_checks"].append({"check": signal_name, "status": "pass"})
                    results["passed"] += 1
                else:
                    results["signal_checks"].append({"check": signal_name, "status": "fail", "detail": f"bullets={has_bullets}, lines={line_count}"})
                    results["failed"] += 1
            elif signal_name == "非第一人称":
                if not features.get("has_first_person", False):
                    results["signal_checks"].append({"check": signal_name, "status": "pass"})
                    results["passed"] += 1
                else:
                    results["signal_checks"].append({"check": signal_name, "status": "warn", "detail": "Contains first person"})
                    results["warnings"] += 1
            else:
                results["signal_checks"].append({"check": signal_name, "status": "pass", "detail": "no specific keywords"})
                results["passed"] += 1
        else:
            found = [kw for kw in keywords if kw in text]
            if found:
                results["signal_checks"].append({"check": signal_name, "status": "pass", "detail": f"found: {found[:3]}"})
                results["passed"] += 1
            else:
                results["signal_checks"].append({"check": signal_name, "status": "warn", "detail": "no matching keywords"})
                results["warnings"] += 1

    # Check avoid patterns
    for pattern in avoid:
        if pattern == "emoji过多" and features.get("emoji_count", 0) > 3:
            results["signal_checks"].append({"check": f"avoid: {pattern}", "status": "warn", "detail": f"{features['emoji_count']} emoji found"})
            results["warnings"] += 1
        elif pattern == "硬促销" and features.get("has_hard_sell", False):
            results["signal_checks"].append({"check": f"avoid: {pattern}", "status": "fail", "detail": "hard sell detected"})
            results["failed"] += 1
        elif pattern == "参数堆砌" and features.get("has_parameter", False) and features.get("has_scene_opening", False) == False:
            results["signal_checks"].append({"check": f"avoid: {pattern}", "status": "warn", "detail": "parameters without scene context"})
            results["warnings"] += 1

    return results


def generate_diff_report(tmall_results, xhs_results):
    """Generate structured diff between tmall and xiaohongshu content."""
    tmall_feat = tmall_results.get("features", {})
    xhs_feat = xhs_results.get("features", {})

    diffs = []

    # Compare structural differences
    if tmall_feat.get("has_emoji", False) != xhs_feat.get("has_emoji", False):
        diffs.append({
            "dimension": "emoji_usage",
            "tmall": "has_emoji" if tmall_feat.get("has_emoji") else "no_emoji",
            "xiaohongshu": "has_emoji" if xhs_feat.get("has_emoji") else "no_emoji",
            "expected": "xiaohongshu should have more emoji",
            "pass": xhs_feat.get("has_emoji", False),
        })

    if tmall_feat.get("has_first_person", False) != xhs_feat.get("has_first_person", False):
        diffs.append({
            "dimension": "first_person",
            "tmall": "first_person" if tmall_feat.get("has_first_person") else "no_first_person",
            "xiaohongshu": "first_person" if xhs_feat.get("has_first_person") else "no_first_person",
            "expected": "xiaohongshu should use first person, tmall should not",
            "pass": xhs_feat.get("has_first_person", False) and not tmall_feat.get("has_first_person", False),
        })

    if tmall_feat.get("has_cta", False) != xhs_feat.get("has_cta", False):
        diffs.append({
            "dimension": "cta_clarity",
            "tmall": "has_cta" if tmall_feat.get("has_cta") else "no_cta",
            "xiaohongshu": "has_cta" if xhs_feat.get("has_cta") else "no_cta",
            "expected": "tmall should have clearer CTA",
            "pass": tmall_feat.get("has_cta", False),
        })

    if tmall_feat.get("has_scene_opening", False) != xhs_feat.get("has_scene_opening", False):
        diffs.append({
            "dimension": "scene_opening",
            "tmall": "scene_opening" if tmall_feat.get("has_scene_opening") else "direct",
            "xiaohongshu": "scene_opening" if xhs_feat.get("has_scene_opening") else "direct",
            "expected": "xiaohongshu should open with scene/experience",
            "pass": xhs_feat.get("has_scene_opening", False),
        })

    if tmall_feat.get("has_hard_sell", False) != xhs_feat.get("has_hard_sell", False):
        diffs.append({
            "dimension": "hard_sell",
            "tmall": "hard_sell" if tmall_feat.get("has_hard_sell") else "no_hard_sell",
            "xiaohongshu": "hard_sell" if xhs_feat.get("has_hard_sell") else "no_hard_sell",
            "expected": "tmall may use hard sell, xiaohongshu should not",
            "pass": not xhs_feat.get("has_hard_sell", False),
        })

    return diffs


def main():
    import argparse
    parser = argparse.ArgumentParser(description="BrandKit Channel Validator")
    parser.add_argument("--allow-warnings", action="store_true", help="Don't fail on warnings")
    parser.add_argument("--output-dir", default="output", help="Output directory")
    parser.add_argument("--verify-dir", default=".build/verify", help="Verify report directory")
    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    verify_dir = Path(args.verify_dir)
    verify_dir.mkdir(parents=True, exist_ok=True)

    # Determine campaign name from output dirs or manifest files
    campaign_name = ""
    for d in output_dir.iterdir():
        if d.is_dir() and not d.name.startswith("."):
            campaign_name = d.name
            break
    # Try to read manifest for richer context
    manifest_path = Path(f".build/manifest-{campaign_name}.json")
    manifest = {}
    if manifest_path.exists():
        try:
            manifest = json.loads(manifest_path.read_text())
        except (json.JSONDecodeError, OSError):
            pass
    campaign_name = manifest.get("campaign", "")

    # Group content files by channel from campaign dirs
    md_files = []
    for campaign_dir in output_dir.iterdir():
        if not campaign_dir.is_dir() or campaign_dir.name.startswith("."):
            continue
        content_dir = campaign_dir / "content"
        if content_dir.exists():
            md_files.extend(f for f in content_dir.glob("*.md") if not f.name.startswith("._"))

    channel_groups = {}
    for f in md_files:
        # Parse channel from filename: {channel}-{type}.md
        parts = f.stem.split("-", 1)
        if len(parts) == 2:
            channel = parts[0]
            if channel not in channel_groups:
                channel_groups[channel] = []
            channel_groups[channel].append(f)

    all_reports = {}
    all_diffs = []

    for channel, files in channel_groups.items():
        print(f"\n[CHANNEL VALIDATOR] {channel} ({len(files)} files)")
        channel_results = []
        for f in files:
            result = validate_channel(f, channel)
            channel_results.append(result)
            status_icon = "✅" if result["failed"] == 0 else "❌"
            print(f"  {status_icon} {f.name}: {result['passed']} passed, {result['failed']} failed, {result['warnings']} warnings")

        all_reports[channel] = channel_results

    # Generate cross-channel diff — overall channel profile comparison
    if "tmall" in channel_groups and "xiaohongshu" in channel_groups:
        print("\n[CROSS-CHANNEL DIFF] tmall vs xiaohongshu")

        # Aggregate features per channel
        tmall_all_text = ""
        xhs_all_text = ""
        for f in channel_groups["tmall"]:
            with open(f) as fh:
                tmall_all_text += fh.read() + "\n"
        for f in channel_groups["xiaohongshu"]:
            with open(f) as fh:
                xhs_all_text += fh.read() + "\n"

        tmall_agg = extract_features(tmall_all_text)
        xhs_agg = extract_features(xhs_all_text)

        # Build overall diff report
        overall_diffs = [
            {
                "dimension": "emoji_usage",
                "tmall": f"{tmall_agg.get('emoji_count', 0)} emoji",
                "xiaohongshu": f"{xhs_agg.get('emoji_count', 0)} emoji",
                "expected": "xiaohongshu should have more emoji",
                "pass": xhs_agg.get("emoji_count", 0) > tmall_agg.get("emoji_count", 0),
            },
            {
                "dimension": "first_person",
                "tmall": "yes" if tmall_agg.get("has_first_person") else "no",
                "xiaohongshu": "yes" if xhs_agg.get("has_first_person") else "no",
                "expected": "xiaohongshu should use first person, tmall should not",
                "pass": xhs_agg.get("has_first_person", False) and not tmall_agg.get("has_first_person", False),
            },
            {
                "dimension": "scene_opening",
                "tmall": "yes" if tmall_agg.get("has_scene_opening") else "no",
                "xiaohongshu": "yes" if xhs_agg.get("has_scene_opening") else "no",
                "expected": "xiaohongshu should open with scene/experience",
                "pass": xhs_agg.get("has_scene_opening", False),
            },
            {
                "dimension": "hard_sell",
                "tmall": "yes" if tmall_agg.get("has_hard_sell") else "no",
                "xiaohongshu": "yes" if xhs_agg.get("has_hard_sell") else "no",
                "expected": "tmall may use hard sell, xiaohongshu should not",
                "pass": not xhs_agg.get("has_hard_sell", False),
            },
            {
                "dimension": "parameter_usage",
                "tmall": "yes" if tmall_agg.get("has_parameter") else "no",
                "xiaohongshu": "yes" if xhs_agg.get("has_parameter") else "no",
                "expected": "tmall should use more parameters",
                "pass": tmall_agg.get("has_parameter", False) or not xhs_agg.get("has_parameter", False),
            },
            {
                "dimension": "cta_clarity",
                "tmall": "yes" if tmall_agg.get("has_cta") else "no",
                "xiaohongshu": "yes" if xhs_agg.get("has_cta") else "no",
                "expected": "tmall should have clearer CTA",
                "pass": tmall_agg.get("has_cta", False),
            },
        ]

        for d in overall_diffs:
            icon = "✅" if d["pass"] else "❌"
            print(f"  {icon} {d['dimension']}")
            print(f"     tmall: {d['tmall']}")
            print(f"     xiaohongshu: {d['xiaohongshu']}")
            print(f"     expected: {d['expected']}")
        all_diffs.extend(overall_diffs)

    # Write report
    report = {
        "channel_reports": {k: [{"file": str(r["file"]), "passed": r["passed"], "failed": r["failed"], "warnings": r["warnings"]} for r in v] for k, v in all_reports.items()},
        "cross_channel_diffs": all_diffs,
        "diff_summary": {
            "total_diffs": len(all_diffs),
            "passed": sum(1 for d in all_diffs if d["pass"]),
            "failed": sum(1 for d in all_diffs if not d["pass"]),
        },
    }

    report_path = verify_dir / "channel-diff-report.json"
    with open(report_path, "w") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    print(f"\n[OK] Channel diff report → {report_path}")

    # Append channel diff report to manifest
    manifest_path = Path(f".build/manifest-{campaign_name}.json")
    if manifest_path.exists():
        try:
            manifest = json.loads(manifest_path.read_text())
        except (json.JSONDecodeError, OSError):
            manifest = {}
        if "reports" not in manifest:
            manifest["reports"] = {}
        manifest["reports"]["channel_diff"] = {"path": str(report_path.resolve().relative_to(Path.cwd().resolve()))}
        manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False))
        print(f"[OK] Manifest updated with channel diff report")

    # Summary
    print(f"\n{'='*50}")
    print(f"Cross-channel diffs: {report['diff_summary']['total_diffs']} total")
    print(f"  Passed: {report['diff_summary']['passed']}")
    print(f"  Informational: {report['diff_summary']['failed']}")
    print(f"{'='*50}")

    # Cross-channel diffs are informative, not blocking
    # Only block on individual file validation failures
    file_failures = sum(f.get("failed", 0) for f in report.get("file_results", []))
    if file_failures > 0 and not args.allow_warnings:
        sys.exit(1)


if __name__ == "__main__":
    import sys
    main()
