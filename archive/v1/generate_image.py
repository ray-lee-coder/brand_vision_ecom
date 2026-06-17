#!/usr/bin/env python3
"""brand_vision_ecom: brand.yaml -> Style Lock (per platform) -> template -> API -> image."""
import argparse, base64, json, os, re, sys, time, urllib.error, urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.resolve()))
import platforms  # platform profiles + rendering + dispatch

DEFAULT_SIZE = "2048x2048"
BASE = Path(__file__).parent.parent.resolve()
TEMPLATES = BASE / "templates"
VAR_RE = re.compile(r"\{(\w+)\}")

def die(m): print(f"ERROR: {m}", file=sys.stderr); raise SystemExit(1)
def hexc(v):
    if not isinstance(v, str) or not re.match(r"^#[0-9a-fA-F]{6}$", v.strip()): die(f"Need #RRGGBB: {v}")
    return v.strip()
def tmpls(): return sorted(f.stem for f in TEMPLATES.glob("*.json"))

def plist(): return platforms.list_ids()

# ── .env ──
def load_env(env=""):
    for f in ([Path(env)] if env else []) + [BASE / ".env"]:
        if not f.is_file(): continue
        for ln in f.read_text().splitlines():
            ln = ln.strip()
            if not ln or ln.startswith("#") or "=" not in ln: continue
            k, v = ln.split("=", 1)
            k, v = k.strip(), v.strip().strip("'\"")
            if k not in os.environ: os.environ[k] = v
        if env: break

# ── Brand ──
def load(path):
    import yaml
    p = Path(path)
    if not p.is_file(): die(f"Not found: {path}")
    b = yaml.safe_load(p.read_text()).get("brand")
    if not b: die("brand.yaml: missing 'brand'")
    if not isinstance(b.get("name"), str) or not b["name"].strip(): die("name required")
    c = b.get("colors")
    if not isinstance(c, dict): die("colors required")
    for k in ("primary","canvas","text"):
        if k not in c: die(f"colors.{k} required"); hexc(c[k])
    t = b.get("typography")
    if not isinstance(t, dict): die("typography required")
    for k in ("display","body"):
        if k not in t: die(f"typography.{k} required")
    if b.get("tone") and b["tone"] not in ("warm","cool","neutral"): die("tone must be warm/cool/neutral")
    b.setdefault("description",""); b.setdefault("tone","neutral"); b.setdefault("imagery",{})
    b["colors"].setdefault("accent", c["primary"])
    return b

# ── Template ──
def load_tmpl(tid):
    v = tmpls()
    if tid not in v: die(f"Unknown template '{tid}'. Options: {', '.join(v)}")
    return json.loads((TEMPLATES / f"{tid}.json").read_text())

def resolve_body(tmpl, prod, var="", **brand_info):
    """Resolve template variables and return (body_text, prohibitions, metadata)."""
    t = tmpl["prompt_template"]
    vs = tmpl.get("variants",{})
    if var and var not in vs: die(f"Template '{tmpl['id']}' has no variant '{var}'. Options: {', '.join(vs.keys()) or 'none'}")
    ov = vs[var].get("overrides",{}) if var else {}
    bg, lt, comp = [ov.get(k,tmpl["defaults"][k]) for k in ("background","lighting","composition")]
    body = t.get("prompt","") or json.dumps(t, ensure_ascii=False)
    ctx = {"product_description":prod,"background":bg,"lighting":lt,"composition":comp,"variant":var,
           "name":brand_info.get("name",""),"tone":brand_info.get("tone","neutral")}
    miss = [p for p in VAR_RE.findall(body) if p not in ctx]
    if miss: die(f"Template '{tmpl['id']}': unknown vars: {miss}")
    for k,v in ctx.items(): body = body.replace("{"+k+"}",str(v))
    left = VAR_RE.findall(body)
    if left: die(f"Template '{tmpl['id']}': unresolved: {left}")
    prohib = tmpl.get("prohibitions", "No watermarks, fake logos, extra text. Top-center reserved.")
    return body, prohib, {"variant":var} if var else {}

# ── Build prompt (platform-aware) ──
def build_prompt(platform_id, brand, body, prohibitions, whitespace_pct):
    """Render the full prompt for the given platform."""
    return platforms.render_prompt(platform_id, brand, body, prohibitions, whitespace_pct)

