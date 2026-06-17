#!/usr/bin/env python3
"""
BrandKit Verifier — L1 视觉断言 + Claim Checker
M0-A: 验证编译正确性
"""

import json
import os
import sys
from pathlib import Path
import re


def verify_visual(html_path, resolved):
    """L1 visual assertions via Playwright getComputedStyle."""
    brand = resolved.get("brand", {})
    colors = brand.get("colors", {})
    expected_primary = colors.get("primary", "#000000").lower()
    expected_background = colors.get("background", "#FFFFFF").lower()
    expected_accent = colors.get("accent", "#888888").lower()

    results = {
        "file": str(html_path),
        "checks": [],
        "passed": 0,
        "failed": 0,
    }

    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        results["error"] = "playwright not installed"
        return results

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page()
            page.goto(f"file://{html_path.resolve()}", wait_until="networkidle")

            # Check CSS variables
            checks = [
                ("primary color", "--brand-primary", expected_primary),
                ("background color", "--brand-background", expected_background),
                ("accent color", "--brand-accent", expected_accent),
            ]

            for name, var, expected in checks:
                actual = page.evaluate(f"getComputedStyle(document.documentElement).getPropertyValue('{var}').trim().toLowerCase()")
                if actual == expected:
                    results["checks"].append({"check": name, "status": "pass", "expected": expected, "actual": actual})
                    results["passed"] += 1
                else:
                    results["checks"].append({"check": name, "status": "fail", "expected": expected, "actual": actual})
                    results["failed"] += 1

            # Check safe margin
            safe_margin = page.evaluate("getComputedStyle(document.documentElement).getPropertyValue('--safe-margin').trim()")
            results["checks"].append({"check": "safe-margin defined", "status": "pass" if safe_margin else "fail", "value": safe_margin})
            if safe_margin:
                results["passed"] += 1
            else:
                results["failed"] += 1

            browser.close()

    except Exception as e:
        results["error"] = str(e)

    return results


def verify_content(content_path, resolved):
    """Claim Checker: verify content against brand rules and product facts."""
    brand = resolved.get("brand", {})
    claims = brand.get("claims", {})
    require_evidence = claims.get("require_evidence", [])

    claim_rules = resolved.get("content_spec", {}).get("claim_rules", {})
    forbidden_phrases = claim_rules.get("forbidden", [])

    product = resolved.get("product", {})
    facts = product.get("facts", {})

    with open(content_path, "r") as f:
        text = f.read()

    results = {
        "file": str(content_path),
        "checks": [],
        "passed": 0,
        "failed": 0,
    }

    # Check forbidden phrases
    for phrase in forbidden_phrases:
        if phrase.lower() in text.lower():
            results["checks"].append({
                "check": f"forbidden phrase: '{phrase}'",
                "status": "fail",
                "detail": f"Found in content: '{phrase}'",
            })
            results["failed"] += 1
        else:
            results["checks"].append({
                "check": f"forbidden phrase: '{phrase}'",
                "status": "pass",
            })
            results["passed"] += 1

    # Check require_evidence claims
    for evidence_term in require_evidence:
        if evidence_term.lower() in text.lower():
            # Check if any product fact supports this
            found_evidence = False
            for fact_key, fact_data in facts.items():
                source = fact_data.get("source", {})
                if source.get("ref"):
                    found_evidence = True
                    break
            if found_evidence:
                results["checks"].append({
                    "check": f"evidence for '{evidence_term}'",
                    "status": "pass",
                    "detail": f"Product facts have source references",
                })
                results["passed"] += 1
            else:
                results["checks"].append({
                    "check": f"evidence for '{evidence_term}'",
                    "status": "fail",
                    "detail": f"'{evidence_term}' found but no product fact source",
                    "action": "BLOCK_BUILD",
                })
                results["failed"] += 1
                results["build_blocked"] = True

    # Check voice avoid terms
    voice = brand.get("voice", {})
    avoid_terms = voice.get("avoid", [])
    for term in avoid_terms:
        if isinstance(term, str) and term.lower() in text.lower():
            results["checks"].append({
                "check": f"voice avoid: '{term}'",
                "status": "warn",
                "detail": f"Voice guideline term found in content",
            })

    return results


def main():
    import argparse
    parser = argparse.ArgumentParser(description="BrandKit Verifier")
    parser.add_argument("--resolved", default=".build/resolved-task.json", help="Resolved task JSON")
    parser.add_argument("--output-dir", default="output", help="Output directory")
    parser.add_argument("--verify-dir", default=".build/verify", help="Verify report directory")
    args = parser.parse_args()

    resolved_path = Path(args.resolved)
    if not resolved_path.exists():
        print(f"[ERROR] Resolved task not found: {resolved_path}")
        sys.exit(1)

    with open(resolved_path) as f:
        resolved = json.load(f)

    output_dir = Path(args.output_dir)
    verify_dir = Path(args.verify_dir)
    verify_dir.mkdir(parents=True, exist_ok=True)

    visual_report = {"files": [], "total_passed": 0, "total_failed": 0}
    content_report = {"files": [], "total_passed": 0, "total_failed": 0}

    # Verify visual outputs
    html_files = [f for f in output_dir.glob("*.html") if not f.name.startswith("._")]
    for html_file in html_files:
        print(f"[VERIFY] Visual: {html_file.name}")
        result = verify_visual(html_file, resolved)
        visual_report["files"].append(result)
        visual_report["total_passed"] += result.get("passed", 0)
        visual_report["total_failed"] += result.get("failed", 0)
        for check in result.get("checks", []):
            status_icon = "✅" if check["status"] == "pass" else ("⚠️" if check["status"] == "warn" else "❌")
            print(f"  {status_icon} {check['check']}: {check.get('actual', check.get('detail', ''))}")

    # Verify content outputs
    md_files = [f for f in output_dir.glob("*.md") if not f.name.startswith("._")]
    for md_file in md_files:
        print(f"\n[VERIFY] Content: {md_file.name}")
        result = verify_content(md_file, resolved)
        content_report["files"].append(result)
        content_report["total_passed"] += result.get("passed", 0)
        content_report["total_failed"] += result.get("failed", 0)
        for check in result.get("checks", []):
            status_icon = "✅" if check["status"] == "pass" else ("⚠️" if check["status"] == "warn" else "❌")
            print(f"  {status_icon} {check['check']}")

    # Write reports
    visual_report_path = verify_dir / "visual-report.json"
    with open(visual_report_path, "w") as f:
        json.dump(visual_report, f, indent=2, ensure_ascii=False)
    print(f"\n[OK] Visual report → {visual_report_path}")

    content_report_path = verify_dir / "content-report.json"
    with open(content_report_path, "w") as f:
        json.dump(content_report, f, indent=2, ensure_ascii=False)
    print(f"[OK] Content report → {content_report_path}")

    # Check for build-blocked
    build_blocked = any(
        file_result.get("build_blocked", False)
        for file_result in content_report["files"]
    )

    # Summary
    print(f"\n{'='*50}")
    print(f"Visual: {visual_report['total_passed']} passed, {visual_report['total_failed']} failed")
    print(f"Content: {content_report['total_passed']} passed, {content_report['total_failed']} failed")
    if build_blocked:
        print(f"[BLOCKED] Unsupported claims detected — build failed")
    print(f"{'='*50}")

    if visual_report["total_failed"] > 0 or content_report["total_failed"] > 0 or build_blocked:
        sys.exit(1)


if __name__ == "__main__":
    main()
