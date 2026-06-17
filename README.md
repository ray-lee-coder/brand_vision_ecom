# brand_vision_ecom

Write your brand's visual rules into a YAML file. Every AI-generated product image uses the same colors, fonts, lighting and composition — no more rewriting prompts per image.

This is a **brand-aware Prompt Compiler**: it reads structured brand data, compiles a visual Style Lock, matches a scene template, and calls an image generation API. Currently optimized for GPT-Image-2; see compatibility table below.

---

> ⚠️ **Prompts designed for GPT-Image-2**
> 
> The Style Lock structure, scene templates, hex color locking, whitespace declarations, and negative constraints are all tuned for GPT-Image-2's behavior. Results with other models may vary significantly. Known issues with non-GPT models include:
> - Style Lock text being rendered as visible text in the image
> - Color hex values not being followed precisely
> - Numeric constraints (product ratio, whitespace) being ignored
> - Prohibited items still appearing in outputs
> 
> If you're using a different backend, generate a single test image first (`--output /tmp/test.png`) before scaling up.

---

## Quick start

```bash
# 1. Clone
git clone https://github.com/ray-lee-coder/brand_vision_ecom.git
cd brand_vision_ecom

# 2. Install (just pyyaml)
pip install pyyaml

# 3. Configure API (copy .env.example to .env, fill in your key)
#    IMG_BASE_URL=https://token.sensenova.cn/v1
#    IMG_MODEL=sensenova-u1-fast
#    IMG_API_KEY=sk-...

# 4. Generate
python3 scripts/generate_image.py examples/aether/brand.yaml \
  --product "wireless earbuds, dark navy body, gold accent ring" \
  --template hero-image
```

Output: a 2048×2048 PNG file.

---

## How it works

```
brand.yaml → compile Style Lock → match template → build prompt → call API → image
```

1. **brand.yaml** — brand colors, fonts, photography preferences in one file
2. **Style Lock** — a fixed "visual contract" (hex palette, font names, lighting, product ratio, whitespace) that gets prepended to every prompt
3. **Scene templates** — 15 built-in templates (hero, lifestyle, flat lay, detail, model, social, UGC, before-after, packaging, infographic, multi-product, multi-angle grid, editorial, seasonal, poster)
4. **Prompt** — Style Lock + template + product description assembled into a single prompt
5. **API call** — sent to any OpenAI-compatible image generation endpoint

Multi-image sets (e.g., a PDP) all share the same Style Lock. One lock, consistent output.

---

## Why not just write prompts directly?

| Situation | Direct prompting | With brand_vision_ecom |
|-----------|-----------------|----------------------|
| Color | "Deep blue" → navy or cobalt? | `#1E3A8A` — same hex every time |
| Typography | "Modern sans-serif" → LLM picks one | Named font injected into prompt |
| Consistency | Describe per image → drifts | One Style Lock → all images share it |
| Switch brands | Rewrite everything from scratch | Swap the brand.yaml file |
| Multi-image sets | Write each prompt individually | Change `--template`, Style Lock reuses |

---

## brand.yaml reference

```yaml
brand:
  name: "Your Brand"
  description: "One-line brand description (embedded in prompts)"
  tone: "cool"                      # warm / cool / neutral

  colors:
    primary: "#D4AF37"              # Brand primary color (required)
    accent: "#D4AF37"               # Accent color (optional, defaults to primary)
    canvas: "#FFFFFF"               # Background color (required)
    text: "#F7F5F0"                 # Text color (required)
    surface: "#1B2A4A"             # Surface color (optional)
    border: "#9DB3CD"              # Border color (optional)

  typography:
    display: "PP Mori"              # Display/headline font
    body: "Inter"                   # Body text font

  imagery:                           # Photography preferences (optional, has defaults)
    primary_lighting: "editorial_cinematic"
    default_angle: "three_quarter"
    product_frame_ratio: 0.40
    background: "pure_white"
    retouching: "moderate"
    min_views: 5
    required_angles:
      - front
      - three_quarter_left
      - three_quarter_right
      - side_left
      - detail
```

Two reference brand files in `examples/`: `aether/brand.yaml` (audio-tech, gold + navy) and `nike/brand.yaml` (sport, monochrome).

---

## Scene templates (15)

| Template ID | Use case | Variants |
|-------------|----------|----------|
| `hero-image` | White background product shot, search result hero | luxury / minimal / tech |
| `lifestyle-scene` | Lifestyle/usage scene | indoor / outdoor / studio |
| `flat-lay` | Overhead flat lay, accessories | minimal / styled / bundle |
| `detail-macro` | Macro close-up, material texture | material / stitching / hardware |
| `model-showcase` | Model wearing product, fashion | fullbody / halfbody / detail / editorial |
| `social-media` | Xiaohongshu, Instagram, TikTok | xiaohongshu / instagram / tiktok |
| `ugc-style` | User-generated content, unboxing, reviews | unboxing / usingselfie / review |
| `before-after` | Before/after comparison | skincare / cleaner / lighting |
| `packaging` | Package/box/gift presentation | closed / opened / gift |
| `infographic` | A+ content, feature grid, comparison table | featuregrid / comparison / specs |
| `multi-product` | Bundle, product family, series display | row / cluster / tiered |
| `multi-angle-grid` | Multi-angle grid, color variants | 2x2 / 1x4 / colors |
| `magazine-editorial` | Editorial, brand campaign | highfashion / stillife / cover |
| `seasonal-campaign` | Seasonal/holiday campaign | spring / summer / autumn / winter |
| `poster-banner` | Promotional poster, launch | sale / editorial / launch |

```bash
# Switch templates freely
python3 scripts/generate_image.py examples/aether/brand.yaml \
  --product "..." --template lifestyle-scene

# Use --variant for a style variant
python3 scripts/generate_image.py examples/aether/brand.yaml \
  --product "..." --template poster-banner --variant editorial
```

---

## Model compatibility

| Model | Style Lock fidelity | Tested |
|-------|-------------------|--------|
| GPT-Image-2 (apimart.ai) | ✅ Best — hex values, ratio, whitespace, negatives all work | ✅ Yes |
| SenseNova U1-Fast | ⚠️ Moderate — colors mostly follow, may render text in image | ✅ Yes |
| Other OpenAI-compatible | ❓ Unknown — test one image first before batch | ❌ No |

**Tip:** Always run `python3 scripts/generate_image.py ... --output /tmp/test.png` first to verify output quality before batch generation.

---

## Project structure

```
├── scripts/generate_image.py      Core script (~260 lines)
├── templates/                     15 scene templates (JSON)
├── schemas/brand.schema.json      Brand data specification
├── examples/
│   ├── aether/brand.yaml          Audio-tech brand example (gold + navy)
│   └── nike/brand.yaml            Sport brand example (monochrome)
├── .env.example                   API config template
├── README.md                      This file
└── README.zh.md                   Chinese version
```

Zero external Git dependencies. Clone, `pip install pyyaml`, configure `.env`, and you're ready to generate.
