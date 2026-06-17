# scripts/platforms.py — Platform registry, prompt rendering, payload building, response parsing.
# brand_vision_ecom: one brand.yaml → many platforms.
#
# Adding a new platform:
#   1. Create platforms/<id>.json
#   2. Add a renderer function below in RENDERERS
#   3. Add a builder function below in BUILDERS (if payload differs from openai_standard)
#   4. Add a parser below in PARSERS (if response differs from standard url/b64_json)
#   5. Register the platform in _registry.json

from __future__ import annotations

import json, os, re, sys
from pathlib import Path

BASE = Path(__file__).parent.parent.resolve()
PLATFORM_DIR = BASE / "platforms"
RE_HEX = re.compile(r"#[0-9a-fA-F]{6}")

# ── Load ──

def _load_platforms():
    """Lazily load all platform profiles from platforms/*.json."""
    reg = json.loads((PLATFORM_DIR / "_registry.json").read_text())
    pl = {}
    for pid in reg.get("platforms", []):
        fp = PLATFORM_DIR / f"{pid}.json"
        if fp.is_file():
            pl[pid] = json.loads(fp.read_text())
    return pl, reg.get("default_platform", "gpt-image-2")

_PLATFORMS, _DEFAULT_PLATFORM = None, None

def platforms():
    global _PLATFORMS, _DEFAULT_PLATFORM
    if _PLATFORMS is None:
        _PLATFORMS, _DEFAULT_PLATFORM = _load_platforms()
    return _PLATFORMS, _DEFAULT_PLATFORM

def get(pid: str):
    """Get a platform profile by id."""
    ps, _ = platforms()
    if pid not in ps:
        avail = ", ".join(sorted(ps.keys()))
        raise SystemExit(f"Unknown platform '{pid}'. Available: {avail}")
    return ps[pid]

def list_ids():
    ps, _ = platforms()
    return sorted(ps.keys())

# ── Hex → semantic color names ──

HEX_TO_WORD = {
    "#D4AF37": "warm gold",
    "#C9A84C": "golden",
    "#B8860B": "dark goldenrod",
    "#FFD700": "gold",
    "#FFFFFF": "pure white",
    "#F7F5F0": "warm off-white",
    "#1B2A4A": "dark navy",
    "#111111": "pure black",
    "#1E3A8A": "navy blue",
    "#9DB3CD": "slate gray blue",
    "#F5F5F5": "light gray",
    "#E5E5E5": "silver gray",
    "#000000": "pure black",
    "#333333": "dark gray",
    "#666666": "medium gray",
    "#999999": "gray",
    "#CCCCCC": "light silver",
    "#F0F0F0": "off-white",
    "#FAFAFA": "near white",
}

def hex_to_word(h: str) -> str:
    h_u = h.strip().upper()
    if h_u in HEX_TO_WORD:
        return HEX_TO_WORD[h_u]
    # generic fallback: describe the color
    r, g, b = int(h_u[1:3], 16), int(h_u[3:5], 16), int(h_u[5:7], 16)
    if r > 200 and g > 200 and b > 200: return "very light"
    if r < 50 and g < 50 and b < 50: return "very dark"
    brightness = (r * 299 + g * 587 + b * 114) / 1000
    tone = "dark" if brightness < 128 else "light"
    return f"{tone} {h_u}"

# ── Prompt Rendering ──

def _render_prepend_and_body(brand, style_lock, brand_desc, body, prohibitions, whitespace_pct):
    """GPT-Image-2 style: Style Lock as plain text prefix + body as structured description."""
    font_part = f" {brand['typography']['display']}/{brand['typography']['body']}" if brand.get("typography") else ""
    head = f"brand{brand_desc}|{brand['colors']['primary']}/{brand['colors']['canvas']}/{brand['colors']['text']}|{brand['tone']} tone{font_part}"
    return f"{head}\n\n{body}\n\n留白至少 {whitespace_pct}%。\n{prohibitions}"

def _render_bracket_style_context(brand, style_lock, brand_desc, body, prohibitions, whitespace_pct):
    """SenseNova U1-Fast: wrap Style Lock in brackets [style: ...] to reduce visible text risk."""
    c = brand["colors"]
    t = brand.get("typography", {})
    img = brand.get("imagery", {})
    style_line = (
        f"[style: {brand['name']} | primary={c['primary']} accent={c.get('accent','')} "
        f"canvas={c['canvas']} text={c['text']} | {brand['tone']} tone | "
        f"display={t.get('display','')} body={t.get('body','')} | "
        f"lighting={img.get('primary_lighting','studio_soft')} angle={img.get('default_angle','3/4')} "
        f"frame_ratio={img.get('product_frame_ratio',0.35)}]"
    )
    return f"{style_line}\n\n{body}\n\n留白至少 {whitespace_pct}%。\n{prohibitions}"

