#!/usr/bin/env python3
"""
BrandKit Background Generator — v0.3.0
对称于 Content Pipeline 的 Copy Generator。

支持两种模式:
1. U1-Fast API: 真实图像生成 (默认, 需要 SENSENOVA_API_KEY)
2. SVG placeholder: 离线占位 (--placeholder 标志)

仅 scene-spec 标记 `regenerate_background: true` 的场景调用。
输出: .build/backgrounds/{scene}-{hash}.png + metadata
"""

import json
import os
import hashlib
import time
import requests
from pathlib import Path


class ProviderError(RuntimeError):
    """Raised when an external provider returns an error or malformed response."""
    def __init__(self, provider: str, code: str, detail: str):
        self.provider = provider
        self.code = code
        self.detail = detail
        super().__init__(f"[{provider}] {code}: {detail}")


# ── SenseNova U1-Fast Configuration ──
U1_FAST_URL = "https://token.sensenova.cn/v1/images/generations"
U1_FAST_MODEL = "sensenova-u1-fast"
U1_FAST_SIZE = "2048x2048"
U1_FAST_MAX_CHARS = 3800  # Leave buffer for style lock


def call_u1_fast(prompt: str, api_key: str) -> bytes:
    """Call SenseNova U1-Fast image generation API. Returns PNG bytes."""
    # Truncate prompt if needed
    if len(prompt) > U1_FAST_MAX_CHARS:
        prompt = prompt[:U1_FAST_MAX_CHARS]

    resp = requests.post(
        U1_FAST_URL,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        json={
            "model": U1_FAST_MODEL,
            "prompt": prompt,
            "size": U1_FAST_SIZE,
            "n": 1,
            "response_format": "b64_json",
        },
        timeout=120,
    )
    resp.raise_for_status()
    data = resp.json()

    # U1-Fast returns b64_json
    b64 = data.get("data", [{}])[0].get("b64_json", "")
    if not b64:
        raise RuntimeError("U1-Fast returned no image data")

    import base64
    return base64.b64decode(b64)


def build_background_prompt(scene_name: str, brand_colors: dict, product_name: str,
                           scene_desc: str = "") -> str:
    """Build prompt for background image generation."""
    primary = brand_colors.get("primary", "#111827")
    accent = brand_colors.get("accent", "#8B7355")
    background = brand_colors.get("background", "#F7F4EF")

    brand_style = (
        f"Brand: premium audio, urban professionals. "
        f"Colors: primary {primary}, accent {accent}, background {background}. "
        f"Style: minimal, precise, calm. "
        f"No text, no logo, no watermarks. "
        f"Empty scene for product photography compositing."
    )

    if not scene_desc:
        scene_prompts = {
            "lifestyle": (
                "Urban lifestyle background for premium audio product photography. "
                "Warm ambient lighting, modern city apartment interior, "
                "soft natural light through window, wooden desk surface. "
                "Mood: calm, sophisticated, premium. "
            ),
            "packshot": (
                "Studio product photography background. "
                "Smooth dark surface with soft reflections. "
                "Clean, minimal, technical atmosphere. "
                "Rim lighting from behind, soft fill from front. "
            ),
            "hero": (
                "Clean white studio background for product photography. "
                "Soft even lighting, no shadows, no textures. "
                "Pure minimal commercial photography backdrop."
            ),
            "cover": (
                "Editorial cover background. "
                "Warm tones, minimal composition. "
                "Premium magazine style, sophisticated mood."
            ),
        }
        scene_desc = scene_prompts.get(scene_name, scene_prompts["hero"])

    return f"{scene_desc} {brand_style}"


