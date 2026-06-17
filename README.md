# BrandKit

> **Brand-constrained visual & content compiler for e-commerce.**
> Write brand rules once. Generate platform-optimized visuals and copy that stay consistent.

```bash
git clone https://github.com/ray-lee-coder/brand_vision_ecom.git
cd brand_vision_ecom
pip install pyyaml playwright
python3 -m playwright install chromium
```

## What it does

```
Campaign Task (brand × product × platform)
  │
  ├─ Visual Pipeline → HTML + PNG
  │   ├─ Brand tokens compiled to CSS variables
  │   ├─ Product image FIXED (never modified)
  │   ├─ Background independently generatable
  │   └─ L1 validation (colors, margins, safe areas)
  │
  └─ Content Pipeline → Markdown + Provenance
      ├─ Product facts → message plan
      ├─ Claim checked against brand rules
      ├─ Channel adapted (天猫=conversion, 小红书=experience)
      └─ Provenance: every claim traces to source
```

## Quick start

```bash
# Build a campaign
bash scripts/brandkit build campaigns/618-launch.yaml

# Output in output/
ls output/
# tmall-hero.png  xiaohongshu-cover.png  tmall-product_title.md ...

# Validate channel differentiation
bash scripts/brandkit validate

# Run baseline comparison
bash scripts/brandkit baseline campaigns/618-launch.yaml --dry-run
```

## Spec files

| File | Purpose | Location |
|------|---------|----------|
| `brand-core.yaml` | Brand identity (colors, fonts, logo, voice, claims) | `brands/aether/` |
| `visual-spec.yaml` | Visual rules (layout, scene policy, photography) | `brands/aether/` |
| `content-spec.yaml` | Content rules (message hierarchy, copy rules) | `brands/aether/` |
| `products/{sku}.yaml` | Product facts with source references | `brands/aether/products/` |
| `channels/{channel}.yaml` | Platform constraints (visual + content) | `channels/` |
| `campaigns/{campaign}.yaml` | Campaign task entry | `campaigns/` |

### brand-core.yaml

Long-term stable brand identity. Example:

```yaml
brand:
  name: Aether
  category: audio-tech
colors:
  primary: "#111827"
  accent: "#8B7355"
  background: "#F7F4EF"
typography:
  latin:
    heading: "Neue Haas Grotesk"
    body: "Inter"
voice:
  tone: [restrained, precise, confident]
  avoid: [shouting, fake luxury, internet slang]
claims:
  require_evidence: ["best", "first", "medical grade", "100%"]
```

### product-facts.yaml

Structured product facts with source references:

```yaml
product:
  id: x1-headphones
  name: Aether X1
  facts:
    noise_reduction:
      value: 42
      unit: dB
      source:
        type: lab_report
        ref: docs/x1-noise-test.pdf
      status: verified
```

## Architecture

```
Spec files (brand-core / visual / content / products / channels / campaign)
  │
  ▼
Compiler (compile.py)
  ├─ Spec merge with priority resolution
  ├─ Hard constraint conflict detection
  └─ resolved-task.json + message-plan.json
        │
        ▼
Visual Renderer (render_visual.py)    Content Renderer (render_content.py)
  ├─ HTML Compositor                     ├─ Fact Resolver
  ├─ Background Generator                ├─ Message Planner
  ├─ Product image FIXED                 ├─ Copy Generator (LLM)
  └─ Playwright → PNG                    ├─ Claim Checker
                                         └─ Markdown + Provenance
        │
        ▼
Verifier (verify.py)
  ├─ L1 CSS assertions (colors, margins)
  ├─ Claim checker (forbidden phrases, require_evidence)
  ├─ Build blocking (hard constraint violations)
  └─ Channel diff report (天猫 vs 小红书 structural differences)
```

## CLI

```bash
brandkit init <brand>         # Initialize a new brand directory
brandkit build [campaign]     # Build single campaign kit
brandkit build-all            # Build all campaigns
brandkit render visual        # Render visual outputs
brandkit render content       # Render content outputs
brandkit render ab            # Generate A/B drafts
brandkit verify               # Verify outputs against brand rules
brandkit validate             # Validate channel differentiation
brandkit baseline [campaign]  # Run pure-prompt baseline comparison
brandkit clean                # Clean build artifacts
```

User doesn't need to memorize CLI. Agent (Claude Code / Codex / Cursor) interprets:

> "按 Aether 品牌规范，给 X1 耳机做一套 618 首发物料。先出天猫主图、小红书封面、天猫标题和五点描述。"

## Non-goals

- No Web App, database, or user accounts
- No Figma plugin or design tool integration
- No full video production, 3D rendering, or advanced animation
- No marketing automation or CRM workflows
- No multi-user collaboration or approval flows
- No PPTX / DOCX / MP4 as primary output (experimental only)

## Example output

```
output/aether-618/
├── visual/
│   ├── tmall-hero.png          # Brand-colored product hero (800×800)
│   ├── xiaohongshu-cover.png   # Lifestyle cover for Xiaohongshu (600×800)
│   └── preview.html            # Editable HTML preview
├── content/
│   ├── tmall-product_title.md  # "Aether X1 沉浸降噪 — 618限时特惠"
│   ├── tmall-bullet_points.md  # 5-point description with fact sources
│   ├── xiaohongshu-note.md     # Experience-style note
│   └── xiaohongshu-title.md    # Cover title
├── verify/
│   ├── visual-report.json      # L1 assertion results
│   ├── content-report.json     # Claim checker results
│   └── channel-diff-report.json # Cross-platform structural differences
└── .visual-provenance.json     # Version tracking
```

## Roadmap

| Phase | Focus | Status |
|-------|-------|--------|
| M0-A | Compiler Spine (spec merge + conflict detection) | ✅ |
| M0-B | Campaign Kit (2 visual + 4 content outputs) | ✅ |
| M1 | Content Governance (provenance, claim checking, channel diff) | ✅ |
| M2 | Visual Hybrid (foreground/background separation, local regenerate) | ✅ |
| M3 | Skill Distribution (SKILL.md, README, GitHub sync) | ✅ |

## License

MIT
