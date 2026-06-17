#!/usr/bin/env python3
"""ecom_pack.py — 电商平台商品套图编排器。

读 brand.yaml + 平台规格 → 按平台要求产出全套商品图。

用法:
  python3 scripts/ecom_pack.py brand.yaml --platform taobao --product "wireless earbuds"
  python3 scripts/ecom_pack.py brand.yaml --platforms taobao,douyin --product "..."
  python3 scripts/ecom_pack.py --inspect taobao
  python3 scripts/ecom_pack.py --list-platforms
"""
import argparse, json, os, re, subprocess, sys, time
from pathlib import Path

BASE = Path(__file__).parent.parent.resolve()
ECOM_DIR = BASE / "ecom_platforms"
GEN_SCRIPT = BASE / "scripts" / "generate_image.py"

def die(m): print(f"ERROR: {m}", file=sys.stderr); raise SystemExit(1)

# ── Platform specs ──

def _load_registry():
    reg = json.loads((ECOM_DIR / "_registry.json").read_text())
    return reg.get("platforms", []), reg.get("default_platform", "taobao")

def list_platforms():
    pids, _ = _load_registry()
    return sorted(pids)

def get_spec(pid):
    pids, _ = _load_registry()
    if pid not in pids:
        avail = ", ".join(pids)
        die(f"Unknown ecom platform '{pid}'. Available: {avail}")
    return json.loads((ECOM_DIR / f"{pid}.json").read_text())

def _safe_filename(img, spec):
    """Generate a safe filename from image spec entry."""
    safe = re.sub(r'[^a-z0-9_\u4e00-\u9fff-]', '', img["label"].replace(' （', '-').replace('）', '')[:30])
    return f"{img['seq']:02d}_{safe}_{img['template']}.png"

# ── Inspect ──

def show_spec(pid):
    s = get_spec(pid)
    print(f"\n=== {s['name']} ({s['id']}) ===")
    print(f"  Description: {s['description']}")
    print(f"  Default size: {s['default_size']}")
    print(f"  Format: {s['format']}  ≤{s['max_size_kb']}KB")
    print(f"  Image set ({len(s['image_set'])} images):")
    print(f"  {'#':<3} {'Type':<12} {'Label':<20} {'Template':<22} {'Size':<12} {'Req':<5}")
    print(f"  {'-'*74}")
    for img in s["image_set"]:
        req = "✓" if img["required"] else "✗"
        print(f"  {img['seq']:<3} {img['type']:<12} {img['label']:<20} "
              f"{img['template']:<22} {img['size']:<12} {req:<5}")
    print()

# ── Generate ──

def gen_one(spec, img, brand_yaml, product, model_platform, env, output_dir, dry_run):
    """Generate one image from the platform spec."""
    seq = img["seq"]
    label = img["label"]
    template = img["template"]
    variant = img.get("variant", "")
    size = img.get("size", spec["default_size"])

    # Build filename
    safe_label = re.sub(r"[^a-z0-9\u4e00-\u9fff_-]", "", label.replace(" ", "-").replace("（", "").replace("）", ""))[:30]
    fname = f"{seq:02d}_{safe_label}_{template}.png"
    out_path = output_dir / fname

    cmd = [
        sys.executable, str(GEN_SCRIPT), str(brand_yaml),
        "--product", product,
        "--template", template,
        "--size", size,
        "--output", str(out_path),
    ]
    if variant:
        cmd += ["--variant", variant]
    if model_platform:
        cmd += ["--platform", model_platform]
    if env:
        cmd += ["--env", env]
    if dry_run:
        cmd += ["--dry-run"]

    print(f"\n  [{seq}/{len(spec['image_set'])}] {label}")
    print(f"       template={template}  size={size}{f'  variant={variant}' if variant else ''}")
    print(f"       → {out_path.name}")

    if dry_run:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        # Show the prompt header only
        for line in result.stdout.splitlines():
            if line.startswith("  Prompt:") or line.startswith("PROMPT"):
                print(f"       {line}")
        if result.returncode != 0:
            print(f"       ⚠️  dry-run failed: {result.stderr.strip()[:200]}")
    else:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        if result.returncode != 0:
            print(f"       ❌ FAILED: {result.stderr.strip()[:300]}")
            return False
        # Show summary
        for line in result.stdout.splitlines():
            if line.startswith("  Image:") or line.startswith("  Prompt:") or line.startswith("  API") or line.startswith("  Metadata"):
                print(f"       {line}")
    return True

