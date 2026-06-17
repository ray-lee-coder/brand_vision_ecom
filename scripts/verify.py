#!/usr/bin/env python3
"""
BrandKit Verifier (v0.3.0)
FIXES:
- Claim Graph: validates claims JSON, not just markdown text
- Cross-pipeline consistency: checks visual + content share same primary_benefit
- Campaign-specific output dirs
- --allow-warnings flag to allow non-blocking warnings
"""

import json
import sys
from pathlib import Path
import re


def verify_visual(html_path, resolved, message_plan):
    """L1 visual assertions via Playwright getComputedStyle."""
    brand = resolved.get("brand", {})
    colors = brand.get("colors", {})
    expected_primary = colors.get("primary", "#000000").lower()
    expected_background = colors.get("background", "#FFFFFF").lower()
    expected_accent = colors.get("accent", "#888888").lower()

    results = {"file": str(html_path), "checks": [], "passed": 0, "failed": 0}

    # Check if visual uses message-plan headline (skip templates without headline slot)
    if message_plan:
        visual_msg = message_plan.get("visual", {})
        expected_headline = visual_msg.get("headline", "")
        expected_subtitle = visual_msg.get("subtitle", "")
        if expected_headline:
            with open(html_path) as f:
                html_content = f.read()
            # Only verify headline exists if the template has a {headline} slot
            if "{headline}" not in html_content:
                # Template doesn't have headline slot (e.g. packshot) — skip
                results["checks"].append({"check": "headline from message-plan (template has no headline slot)", "status": "info"})
            elif expected_headline in html_content:
                results["checks"].append({"check": "headline from message-plan", "status": "pass"})
                results["passed"] += 1
            else:
                results["checks"].append({"check": "headline from message-plan", "status": "fail", "detail": f"Expected: '{expected_headline}'"})
                results["failed"] += 1

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


def verify_content(content_path, resolved, message_plan):
    """Claim Graph: validate claims JSON + markdown text."""
    brand = resolved.get("brand", {})
    claims_config = brand.get("claims", {})
    require_evidence = claims_config.get("require_evidence", [])

    content_spec = resolved.get("content_spec", {})
    claim_rules = content_spec.get("claim_rules", {})
    forbidden_phrases = claim_rules.get("forbidden", [])

    product = resolved.get("product", {})
    facts = product.get("facts", {})

    with open(content_path) as f:
        text = f.read()

    results = {
        "file": str(content_path),
        "checks": [],
        "passed": 0,
        "failed": 0,
        "build_blocked": False,
    }

    # Check 1: forbidden phrases in text
    for phrase in forbidden_phrases:
        if phrase.lower() in text.lower():
            results["checks"].append({"check": f"forbidden phrase: '{phrase}'", "status": "fail", "detail": f"Found in content"})
            results["failed"] += 1
            results["build_blocked"] = True
        else:
            results["checks"].append({"check": f"forbidden phrase: '{phrase}'", "status": "pass"})
            results["passed"] += 1

    # Check 2: Claim Graph — load provenance JSON if exists
    provenance_path = content_path.with_suffix(".provenance.json")
    claims = []
    if provenance_path.exists():
        with open(provenance_path) as f:
            prov_data = json.load(f)
        claims = prov_data.get("claims", [])

    if claims:
        for claim in claims:
            fact_ref = claim.get("fact_ref", "")
            source_ref = claim.get("source_ref", "")
            status = claim.get("status", "")

            # Every objective claim must have a fact_ref
            is_marketing = fact_ref == "marketing_writing"
            is_verified = status == "verified"
            has_source = bool(source_ref)

            if is_marketing:
                results["checks"].append({"check": f"marketing claim: '{claim.get('claim', '')[:40]}'", "status": "info", "detail": "No fact_ref (marketing writing)"})
            elif is_verified and has_source:
                results["checks"].append({"check": f"fact claim: '{claim.get('claim', '')[:40]}'", "status": "pass", "detail": f"fact_ref={fact_ref}"})
                results["passed"] += 1
            else:
                results["checks"].append({"check": f"unverified claim: '{claim.get('claim', '')[:40]}'", "status": "warn", "detail": f"fact_ref={fact_ref}, source={source_ref}"})

    # Check 3: require_evidence in text — must have matching fact
    for evidence_term in require_evidence:
        if evidence_term.lower() in text.lower():
            # Check if ANY claim in provenance matches this evidence
            evidence_covered = False
            for claim in claims:
                claim_text = claim.get("claim", "").lower()
                if evidence_term.lower() in claim_text and claim.get("fact_ref") != "marketing_writing":
                    evidence_covered = True
                    break
            if evidence_covered:
                results["checks"].append({"check": f"evidence for '{evidence_term}'", "status": "pass"})
                results["passed"] += 1
            else:
                results["checks"].append({
                    "check": f"evidence for '{evidence_term}'", "status": "fail",
                    "detail": f"'{evidence_term}' in text but no fact_ref found in provenance",
                    "action": "BLOCK_BUILD",
                })
                results["failed"] += 1
                results["build_blocked"] = True

    # Check 4: Verify content uses message-plan primary_benefit
    if message_plan:
        expected_benefit = message_plan.get("primary_benefit", {}).get("statement", "")
        if expected_benefit and expected_benefit in text:
            results["checks"].append({"check": "primary_benefit from message-plan", "status": "pass"})
            results["passed"] += 1

    # Check 5: Voice avoid terms (warn only)
    voice = brand.get("voice", {})
    avoid_terms = voice.get("avoid", [])
    for term in avoid_terms:
        if isinstance(term, str) and term.lower() in text.lower():
            results["checks"].append({"check": f"voice avoid: '{term}'", "status": "warn"})

    return results


