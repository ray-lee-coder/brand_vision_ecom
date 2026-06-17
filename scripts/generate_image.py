#!/usr/bin/env python3
"""
brand_vision_ecom — 品牌约束电商生图工具

用法:
  python3 generate_image.py examples/aether/brand.yaml --product "无线耳塞" --template hero-image
  python3 generate_image.py examples/aether/brand.yaml --product "无线耳塞" --template lifestyle-scene --size 1536x2048
  python3 generate_image.py examples/nike/brand.yaml --product "跑鞋" --template multi-angle-grid --output-dir ./outputs

读取 brand.yaml → 编译 Style Lock → 匹配场景模板 → 调用 API → 出图。
"""
from __future__ import annotations

import argparse, base64, json, os, sys, time, urllib.error, urllib.request
from pathlib import Path
from typing import Any

# ── 默认配置 ──────────────────────────────────────────────

DEFAULT_SIZE = "2048x2048"
DEFAULT_RESOLUTION = "2k"
BASE_DIR = Path(__file__).parent.parent.resolve()
TEMPLATES_DIR = BASE_DIR / "templates"
TEMPLATE_LIST = [f.stem for f in sorted(TEMPLATES_DIR.glob("*.json"))]

VALID_SIZES_SYNC = {
    "1024x1024", "2048x2048", "3840x3840",
    "1536x1024", "2048x1360", "3840x2560",
    "1024x1536", "1360x2048", "2560x3840",
    "1536x864", "2048x1152", "3840x2160",
    "864x1536", "1152x2048", "2160x3840",
}

# ── 工具函数 ──────────────────────────────────────────────

def fail(msg: str, code: int = 1) -> None:
    print(f"错误: {msg}", file=sys.stderr)
    raise SystemExit(code)

def hex_color(v: str) -> str:
    """确保值是 #RRGGBB 格式"""
    v = v.strip()
    if not v.startswith("#"):
        fail(f"颜色值必须以 # 开头: {v}")
    if len(v) != 7:
        fail(f"颜色值必须是 #RRGGBB 格式: {v}")
    return v

# ── 第 1 步：读 brand.yaml ────────────────────────────────

def load_brand(path: str) -> dict:
    import yaml  # pip install pyyaml
    if not Path(path).is_file():
        fail(f"品牌配置文件不存在: {path}")
    try:
        with open(path) as f:
            data = yaml.safe_load(f)
    except Exception as e:
        fail(f"解析 brand.yaml 失败: {e}")

    brand = data.get("brand", {})
    if not brand.get("name"):
        fail("brand.yaml 缺少 brand.name")

    colors = brand.get("colors", {})
    for k in ("primary", "canvas", "text"):
        if k not in colors:
            fail(f"brand.yaml 缺少 brand.colors.{k}")
        hex_color(colors[k])

    typo = brand.get("typography", {})
    for k in ("display", "body"):
        if k not in typo:
            fail(f"brand.yaml 缺少 brand.typography.{k}")

    return data

# ── 第 2 步：编译 Style Lock ──────────────────────────────

def compile_style_lock(brand: dict) -> str:
    b = brand["brand"]
    c = b["colors"]
    t = b["typography"]
    desc = b.get("description", "")
    tone = b.get("tone", "neutral")
    img = b.get("imagery", {})

    lighting = img.get("primary_lighting", "studio_soft")
    angle = img.get("default_angle", "three_quarter")
    ratio = img.get("product_frame_ratio", 0.35)

    # 提取品牌调性关键词（取 description 前 10 个词）
    kw = " ".join(desc.split()[:10]) if desc else f"{b['name']} brand"

    pct = int(ratio * 100)
    gap = 100 - pct

    lock = (
        f"fixed palette of {c['primary']} primary, {c.get('accent', c['primary'])} accent, "
        f"{c['canvas']} canvas, {c['text']} text; "
        f"{tone} tone, {lighting} lighting; "
        f"{t['display']} / {t['body']} typography; "
        f"{angle} presentation at {pct}% frame coverage; "
        f"generous {gap}% whitespace; "
        f"no color palette changes, no mixed fonts, no random backgrounds, no inconsistent lighting"
    )
    return lock

# ── 第 3 步：匹配场景模板 ─────────────────────────────────

def load_template(template_id: str) -> dict:
    if template_id not in TEMPLATE_LIST:
        fail(f"场景模板不支持。可用: {', '.join(TEMPLATE_LIST)}")
    path = TEMPLATES_DIR / f"{template_id}.json"
    with open(path) as f:
        return json.load(f)

# ── 第 4 步：构建 Prompt ─────────────────────────────────

def build_prompt(brand: dict, template: dict, product_desc: str, variant: str = "") -> str:
    lock = compile_style_lock(brand)
    prompt_tmpl = template["prompt_template"]

    # 检查变体
    overrides = {}
    if variant and variant in template.get("variants", {}):
        overrides = template["variants"][variant].get("overrides", {})

    bg = overrides.get("background", template["defaults"]["background"])
    lt = overrides.get("lighting", template["defaults"]["lighting"])
    comp = overrides.get("composition", template["defaults"]["composition"])

    body = prompt_tmpl.get("prompt", "") or json.dumps(prompt_tmpl, ensure_ascii=False)
    body = body.replace("{product_description}", product_desc)
    body = body.replace("{background}", bg)
    body = body.replace("{lighting}", lt)
    body = body.replace("{composition}", comp)

    prohibitions = (
        "不要添加：道具、手、水印、假 logo、额外文字、装饰元素、渐变背景。"
        "顶部中央 200×100 区域留空（价格叠加区）。"
    )

    prompt = (
        f"Campaign Style Lock: {lock}.\n\n"
        f"{body}\n\n"
        f"留白至少 {100 - int(brand['brand'].get('imagery', {}).get('product_frame_ratio', 0.35) * 100)}%。\n"
        f"{prohibitions}"
    )
    return prompt