def generate_background(scene_name, brand_colors, product_name, scene_desc="",
                        output_dir=None, use_placeholder=False):
    """
    Generate a background image for a scene.

    Returns dict with background info.
    Primary mode: U1-Fast API (real image generation).
    Fallback: SVG placeholder (use_placeholder=True or API unavailable).
    """
    if output_dir is None:
        output_dir = Path(".build") / "backgrounds"
    else:
        output_dir = Path(output_dir) / "backgrounds"
    output_dir.mkdir(parents=True, exist_ok=True)

    prompt = build_background_prompt(scene_name, brand_colors, product_name, scene_desc)

    bg_type = "generated_u1fast"
    file_path = None
    content = ""
    scene_hash = hashlib.md5(prompt.encode()).hexdigest()[:8]

    api_key = os.environ.get("SENSENOVA_API_KEY") or os.environ.get("CUSTOM_API_KEY")

    if not use_placeholder:
        # Online mode: API is required
        if not api_key:
            raise ProviderError(
                provider="sensenova",
                code="NO_CREDENTIALS",
                detail="SENSENOVA_API_KEY or CUSTOM_API_KEY not set. Use --placeholder for offline SVG mode."
            )
        try:
            print(f"  [BG] Calling U1-Fast for '{scene_name}'...")
            png_bytes = call_u1_fast(prompt, api_key)
            file_path = output_dir / f"{scene_name}-{scene_hash}.png"
            with open(file_path, "wb") as f:
                f.write(png_bytes)
            print(f"  [BG] U1-Fast OK → {file_path} ({len(png_bytes)} bytes)")
            bg_type = "u1_fast"
        except Exception as e:
            raise ProviderError(
                provider="sensenova",
                code="API_FAILURE",
                detail=f"U1-Fast image generation failed: {e}"
            )

    if bg_type != "u1_fast":
        # SVG placeholder fallback
        primary = brand_colors.get("primary", "#111827")
        accent = brand_colors.get("accent", "#8B7355")
        content = f'''<svg xmlns="http://www.w3.org/2000/svg" width="100%" height="100%">
  <defs>
    <linearGradient id="bg-grad" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" style="stop-color:{primary};stop-opacity:0.08" />
      <stop offset="50%" style="stop-color:{accent};stop-opacity:0.04" />
      <stop offset="100%" style="stop-color:{primary};stop-opacity:0.12" />
    </linearGradient>
    <radialGradient id="bg-glow" cx="50%" cy="40%" r="50%">
      <stop offset="0%" style="stop-color:{accent};stop-opacity:0.15" />
      <stop offset="100%" style="stop-color:{primary};stop-opacity:0" />
    </radialGradient>
  </defs>
  <rect width="100%" height="100%" fill="url(#bg-grad)" />
  <rect width="100%" height="100%" fill="url(#bg-glow)" />
</svg>'''

    bg_info = {
        "scene": scene_name,
        "type": bg_type,
        "description": prompt[:100],
        "hash": scene_hash,
        "content": content,
        "file_path": str(file_path) if file_path else None,
        "generation_mode": "api" if bg_type == "u1_fast" else "placeholder",
        "product_fixed": True,
    }
    return bg_info


def inject_background(html, bg_info):
    """Inject background into HTML template."""
    if not bg_info:
        html = html.replace("{background_style}", "background: var(--brand-background);")
        html = html.replace("{background_content}", "")
        return html

    bg_type = bg_info.get("type", "solid")

    if bg_type == "u1_fast":
        # Real generated image
        file_path = bg_info.get("file_path")
        if file_path and os.path.exists(file_path):
            style = "background: var(--brand-background);"
            content = f'<img src="file://{Path(file_path).resolve()}" alt="generated background" data-gen-mode="u1_fast">'
            html = html.replace("{background_style}", style)
            html = html.replace("{background_content}", content)
        else:
            html = html.replace("{background_style}", "background: var(--brand-background);")
            html = html.replace("{background_content}", "")
    else:
        # SVG placeholder or solid
        style = "background: var(--brand-background);"
        content = bg_info.get("content", "")
        html = html.replace("{background_style}", style)
        html = html.replace("{background_content}", content)

    return html


def main():
    import argparse
    parser = argparse.ArgumentParser(description="BrandKit Background Generator")
    parser.add_argument("--resolved", default=".build/resolved-task.json")
    parser.add_argument("--scene", default="lifestyle")
    parser.add_argument("--desc", default="", help="Scene description")
    parser.add_argument("--placeholder", action="store_true", help="Use SVG placeholder instead of API")
    args = parser.parse_args()

    with open(args.resolved) as f:
        resolved = json.load(f)

    brand = resolved.get("brand", {})
    colors = brand.get("colors", {})
    product = resolved.get("product", {})
    product_name = product.get("name", "Product")

    bg = generate_background(args.scene, colors, product_name, args.desc,
                             use_placeholder=args.placeholder)
    print(json.dumps({k: v for k, v in bg.items() if k != "content"}, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