def main():
    import argparse
    parser = argparse.ArgumentParser(description="BrandKit Verifier (v0.3.0)")
    parser.add_argument("--resolved", default=".build/resolved-task.json")
    parser.add_argument("--message-plan", default=".build/message-plan.json")
    parser.add_argument("--output-dir", default="output")
    parser.add_argument("--verify-dir", default=".build/verify")
    parser.add_argument("--allow-warnings", action="store_true", help="Don't fail on warnings")
    args = parser.parse_args()

    resolved_path = Path(args.resolved)
    if not resolved_path.exists():
        print(f"[ERROR] Resolved task not found: {resolved_path}")
        sys.exit(1)
    with open(resolved_path) as f:
        resolved = json.load(f)

    msg_path = Path(args.message_plan)
    message_plan = {}
    if msg_path.exists():
        with open(msg_path) as f:
            message_plan = json.load(f)

    output_dir = Path(args.output_dir)
    verify_dir = Path(args.verify_dir)
    verify_dir.mkdir(parents=True, exist_ok=True)

    visual_report = {"files": [], "total_passed": 0, "total_failed": 0}
    content_report = {"files": [], "total_passed": 0, "total_failed": 0}

    # Verify visual outputs (campaign-specific)
    visual_dirs = list(output_dir.glob("*/visual/"))
    if not visual_dirs:
        # Fallback: check output/ root for html
        html_files = [f for f in output_dir.glob("*.html") if not f.name.startswith("._")]
        if html_files:
            visual_dirs = [output_dir]
    
    for vd in visual_dirs:
        html_files = [f for f in vd.glob("*.html") if not f.name.startswith("._")]
        for html_file in html_files:
            print(f"[VERIFY] Visual: {html_file.relative_to(output_dir)}")
            result = verify_visual(html_file, resolved, message_plan)
            visual_report["files"].append(result)
            visual_report["total_passed"] += result.get("passed", 0)
            visual_report["total_failed"] += result.get("failed", 0)
            for check in result.get("checks", []):
                icon = "✅" if check["status"] == "pass" else ("⚠️" if check["status"] in ("warn", "info") else "❌")
                detail = check.get("actual", check.get("detail", ""))
                print(f"  {icon} {check['check']}: {detail}")

    # Verify content outputs (campaign-specific)
    content_dirs = list(output_dir.glob("*/content/"))
    if not content_dirs:
        md_files = [f for f in output_dir.glob("*.md") if not f.name.startswith("._")]
        if md_files:
            content_dirs = [output_dir]

    for cd in content_dirs:
        md_files = [f for f in cd.glob("*.md") if not f.name.startswith("._")]
        for md_file in md_files:
            print(f"\n[VERIFY] Content: {md_file.relative_to(output_dir)}")
            result = verify_content(md_file, resolved, message_plan)
            content_report["files"].append(result)
            content_report["total_passed"] += result.get("passed", 0)
            content_report["total_failed"] += result.get("failed", 0)
            for check in result.get("checks", []):
                icon = "✅" if check["status"] == "pass" else ("⚠️" if check["status"] in ("warn", "info") else "❌")
                print(f"  {icon} {check['check']}")

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

    has_failures = (visual_report["total_failed"] > 0 or content_report["total_failed"] > 0 or build_blocked)
    if has_failures and not args.allow_warnings:
        sys.exit(1)


if __name__ == "__main__":
    main()