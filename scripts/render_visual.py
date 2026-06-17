#!/usr/bin/env python3
"""
BrandKit Visual Renderer (v0.3.0)
M2: 前景/背景分离 + 背景生成槽 + 局部重生成 + 版本追踪
FIXES:
- Reads message-plan.json for headline/subtitle (不再 hardcode)
- Missing product asset → BUILD FAILED (不再静默 placeholder)
- Unknown template → BUILD FAILED (不再静默 fallback)
"""

import json
import os
import sys
import hashlib
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
try:
    from background_generator import generate_background, inject_background
    HAS_BG_GEN = True
except ImportError:
    HAS_BG_GEN = False


def resolve_product_image(product_facts, source_required, allow_placeholder=False):
    """Resolve product image from product facts assets.
    source_required=True + asset missing → BUILD FAILED (unless --allow-placeholder)."""
    assets = product_facts.get("assets", {})
    product_image = assets.get("packshot", "")

    if not product_image:
        if source_required and not allow_placeholder:
            raise RuntimeError(
                "Product asset missing: 'packshot' not defined in product facts. "
                "Set source_required: false in visual-spec or use --allow-placeholder."
            )
        return "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='200' height='200'%3E%3Crect width='200' height='200' fill='%23ddd'/%3E%3Ctext x='100' y='105' text-anchor='middle' fill='%23999' font-size='14'%3EProduct%3C/text%3E%3C/svg%3E", None

    abs_img = str(Path(product_image).resolve()) if not os.path.isabs(product_image) else product_image
    if not os.path.exists(abs_img):
        if source_required and not allow_placeholder:
            raise RuntimeError(
                f"Product asset not found: {abs_img}. "
                "Use --allow-placeholder to generate with placeholder."
            )
        return "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='200' height='200'%3E%3Crect width='200' height='200' fill='%23ddd'/%3E%3Ctext x='100' y='105' text-anchor='middle' fill='%23999' font-size='14'%3EProduct%3C/text%3E%3C/svg%3E", None

    with open(abs_img, "rb") as f:
        img_hash = hashlib.md5(f.read()).hexdigest()[:8]
    return f"file://{abs_img}", img_hash


def get_scene_policy(visual_spec, scene_name):
    """Get scene generation policy from visual-spec."""
    scene_policies = visual_spec.get("scene_policy", {})
    policy = scene_policies.get(scene_name, {})
    return {
        "html_dominant": policy.get("html_dominant", True),
        "regenerate_background": policy.get("regenerate_background", False),
        "preserve_product_asset": policy.get("preserve_product_asset", True),
    }


def render_html(resolved, output_dir, message_plan, allow_placeholder=False, use_placeholder_bg=False):
    """Compose HTML with foreground/background separation.
    Reads headline/subtitle from message-plan.json (not hardcoded)."""
    campaign = resolved.get("campaign", {})
    brand = resolved.get("brand", {})
    visual_spec = resolved.get("visual_spec", {})
    product_facts = resolved.get("product", {})
    output_targets = resolved.get("output_targets", [])

    brand_name = brand.get("name", "Brand")
    colors = brand.get("colors", {})
    typography = brand.get("typography", {})
    latin = typography.get("latin", {})
    heading_font = latin.get("heading", "Inter")
    body_font = latin.get("body", "Inter")

    primary = colors.get("primary", "#000000")
    secondary = colors.get("secondary", "#666666")
    accent = colors.get("accent", "#888888")
    background = colors.get("background", "#FFFFFF")

    # Resolve product image — FAILS if source_required and asset missing
    source_required = visual_spec.get("product_image", {}).get("source_required", True)
    product_image_src, product_img_hash = resolve_product_image(product_facts, source_required, allow_placeholder)

    # Read from message-plan (single source of truth)
    visual_msg = message_plan.get("visual", {})
    headline = visual_msg.get("headline", message_plan.get("primary_benefit", {}).get("statement", "Brand"))
    subtitle = visual_msg.get("subtitle", f"{brand_name} — {headline}")
    primary_benefit = message_plan.get("primary_benefit", {}).get("statement", headline)

    visual_targets = [t for t in output_targets if t["type"] == "visual"]
    rendered = []

    for target in visual_targets:
        scene = target.get("scene", "hero")
        ratio = target.get("ratio", "1:1")
        channel = target.get("channel", "unknown")
        constraints = target.get("constraints", {})
        safe_margin = constraints.get("safe_margin_px", 48)

        dims = {"1:1": (800, 800), "3:4": (600, 800), "16:9": (800, 450)}
        width, height = dims.get(ratio, (800, 800))

        policy = get_scene_policy(visual_spec, scene)

        # Load template — FAIL if missing
        template_path = Path("templates") / f"{scene}.html"
        if not template_path.exists():
            raise RuntimeError(f"Template not found: templates/{scene}.html")

        with open(template_path) as f:
            html = f.read()

        # Generate background (independent of product)
        bg_info = None
        if policy["regenerate_background"] and HAS_BG_GEN:
            bg_prompt = policy.get("background_prompt", "")
            bg_info = generate_background(
                scene, colors, product_facts.get("name", brand_name),
                scene_desc=bg_prompt, use_placeholder=use_placeholder_bg,
            )
        if bg_info:
            html = inject_background(html, bg_info)
        else:
            html = html.replace("{background_style}", "background: var(--brand-background);")
            html = html.replace("{background_content}", "")

        # Fill brand tokens (foreground)
        fills = {
            "{primary}": primary, "{secondary}": secondary,
            "{accent}": accent, "{background}": background,
            "{heading_font}": heading_font, "{body_font}": body_font,
            "{safe_margin}": str(safe_margin),
            "{product_coverage}": "50%", "{logo_position}": "top-left",
            "{brand_name}": brand_name,
            "{headline}": headline, "{subtitle}": subtitle,
            "{width}": str(width), "{height}": str(height),
            "{product_image}": product_image_src,
        }
        for key, val in fills.items():
            html = html.replace(key, val)

        # Write HTML to campaign-specific output dir
        campaign_name = campaign.get("name", "default")
        out_dir = output_dir / campaign_name / "visual"
        out_dir.mkdir(parents=True, exist_ok=True)
        html_filename = f"{channel}-{scene}.html"
        html_path = out_dir / html_filename
        with open(html_path, "w") as f:
            f.write(html)
        print(f"[OK] HTML → {html_path}")

        bg_hash = bg_info.get("hash", "static") if bg_info else "static"
        provenance = {
            "file": html_filename,
            "channel": channel, "scene": scene, "ratio": ratio,
            "headline_source": "message-plan",
            "product_asset": {
                "source": product_image_src,
                "hash": product_img_hash,
                "fixed": True,
            },
            "background": {
                "type": bg_info.get("type", "solid") if bg_info else "solid",
                "hash": bg_hash,
                "regenerable": policy["regenerate_background"],
            },
            "version": f"prod-{product_img_hash or 'none'}-bg-{bg_hash}",
        }

        rendered.append({
            "channel": channel, "scene": scene, "ratio": ratio,
            "html_file": str(html_path), "width": width, "height": height,
            "provenance": provenance,
        })

    return rendered


