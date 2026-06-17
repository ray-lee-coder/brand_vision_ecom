#!/usr/bin/env python3
"""brand_vision_ecom: brand.yaml -> Style Lock -> template -> API -> image."""
import argparse, base64, json, os, re, sys, time, urllib.error, urllib.request
from pathlib import Path

DEFAULT_SIZE = "2048x2048"
BASE = Path(__file__).parent.parent.resolve()
TEMPLATES = BASE / "templates"
VAR_RE = re.compile(r"\{(\w+)\}")

def die(m): print(f"ERROR: {m}", file=sys.stderr); raise SystemExit(1)
def hexc(v):
    if not isinstance(v, str) or not re.match(r"^#[0-9a-fA-F]{6}$", v.strip()): die(f"Need #RRGGBB: {v}")
    return v.strip()
def tmpls(): return sorted(f.stem for f in TEMPLATES.glob("*.json"))

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

# ── Compile ──
def lock(b):
    c, t = b["colors"], b["typography"]
    desc = (" id:"+b["description"].strip()[:80]) if b.get("description") else ""
    img = b.get("imagery",{})
    r = img.get("product_frame_ratio", 0.35)
    g = 100 - int(r*100)
    return (f"brand{desc}|{c['primary']}/{c['accent']}/{c['canvas']}/{c['text']}"
            f"|{b['tone']},{img.get('primary_lighting','studio_soft')}"
            f"|{t['display']}/{t['body']}|{img.get('default_angle','3/4')} {int(r*100)}%fr,{g}%ws|no drift")

# ── Template ──
def load_tmpl(tid):
    v = tmpls()
    if tid not in v: die(f"Unknown template '{tid}'. Options: {', '.join(v)}")
    return json.loads((TEMPLATES / f"{tid}.json").read_text())

def build(b, tmpl, prod, var=""):
    lock_s = lock(b)
    t = tmpl["prompt_template"]
    vs = tmpl.get("variants",{})
    if var and var not in vs: die(f"Template '{tmpl['id']}' has no variant '{var}'. Options: {', '.join(vs.keys()) or 'none'}")
    ov = vs[var].get("overrides",{}) if var else {}
    bg, lt, comp = [ov.get(k,tmpl["defaults"][k]) for k in ("background","lighting","composition")]
    body = t.get("prompt","") or json.dumps(t, ensure_ascii=False)
    ctx = {"product_description":prod,"background":bg,"lighting":lt,"composition":comp,"variant":var,
           "name":b["name"],"tone":b.get("tone","neutral")}
    miss = [p for p in VAR_RE.findall(body) if p not in ctx]
    if miss: die(f"Template '{tmpl['id']}': unknown vars: {miss}")
    for k,v in ctx.items(): body = body.replace("{"+k+"}",str(v))
    left = VAR_RE.findall(body)
    if left: die(f"Template '{tmpl['id']}': unresolved: {left}")
    r = b.get("imagery",{}).get("product_frame_ratio",0.35); g = 100-int(r*100)
    texty = {"infographic","poster-banner","magazine-editorial","packaging"}
    font = f" {b['typography']['display']}/{b['typography']['body']}" if tmpl["id"] in texty else ""
    desc = (" "+b.get("description","")[:80]) if b.get("description") else ""
    head = f"brand{desc}|{b['colors']['primary']}/{b['colors']['canvas']}/{b['colors']['text']}|{b['tone']} tone{font}"
    prohib = tmpl.get("prohibitions", "No watermarks, fake logos, extra text. Top-center reserved.")
    return f"{head}\n\n{body}\n\n留白至少 {g}%。\n{prohib}", {"variant":var} if var else {}