# ── Main ──

def main():
    allp = list_platforms()
    p = argparse.ArgumentParser(description="电商平台商品套图编排 — brand_vision_ecom")
    p.add_argument("brand_yaml", nargs="?", help="brand.yaml 文件路径")
    p.add_argument("--platform", "-f", default="", help=f"目标电商平台 ({', '.join(allp)})")
    p.add_argument("--platforms", "-F", default="", help="批量平台，逗号分隔")
    p.add_argument("--product", "-p", default="product", help="产品描述")
    p.add_argument("--model-platform", "-m", default="", help="图片生成模型平台（透传给 generate_image.py）")
    p.add_argument("--output-dir", "-o", default="", help="输出目录（默认 outputs/{platform}/）")
    p.add_argument("--env", "-e", default="", help=".env 文件路径")
    p.add_argument("--inspect", "-i", default="", help=f"查看平台规格 ({', '.join(allp)})")
    p.add_argument("--list-platforms", action="store_true", help="列出可用电商平台")
    p.add_argument("--dry-run", "-n", action="store_true", help="只打印不生成")
    a = p.parse_args()

    if a.list_platforms:
        print(f"\nAvailable e-commerce platforms ({len(allp)}):")
        for pid in allp:
            s = json.loads((ECOM_DIR / f"{pid}.json").read_text())
            cnt = len(s["image_set"])
            req = sum(1 for i in s["image_set"] if i["required"])
            print(f"  {pid:<12} — {s['name']:<8}  {cnt}张 ({req}张必需)  {s['default_size']}  ≤{s['max_size_kb']}KB")
            print(f"                {s['description']}")
        return

    if a.inspect:
        show_spec(a.inspect)
        return

    if not a.brand_yaml:
        p.print_usage()
        print("ERROR: brand_yaml required (use --list-platforms or --inspect <platform>)")
        raise SystemExit(1)

    brand_yaml = Path(a.brand_yaml)
    if not brand_yaml.is_file():
        die(f"Not found: {brand_yaml}")

    # Resolve target platforms
    targets = []
    if a.platforms:
        targets = [pid.strip() for pid in a.platforms.split(",") if pid.strip()]
    elif a.platform:
        targets = [a.platform]
    else:
        _, default = _load_registry()
        targets = [default]

    # Validate
    allp_set = set(allp)
    for pid in targets:
        if pid not in allp_set:
            die(f"Unknown platform '{pid}'")

    # Run
    ts = time.strftime("%Y%m%d-%H%M%S")
    for pid in targets:
        spec = get_spec(pid)
        # Output dir
        if a.output_dir:
            out_base = Path(a.output_dir)
        else:
            out_base = BASE / "outputs" / pid
        out_dir = out_base / ts
        out_dir.mkdir(parents=True, exist_ok=True)

        print(f"\n{'='*60}")
        print(f"📦 {spec['name']} ({spec['id']}) — {len(spec['image_set'])}张")
        print(f"   输出目录: {out_dir}")
        print(f"   产品: {a.product[:60]}")
        print(f"{'='*60}")

        success = True
        for img in spec["image_set"]:
            ok = gen_one(spec, img, brand_yaml, a.product, a.model_platform, a.env, out_dir, a.dry_run)
            if not ok:
                success = False
                print(f"       ⚠️ 跳过后续生成")

        if not a.dry_run:
            # Write summary
            summary = {
                "platform": pid,
                "brand_yaml": str(brand_yaml),
                "product": a.product,
                "model_platform": a.model_platform or "default",
                "ts": ts,
                "output_dir": str(out_dir),
                "images": [
                                    {"seq": img["seq"], "label": img["label"],
                                     "template": img["template"], "size": img.get("size", spec["default_size"]),
                                     "file": _safe_filename(img, spec)}
                                    for img in spec["image_set"]
                                ]
            }
            (out_dir / "_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2))
            print(f"\n  ✅ 完成: {out_dir}")
            print(f"  📋 清单: {out_dir / '_summary.json'}")

if __name__ == "__main__":
    main()