def _render_style_prefix_semantic(brand, style_lock, brand_desc, body, prohibitions, whitespace_pct):
    """DALL-E 3: convert hex values to semantic descriptions, short style prefix, no raw hex codes."""
    c = brand["colors"]
    t = brand.get("typography", {})
    img = brand.get("imagery", {})

    # Convert hex to words
    primary_w = hex_to_word(c["primary"])
    canvas_w = hex_to_word(c["canvas"])
    text_w = hex_to_word(c["text"])
    accent_w = hex_to_word(c.get("accent", c["primary"]))

    style_prefix = (
        f"Brand: {brand['name']}. Color scheme: {primary_w} primary, "
        f"{canvas_w} background, {text_w} text, {accent_w} accent. "
        f"Tone: {brand['tone']}. "
        f"Fonts: {t.get('display','')} + {t.get('body','')}. "
        f"Lighting: {img.get('primary_lighting','studio_soft')}. "
        f"Photography style: commercial product photography."
    )
    return f"{style_prefix}\n\n{body}\n\nWhitespace: at least {whitespace_pct}%.\n{prohibitions}"

RENDERERS = {
    "prepend_and_body": _render_prepend_and_body,
    "bracket_style_context": _render_bracket_style_context,
    "style_prefix_semantic": _render_style_prefix_semantic,
}

def render_prompt(platform_id: str, brand: dict, body: str, prohibitions: str, whitespace_pct: int):
    """Render the full prompt for a given platform using its Style Lock strategy."""
    pf = get(platform_id)
    method = pf.get("prompt_rendering", {}).get("style_lock_method", "prepend_and_body")
    renderer = RENDERERS.get(method)
    if not renderer:
        raise SystemExit(f"Platform '{platform_id}': unknown style_lock_method '{method}'")

    # Build style_lock string (used by some renderers)
    c, t = brand["colors"], brand["typography"]
    img = brand.get("imagery", {})
    r = img.get("product_frame_ratio", 0.35)
    g = 100 - int(r * 100)
    desc = ""
    if brand.get("description"):
        desc = " id:" + brand["description"].strip()[:80]
    style_lock = (
        f"brand{desc}|{c['primary']}/{c.get('accent',c['primary'])}/{c['canvas']}/{c['text']}"
        f"|{brand['tone']},{img.get('primary_lighting','studio_soft')}"
        f"|{t['display']}/{t['body']}|{img.get('default_angle','3/4')} {int(r*100)}%fr,{g}%ws|no drift"
    )
    brand_desc = (brand.get("description","")[:80]) if brand.get("description") else ""
    if brand_desc:
        brand_desc = " " + brand_desc

    return renderer(brand, style_lock, brand_desc, body, prohibitions, g)

# ── Payload Building ──

def openai_payload(model: str, prompt: str, size: str, n: int = 1):
    """Standard OpenAI-compatible image generation payload."""
    return {"model": model, "prompt": prompt, "n": n, "size": size}

BUILDERS = {
    "openai_standard": openai_payload,
}

def build_payload(platform_id: str, prompt: str, size: str):
    """Build the API payload for the given platform."""
    pf = get(platform_id)
    payload_type = pf.get("payload_format", "openai_standard")
    builder = BUILDERS.get(payload_type)
    if not builder:
        raise SystemExit(f"Platform '{platform_id}': unknown payload_format '{payload_type}'")
    model = os.environ.get(pf.get("model_env","")) or pf.get("default_model","")
    return builder(model, prompt, size)

# ── Response Parsing ──

def openai_parse(data: dict) -> tuple[str | None, str | None]:
    """Extract (url, b64_json) from standard OpenAI response."""
    item = data.get("data", [{}])[0] if isinstance(data.get("data"), list) else data
    return item.get("url"), item.get("b64_json")

PARSERS = {
    "openai_standard": openai_parse,
}

def parse_response(platform_id: str, raw: dict) -> tuple[str | None, str | None]:
    """Parse API response into (url, b64_json) tuple."""
    pf = get(platform_id)
    payload_type = pf.get("payload_format", "openai_standard")
    parser = PARSERS.get(payload_type)
    if not parser:
        raise SystemExit(f"Platform '{platform_id}': no parser for payload_format '{payload_type}'")
    return parser(raw)

# ── Size validation ──

def validate_size(platform_id: str, size: str) -> str:
    """Validate (and coerce) size for a platform."""
    pf = get(platform_id)
    sz = pf.get("size", {})
    allowed = sz.get("allowed", [])
    fmt = sz.get("format", "wxh")

    if fmt == "wxh":
        m = re.match(r"^(\d+)x(\d+)$", size)
        if not m:
            raise SystemExit(f"Platform '{platform_id}' requires WxH size format (e.g. 1024x1024), got '{size}'")
        w, h = int(m.group(1)), int(m.group(2))
        if w < 256 or w > 4096 or h < 256 or h > 4096:
            raise SystemExit(f"Size {size} out of bounds for platform '{platform_id}' (256-4096)")
        if allowed and size not in allowed:
            raise SystemExit(f"Platform '{platform_id}' does not support size '{size}'. Allowed: {', '.join(allowed)}")
    elif fmt == "ratio":
        m = re.match(r"^\d+:\d+$", size)
        if not m:
            raise SystemExit(f"Platform '{platform_id}' requires ratio format (e.g. 1:1), got '{size}'")
    return size

def default_size(platform_id: str) -> str:
    """Get the default size for a platform."""
    pf = get(platform_id)
    return pf.get("size", {}).get("default", "2048x2048")

# ── Rate limit awareness ──

def rate_limit(platform_id: str) -> dict | None:
    """Get rate limit info for a platform."""
    pf = get(platform_id)
    return pf.get("rate_limit")