# ── 第 5 步：调 API ──────────────────────────────────────

def load_api_config(env_file: str = "") -> tuple:
    """返回 (base_url, model, api_key)"""
    if env_file:
        for line in open(env_file):
            line = line.strip()
            if line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            k, v = k.strip(), v.strip().strip("'\"")
            if k not in os.environ:
                os.environ[k] = v

    base_url = os.environ.get("IMG_BASE_URL") or os.environ.get("OPENAI_BASE_URL") or ""
    model = os.environ.get("IMG_MODEL") or os.environ.get("OPENAI_IMAGE_MODEL") or "gpt-image-2"
    api_key = os.environ.get("IMG_API_KEY") or os.environ.get("OPENAI_API_KEY") or os.environ.get("API_KEY") or ""

    if not base_url:
        fail("缺少 API 配置。设置 IMG_BASE_URL 环境变量或通过 --env 指定 .env 文件")
    if not api_key:
        fail("缺少 API Key。设置 IMG_API_KEY 环境变量或通过 --env 指定 .env 文件")

    return base_url, model, api_key

def call_api(base_url: str, model: str, api_key: str, prompt: str, size: str, output_path: str) -> str:
    """调用图片生成 API，保存到 output_path，返回文件路径"""
    data = json.dumps({"model": model, "prompt": prompt, "n": 1, "size": size}).encode()

    req = urllib.request.Request(
        f"{base_url.rstrip('/')}/images/generations",
        data=data,
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    )

    print(f"  调用 {model} ({size}) ...", end=" ", flush=True)
    try:
        resp = urllib.request.urlopen(req, timeout=120)
        result = json.loads(resp.read().decode())
        img_url = result["data"][0]["url"]
    except urllib.error.HTTPError as e:
        body = e.read().decode()[:200]
        fail(f"API 错误 (HTTP {e.code}): {body}")

    # 下载图片
    print("下载 ...", end=" ", flush=True)
    import subprocess
    subprocess.run(["curl", "-sL", img_url, "-o", output_path], check=True, capture_output=True)
    size_kb = Path(output_path).stat().st_size / 1024
    print(f"完成 ({size_kb:.0f} KB)")
    return output_path

# ── 主流程 ────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="brand_vision_ecom — 品牌约束电商生图")
    parser.add_argument("brand_yaml", help="品牌配置文件路径（如 examples/aether/brand.yaml）")
    parser.add_argument("--product", "-p", default="产品", help="产品文字描述")
    parser.add_argument("--template", "-t", default="hero-image", help=f"场景模板 ({', '.join(TEMPLATE_LIST)})")
    parser.add_argument("--variant", "-v", default="", help="风格变体（如 luxury, minimal, tech）")
    parser.add_argument("--size", "-s", default=DEFAULT_SIZE, help=f"图片尺寸，默认 {DEFAULT_SIZE}")
    parser.add_argument("--output", "-o", default="", help="输出路径（默认自动生成）")
    parser.add_argument("--env", "-e", default="", help=".env 文件路径")
    args = parser.parse_args()

    print(f"\nbrand_vision_ecom — {args.brand_yaml}")

    # Step 1: 读品牌
    print("[1/5] 加载品牌配置 ...")
    brand_data = load_brand(args.brand_yaml)
    brand = brand_data["brand"]
    print(f"  品牌: {brand['name']}")

    # Step 2: 编译 Style Lock
    print("[2/5] 编译 Campaign Style Lock ...")
    lock = compile_style_lock(brand_data)
    print(f"  {lock[:80]}...")

    # Step 3: 加载模板
    print(f"[3/5] 加载场景模板: {args.template} ...")
    template = load_template(args.template)
    print(f"  模板: {template['name']}")

    # Step 4: 构建 Prompt
    print("[4/5] 构建生成 Prompt ...")
    prompt = build_prompt(brand_data, template, args.product, args.variant)
    print(f"  Prompt 长度: {len(prompt)} 字符")
    print(f"  --- Prompt 前 200 字 ---")
    print(prompt[:200])
    print("  ...")

    # Step 5: 调 API
    print("[5/5] 调用生图 API ...")
    base_url, model, api_key = load_api_config(args.env)

    output_dir = args.output or str(Path.cwd() / "outputs")
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    timestamp = time.strftime("%Y%m%d-%H%M%S")
    output_path = Path(output_dir) / f"{brand['name'].lower().replace(' ','-')}-{args.template}-{timestamp}.png"

    call_api(base_url, model, api_key, prompt, args.size, str(output_path))

    print(f"\n✅ 出图完成: {output_path}")

if __name__ == "__main__":
    main()
