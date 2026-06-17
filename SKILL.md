---
description: >
  BrandKit — Brand-constrained visual & content compiler. 
  Given a brand spec, product facts, and campaign brief, 
  generates platform-optimized visual assets and copy 
  that stay consistent with brand identity.
---

# BrandKit Skill

## When to use

- User asks to **generate product images or copy** for e-commerce (天猫/小红书/抖音/Instagram)
- User wants to **keep brand identity consistent** across visual and content outputs
- User needs to **adapt the same product** for different platforms without rewriting prompts
- User wants **claim-checked, factual copy** with provenance tracking

## Do NOT use when

- User wants general-purpose image generation without brand constraints
- User wants video production, 3D modeling, or complex animation
- User wants full marketing automation or CRM workflows

## Workflow

```
1. IDENTIFY the brand → load brands/{brand}/brand-core.yaml
2. IDENTIFY the product → load brands/{brand}/products/{sku}.yaml
3. IDENTIFY the campaign → create or edit campaigns/{campaign}.yaml
4. RUN: brandkit build campaigns/{campaign}.yaml
5. REVIEW: output/ directory for visual + content + provenance
6. VALIDATE: brandkit validate for channel differentiation report
7. COMPARE: brandkit baseline {campaign} --dry-run for pure-prompt comparison
```

## Quick commands

```bash
# Build full campaign kit
brandkit build campaigns/618-launch.yaml

# Build all campaigns
brandkit build-all

# Generate A/B drafts for a content type
brandkit render ab --content-type product_title --channel tmall

# Validate channel differentiation
brandkit validate

# Run baseline comparison
brandkit baseline campaigns/618-launch.yaml --dry-run

# Clean build artifacts
brandkit clean
```

## Architecture

```
User prompt
  ↓
SKILL.md (this file)
  ↓
brandkit CLI
  ├─ compile.py   → resolved-task.json + message-plan.json
  ├─ render_visual.py → HTML + PNG (foreground/background separated)
  ├─ render_content.py → Markdown + provenance
  └─ verify.py    → L1 assertions + claim checker + build blocking
```

## Spec files

| File | Purpose | Example |
|------|---------|---------|
| `brand-core.yaml` | Brand identity (colors, fonts, logo, voice, claims) | `brands/aether/brand-core.yaml` |
| `visual-spec.yaml` | Visual execution rules (layout, scene policy) | `brands/aether/visual-spec.yaml` |
| `content-spec.yaml` | Content execution rules (message hierarchy, copy rules) | `brands/aether/content-spec.yaml` |
| `products/{sku}.yaml` | Product facts with source references | `brands/aether/products/x1.yaml` |
| `channels/{channel}.yaml` | Platform constraints (visual + content) | `channels/tmall.yaml` |
| `campaigns/{campaign}.yaml` | Campaign task entry | `campaigns/618-launch.yaml` |

## Key principles

1. **Brand Core is the shared constraint** — visual and content both read it
2. **Product facts are the truth** — every claim must trace to a source
3. **Foreground is FIXED** — product image never modified, only background regenerated
4. **Deterministic first, generative second** — layout/brand/sizing are compiled, only content slots call LLM
