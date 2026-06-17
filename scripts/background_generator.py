#!/usr/bin/env python3
"""
BrandKit Background Generator — 背景生成槽
对称于 Content Pipeline 的 Copy Generator。
仅 scene-spec 标记 `regenerate_background: true` 的场景调用。

输出: .build/backgrounds/{scene}-{variant}.png + metadata
"""

import json
import os
import sys
import hashlib
import subprocess
import tempfile
from pathlib import Path


def generate_background(scene_name, brand_colors, product_name, scene_desc="",
                        provider="sensenova", output_dir=None):
    """
    Generate a background image for a scene.
    Returns dict with background info.
    """
    if output_dir is None:
        output_dir = Path(".build") / "backgrounds"
    else:
        output_dir = Path(output_dir) / "backgrounds"
    output_dir.mkdir(parents=True, exist_ok=True)

    # Build scene description prompt
    primary_color = brand_colors.get("primary", "#111827")
    accent_color = brand_colors.get("accent", "#8B7355")

    if not scene_desc:
        scene_prompts = {
            "hero": f"Minimal product studio background. Soft gradient from {primary_color} to {accent_color}. Clean, premium, professional.",
            "lifestyle": f"Urban lifestyle scene, warm ambient lighting, premium audio product use context. Color palette: {primary_color}, {accent_color}. Modern city atmosphere.",
            "cover": f"Editorial cover background. Warm tones with {accent_color} accents. Minimal, sophisticated, premium feel.",
            "detail": f"Macro photography backdrop. Dark smooth surface with soft reflections. Technical, precise atmosphere.",
        }
        scene_desc = scene_prompts.get(scene_name, scene_prompts["hero"])

    # For M2, generate a gradient/pattern SVG as background (works without image API)
    # In production, this would call the image generation API
    bg_type = "generated_svg"

    # Create gradient SVG
    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="100%" height="100%">
  <defs>
    <linearGradient id="bg-grad" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" style="stop-color:{primary_color};stop-opacity:0.08" />
      <stop offset="50%" style="stop-color:{accent_color};stop-opacity:0.04" />
      <stop offset="100%" style="stop-color:{primary_color};stop-opacity:0.12" />
    </linearGradient>
    <radialGradient id="bg-glow" cx="50%" cy="40%" r="50%">
      <stop offset="0%" style="stop-color:{accent_color};stop-opacity:0.15" />
      <stop offset="100%" style="stop-color:{primary_color};stop-opacity:0" />
    </radialGradient>
  </defs>
  <rect width="100%" height="100%" fill="url(#bg-grad)" />
  <rect width="100%" height="100%" fill="url(#bg-glow)" />
</svg>'''

    # Hash the scene description for version tracking
    scene_hash = hashlib.md5(scene_desc.encode()).hexdigest()[:8]

    # Save background metadata
    bg_info = {
        "scene": scene_name,
        "type": bg_type,
        "description": scene_desc,
        "hash": scene_hash,
        "content": svg,
        "generated_at": None,  # Set when actually generated via API
        "product_fixed": True,  # Product foreground is ALWAYS fixed
    }

    return bg_info


def inject_background(html, bg_info):
    """Inject background into HTML template."""
    if not bg_info:
        # Fallback: solid brand background
        return html.replace("{background_style}", "background: var(--brand-background);") \
                   .replace("{background_content}", "")

    bg_type = bg_info.get("type", "solid")

    if bg_type == "generated_svg":
        # Inject SVG inline
        svg_content = bg_info.get("content", "")
        # Escape for HTML injection
        style = "background: var(--brand-background);"
        content = svg_content
        html = html.replace("{background_style}", style)
        html = html.replace("{background_content}", content)
    elif bg_type == "image_file":
        # Inject image file
        style = "background: var(--brand-background);"
        content = f'<img src="file://{bg_info.get("file_path", "")}" alt="background">'
        html = html.replace("{background_style}", style)
        html = html.replace("{background_content}", content)
    else:
        # Solid color fallback
        html = html.replace("{background_style}", "background: var(--brand-background);")
        html = html.replace("{background_content}", "")

    return html


def main():
    import argparse
    parser = argparse.ArgumentParser(description="BrandKit Background Generator")
    parser.add_argument("--resolved", default=".build/resolved-task.json")
    parser.add_argument("--scene", default="hero")
    parser.add_argument("--desc", default="", help="Scene description for generation")
    parser.add_argument("--dry-run", action="store_true", help="Print prompts without API calls")
    args = parser.parse_args()

    with open(args.resolved) as f:
        resolved = json.load(f)

    brand = resolved.get("brand", {})
    colors = brand.get("colors", {})
    product = resolved.get("product", {})
    product_name = product.get("name", "Product")

    bg = generate_background(args.scene, colors, product_name, args.desc)
    print(f"[OK] Background generated: {args.scene} (type: {bg['type']}, hash: {bg['hash']})")
    print(f"     Product foreground: FIXED (never modified)")
    print(json.dumps(bg, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