# ── API ──
class API:
    @staticmethod
    def call(prompt, size, out):
        base = (os.environ.get("IMG_BASE_URL") or os.environ.get("OPENAI_BASE_URL") or "").rstrip("/")
        mod = os.environ.get("IMG_MODEL") or os.environ.get("OPENAI_IMAGE_MODEL") or "gpt-image-2"
        key = os.environ.get("IMG_API_KEY") or os.environ.get("OPENAI_API_KEY") or ""
        if not base: die("Set IMG_BASE_URL in .env")
        if not key: die("Set IMG_API_KEY in .env")
        m = re.match(r"^(\d+)x(\d+)$", size)
        if m:
            w,h = int(m.group(1)),int(m.group(2))
            if w<256 or h>256 or w>4096 or h>4096: die(f"Invalid size: {size}")
        elif not re.match(r"^\d+:\d+$", size): die(f"Invalid size: {size}")
        req = urllib.request.Request(f"{base}/images/generations",
            data=json.dumps({"model":mod,"prompt":prompt,"n":1,"size":size}).encode(),
            headers={"Authorization":f"Bearer {key}","Content-Type":"application/json"})
        print(f"  API {mod} ({size}) ...", end=" ", flush=True)
        try:
            raw = urllib.request.urlopen(req, timeout=180).read()
            item = json.loads(raw.decode())["data"][0]
        except Exception as e:
            die(f"API call failed: {e}")
        saved = False
        if isinstance(item.get("url"),str) and item["url"].startswith("http"):
            print("download ...", end=" ", flush=True)
            try:
                ir = urllib.request.urlopen(item["url"], timeout=60)
                d = ir.read()
                if len(d)<100: die(f"File too small ({len(d)}B)")
                Path(out).write_bytes(d); saved = True
            except Exception as e: die(f"Download: {e}")
        if not saved and isinstance(item.get("b64_json"),str) and len(item["b64_json"])>100:
            print("decode ...", end=" ", flush=True)
            try: Path(out).write_bytes(base64.b64decode(item["b64_json"])); saved = True
            except Exception as e: die(f"Base64: {e}")
        if not saved: die(f"No url/b64_json: {json.dumps(item)[:200]}")
        print(f"done ({Path(out).stat().st_size//1024} KB)")

# ── Main ──
def main():
    ts = time.strftime("%Y%m%d-%H%M%S")
    allt = tmpls()
    p = argparse.ArgumentParser(description="brand_vision_ecom")
    p.add_argument("brand_yaml"); p.add_argument("--product","-p",default="product")
    p.add_argument("--template","-t",default="hero-image",help=f"({', '.join(allt)})")
    p.add_argument("--variant","-v",default=""); p.add_argument("--size","-s",default=DEFAULT_SIZE)
    p.add_argument("--output","-o",default=""); p.add_argument("--env","-e",default="")
    p.add_argument("--dry-run",action="store_true")
    a = p.parse_args()
    load_env(a.env)
    print(f"\nConfig: {a.brand_yaml}")
    b = load(a.brand_yaml); print(f"  Brand: {b['name']}")
    tm = load_tmpl(a.template); print(f"  Template: {tm['name']}")
    pr, meta = build(b,tm,a.product,a.variant); print(f"  Prompt: {len(pr)} chars")
    if a.dry_run:
        print(f"\n{'='*60}\nPROMPT\n{'='*60}\n{pr}"); print(f"\nMETADATA: {json.dumps(meta)}"); return
    sb = re.sub(r"[^a-z0-9-]","",b["name"].lower().replace(" ","-"))[:30]
    vt = f"-{a.variant}" if a.variant else ""
    base = f"{sb}-{a.template}{vt}-{ts}"
    if a.output:
        o = Path(a.output)
        if o.suffix in (".png",".jpg",".jpeg",".webp"):
            o.parent.mkdir(parents=True,exist_ok=True); op = o
        else: o.mkdir(parents=True,exist_ok=True); op = o / f"{base}.png"
    else:
        o = Path.cwd()/"outputs"; o.mkdir(parents=True,exist_ok=True); op = o / f"{base}.png"
    API.call(pr, a.size, str(op)); print(f"  Image: {op}")
    mf = {"brand":b["name"],"template":a.template,"variant":a.variant or "","model":os.environ.get("IMG_MODEL",""),"size":a.size,"prompt":pr,"ts":ts}
    mp = op.with_suffix(".json"); mp.write_text(json.dumps(mf,ensure_ascii=False,indent=2))
    print(f"  Metadata: {mp}")

if __name__ == "__main__": main()