# ── API ──
class API:
    @staticmethod
    def call(prompt, size, out, platform_id):
        pf = platforms.get(platform_id)
        base = (os.environ.get(pf.get("base_url_env","")) or "").rstrip("/")
        key = os.environ.get(pf.get("auth_env","")) or ""
        base_env = pf.get("base_url_env", "IMG_BASE_URL")
        auth_env = pf.get("auth_env", "IMG_API_KEY")
        if not base: die(f"Set {base_env} in .env (for platform '{platform_id}')")
        if not key: die(f"Set {auth_env} in .env (for platform '{platform_id}')")
        sh = pf.get("endpoint_suffix","/v1/images/generations")

        # Validate size per platform
        size = platforms.validate_size(platform_id, size)

        # Build payload
        payload = platforms.build_payload(platform_id, prompt, size)
        model = payload.get("model", pf.get("default_model",""))

        req = urllib.request.Request(f"{base}{sh}",
            data=json.dumps(payload).encode(),
            headers={"Authorization":f"Bearer {key}","Content-Type":"application/json"})
        print(f"  API {model} ({size}) via {pf['name']} ...", end=" ", flush=True)
        try:
            raw = urllib.request.urlopen(req, timeout=180).read()
            data = json.loads(raw.decode())
        except Exception as e:
            die(f"API call failed: {e}")

        url, b64 = platforms.parse_response(platform_id, data)
        saved = False
        if isinstance(url, str) and url.startswith("http"):
            print("download ...", end=" ", flush=True)
            try:
                ir = urllib.request.urlopen(url, timeout=60)
                d = ir.read()
                if len(d)<100: die(f"File too small ({len(d)}B)")
                Path(out).write_bytes(d); saved = True
            except Exception as e: die(f"Download: {e}")
        if not saved and isinstance(b64, str) and len(b64)>100:
            print("decode ...", end=" ", flush=True)
            try: Path(out).write_bytes(base64.b64decode(b64)); saved = True
            except Exception as e: die(f"Base64: {e}")
        if not saved: die(f"No url/b64_json: {json.dumps(data)[:200]}")
        rl = platforms.rate_limit(platform_id)
        rl_msg = f" (rate: {rl['rpm']} req/min, {rl['rpd']}/day)" if rl else ""
        print(f"done ({Path(out).stat().st_size//1024} KB){rl_msg}")

# ── Main ──
def main():
    ts = time.strftime("%Y%m%d-%H%M%S")
    allt = tmpls()
    allp = plist()
    p = argparse.ArgumentParser(description="brand_vision_ecom — brand-aware prompt compiler for product images")
    p.add_argument("brand_yaml", nargs="?")
    p.add_argument("--product","-p",default="product")
    p.add_argument("--template","-t",default="hero-image",help=f"({', '.join(allt)})")
    p.add_argument("--variant","-v",default="")
    p.add_argument("--platform","-f",default="",help=f"Target platform ({', '.join(allp)}). Default from _registry.json")
    p.add_argument("--list-platforms",action="store_true",help="List available platforms and exit")
    p.add_argument("--size","-s",default=DEFAULT_SIZE)
    p.add_argument("--output","-o",default="")
    p.add_argument("--env","-e",default="")
    p.add_argument("--dry-run",action="store_true")
    a = p.parse_args()

    if a.list_platforms:
        print(f"\nAvailable platforms ({len(allp)}):")
        pid, default = platforms.platforms()
        for pid in allp:
            pf = platforms.get(pid)
            rl = pf.get("rate_limit")
            rl_s = f"  rate: {rl['rpm']}rpm/{rl['rpd']}rpd" if rl else ""
            tag = " [default]" if pid == default else ""
            print(f"  {pid}{tag}  — {pf.get('name','')} {rl_s}")
            print(f"      {pf.get('description','')}")
        return

    if not a.brand_yaml:
        p.print_usage()
        print("ERROR: brand_yaml argument required (use --list-platforms to see platforms)")
        raise SystemExit(1)

    platform_id = a.platform or platforms._DEFAULT_PLATFORM
    if platform_id not in allp:
        die(f"Unknown platform '{platform_id}'. Use --list-platforms to see options.")

    load_env(a.env)
    sz = platforms.default_size(platform_id) if a.size == DEFAULT_SIZE else a.size
    print(f"\nConfig: {a.brand_yaml}")
    b = load(a.brand_yaml); print(f"  Brand: {b['name']}")
    tm = load_tmpl(a.template); print(f"  Template: {tm['name']}")
    print(f"  Platform: {platforms.get(platform_id)['name']} ({platform_id})")

    # Resolve template body (platform-agnostic)
    body, prohib, meta = resolve_body(tm, a.product, a.variant,
                                       name=b.get("name",""), tone=b.get("tone","neutral"))
    # Build prompt per platform
    r = b.get("imagery",{}).get("product_frame_ratio",0.35)
    whitespace_pct = 100 - int(r * 100)
    prompt = build_prompt(platform_id, b, body, prohib, whitespace_pct)
    print(f"  Prompt: {len(prompt)} chars  (Style Lock: {platforms.get(platform_id)['prompt_rendering']['style_lock_method']})")

    if a.dry_run:
        print(f"\n{'='*60}\nPROMPT\n{'='*60}\n{prompt}")
        print(f"\nMETADATA: {json.dumps(meta)}")
        return

    sb = re.sub(r"[^a-z0-9-]","",b["name"].lower().replace(" ","-"))[:30]
    vt = f"-{a.variant}" if a.variant else ""
    base_f = f"{sb}-{a.template}{vt}-{platform_id}-{ts}"
    if a.output:
        o = Path(a.output)
        if o.suffix in (".png",".jpg",".jpeg",".webp"):
            o.parent.mkdir(parents=True,exist_ok=True); op = o
        else: o.mkdir(parents=True,exist_ok=True); op = o / f"{base_f}.png"
    else:
        o = Path.cwd()/"outputs"; o.mkdir(parents=True,exist_ok=True); op = o / f"{base_f}.png"
    API.call(prompt, sz, str(op), platform_id)
    print(f"  Image: {op}")
    mf = {"brand":b["name"],"template":a.template,"variant":a.variant or "","platform":platform_id,
          "model":os.environ.get(platforms.get(platform_id).get("model_env",""),""),"size":sz,"prompt":prompt,"ts":ts}
    mp = op.with_suffix(".json"); mp.write_text(json.dumps(mf,ensure_ascii=False,indent=2))
    print(f"  Metadata: {mp}")

if __name__ == "__main__": main()