def render_png(html_path, output_path, width, height):
    """Playwright screenshot → PNG. FAILS on error (no silent skip)."""
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        raise RuntimeError("playwright not installed. Run: pip install playwright && python3 -m playwright install chromium")

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": width, "height": height})
        page.goto(f"file://{html_path.resolve()}", wait_until="networkidle")
        page.screenshot(path=str(output_path), full_page=False)
        browser.close()
    return True


def main():
    import argparse
    parser = argparse.ArgumentParser(description="BrandKit Visual Renderer (v0.3.0)")
    parser.add_argument("--resolved", default=".build/resolved-task.json")
    parser.add_argument("--message-plan", default=".build/message-plan.json")
    parser.add_argument("--output-dir", default="output")
    parser.add_argument("--skip-png", action="store_true")
    parser.add_argument("--allow-placeholder", action="store_true")
    parser.add_argument("--placeholder", action="store_true", help="Use SVG placeholder backgrounds instead of API")
    args = parser.parse_args()

    resolved_path = Path(args.resolved)
    if not resolved_path.exists():
        print(f"[ERROR] Resolved task not found: {resolved_path}")
        sys.exit(1)

    with open(resolved_path) as f:
        resolved = json.load(f)

    # Load message-plan (single source of truth)
    msg_path = Path(args.message_plan)
    message_plan = {}
    if msg_path.exists():
        with open(msg_path) as f:
            message_plan = json.load(f)

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    try:
        rendered = render_html(resolved, output_dir, message_plan, args.allow_placeholder, args.placeholder)
    except RuntimeError as e:
        print(f"[FAIL] {e}")
        sys.exit(1)

    if not args.skip_png:
        for r in rendered:
            html_path = Path(r["html_file"])
            png_name = html_path.stem + ".png"
            png_path = html_path.parent / png_name
            try:
                ok = render_png(html_path, png_path, r["width"], r["height"])
                r["png_rendered"] = ok
            except RuntimeError as e:
                print(f"[FAIL] PNG render: {e}")
                sys.exit(1)

    # Write visual provenance
    provenance_path = output_dir / ".visual-provenance.json"
    with open(provenance_path, "w") as f:
        json.dump({
            "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "principle": "product_foreground_fixed_background_independent",
            "headline_source": "message-plan.json",
            "outputs": [r["provenance"] for r in rendered],
        }, f, indent=2, ensure_ascii=False)
    print(f"[OK] Visual provenance → {provenance_path}")
    print(f"[OK] Visual render: {len(rendered)} output(s) — headline from message-plan")


if __name__ == "__main__":
    main()