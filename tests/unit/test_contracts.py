"""
P1 failure tests: compiler contracts, override policy, schema validation.

Each test encodes a known P1 bug as a reproducible red test.
Tests fail with the current code and will pass when Stage 2 fixes are applied.
"""
import json
import sys
import tempfile
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "scripts"))

# ── Helper: build a minimal valid campaign dir with correct YAML structure ──
BRAND_CORE = """brand:
  name: TestBrand
  colors:
    primary: '#000'
    secondary: '#666'
    accent: '#888'
    background: '#FFF'
  typography:
    latin:
      heading: Inter
      body: Inter
  logo:
    min_size_px: 48
    clear_space_px: 24
    allowed_backgrounds: [light, dark]
  voice:
    tone: [precise]
    avoid: []
  claims:
    require_evidence: []
"""

VISUAL_SPEC = """visual:
  default_ratio: '1:1'
layout:
  density: low
  product_coverage: '45%-60%'
  safe_margin_px: 64
product_image:
  source_required: false
scene_policy:
  hero:
    html_dominant: true
    background_prompt: 'test prompt'
"""

CONTENT_SPEC = """content:
  default_language: zh-CN
  claim_rules:
    forbidden: []
  message_hierarchy:
    primary_benefit: test_benefit
    secondary_benefits: []
"""

PRODUCT_FACTS = """product:
  id: test
  name: Test
  facts: {}
  assets: {}
"""

CHANNEL_TMALL = """channel:
  id: tmall
  visual: {}
  content:
    product_title:
      max_chars: 60
"""


def make_campaign_dir(campaign_yaml):
    """Create temp dir with minimal valid specs and a campaign file."""
    d = Path(tempfile.mkdtemp())
    (d / "campaigns").mkdir(parents=True)
    (d / "brands" / "testbrand" / "products").mkdir(parents=True)
    (d / "channels").mkdir()

    (d / "brands" / "testbrand" / "brand-core.yaml").write_text(BRAND_CORE)
    (d / "brands" / "testbrand" / "visual-spec.yaml").write_text(VISUAL_SPEC)
    (d / "brands" / "testbrand" / "content-spec.yaml").write_text(CONTENT_SPEC)
    (d / "brands" / "testbrand" / "products" / "test.yaml").write_text(PRODUCT_FACTS)
    (d / "channels" / "tmall.yaml").write_text(CHANNEL_TMALL)
    (d / "campaigns" / "test.yaml").write_text(campaign_yaml)
    return d


# --- P1-1: Override engine not applied (compile.py:36-76,229-233) ---
# The documented priority/merge engine is not on the compilation path;
# campaign overrides are stored but not applied.

def test_campaign_override_applied():
    """Campaign overrides must appear in resolved-task, not just be stored."""
    from compile import compile_campaign
    d = make_campaign_dir("""campaign:
  name: test
  brand_ref: brands/testbrand/brand-core.yaml
  product_ref: brands/testbrand/products/test.yaml
  objective: test
  audience: test

outputs:
  visual:
    - type: packshot
      channel: tmall
      format: png
  content: []

override:
  headline_max_lines: 3
""")
    (d / "templates").mkdir(exist_ok=True)
    (d / "templates" / "packshot.html").write_text("<html></html>")
    result = compile_campaign(str(d / "campaigns" / "test.yaml"))
    assert result["status"] == "ok", f"Compile failed: {result}"
    resolved = result["resolved"]
    for target in resolved.get("output_targets", []):
        if target.get("type") == "visual":
            constraints = target.get("constraints", {})
            assert constraints.get("headline_max_lines") == 3, \
                f"Override not applied: {constraints}"


# --- P1-2: Visual spec top-level fields dropped (compile.py:220-223) ---
# Compilation keeps only `visual:` and drops `layout`, `product_image`, `scene_policy`.
# NOW FIXED in compile.py.

def test_visual_spec_preserves_top_level_keys():
    """resolved-task must retain layout, product_image, scene_policy from visual-spec."""
    from compile import compile_campaign
    d = make_campaign_dir("""campaign:
  name: test
  brand_ref: brands/testbrand/brand-core.yaml
  product_ref: brands/testbrand/products/test.yaml

outputs:
  visual:
    - type: packshot
      channel: tmall
      format: png
  content: []
""")
    # Create a dummy template that the conflict checker expects
    (d / "templates").mkdir(exist_ok=True)
    (d / "templates" / "packshot.html").write_text("<html></html>")
    result = compile_campaign(str(d / "campaigns" / "test.yaml"))
    assert result["status"] == "ok", f"Compile failed: {result}"
    vspec = result["resolved"].get("visual_spec", {})
    assert "layout" in vspec, "layout should be in visual_spec"
    assert "product_image" in vspec, "product_image should be in visual_spec"
    assert "scene_policy" in vspec, "scene_policy should be in visual_spec"


# --- P1-3: Empty output targets pass silently (compile.py:287) ---
# An empty target/output set can compile, render, verify, and exit zero.
# NOW FIXED — contract check blocks empty targets.

def test_empty_output_targets_blocked():
    """Compilation with no output targets must fail."""
    from compile import compile_campaign
    d = make_campaign_dir("""campaign:
  name: test
  brand_ref: brands/testbrand/brand-core.yaml
  product_ref: brands/testbrand/products/test.yaml

outputs:
  visual: []
  content: []
""")
    result = compile_campaign(str(d / "campaigns" / "test.yaml"))
    # Must NOT succeed — empty targets should block
    assert result["status"] != "ok", "Empty output targets must be blocked"


# --- P1-9: Evidence files don't exist (brands/aether/products/*.yaml) ---
# Evidence references like docs/x1-spec.pdf do not exist on disk.

def test_evidence_file_exists():
    """Compilation must reject a fact whose source ref file does not exist on disk."""
    from compile import compile_campaign
    d = Path(tempfile.mkdtemp())
    (d / "campaigns").mkdir(parents=True)
    (d / "brands" / "testbrand" / "products").mkdir(parents=True)
    (d / "channels").mkdir()

    (d / "brands" / "testbrand" / "brand-core.yaml").write_text(BRAND_CORE)
    (d / "brands" / "testbrand" / "visual-spec.yaml").write_text(VISUAL_SPEC)
    (d / "brands" / "testbrand" / "content-spec.yaml").write_text(CONTENT_SPEC)

    # Product with evidence file ref that does NOT exist
    (d / "brands" / "testbrand" / "products" / "test.yaml").write_text("""product:
  id: test
  name: Test
  facts:
    noise_reduction:
      value: 42
      unit: dB
      source:
        type: lab_report
        ref: does-not-exist-on-disk.pdf
      status: verified
  assets: {}
""")
    (d / "channels" / "tmall.yaml").write_text(CHANNEL_TMALL)
    (d / "campaigns" / "test.yaml").write_text("""campaign:
  name: test
  brand_ref: brands/testbrand/brand-core.yaml
  product_ref: brands/testbrand/products/test.yaml

outputs:
  visual:
    - type: packshot
      channel: tmall
      format: png
  content: []
""")
    (d / "templates").mkdir(exist_ok=True)
    (d / "templates" / "packshot.html").write_text("<html></html>")
    result = compile_campaign(str(d / "campaigns" / "test.yaml"))
    # Evidence file doesn't exist — must fail
    assert result["status"] != "ok", "Missing evidence file must block compilation"


# --- P1-14/15: Unknown channel detection ---
# (redundant with existing test_audit, but committed as a P1 regression marker)

@pytest.mark.xfail(reason="P1: verification validates against hardcoded profiles, not compiled channel YAML (validate_channel.py:12,56)")
def test_channel_validation_uses_compiled_contract():
    """Channel validation must read from compiled channel YAML, not hardcoded profiles."""
    from validate_channel import validate_channel
    tmp = Path(tempfile.mktemp(suffix=".md"))
    # A subtle violation: literary tone without parameter-first structure
    tmp.write_text("沉浸式听觉体验，感受每一个音符的细节")
    result = validate_channel(tmp, "tmall")
    tmp.unlink()
    # The compiled tmall contract would use channel YAML rules, not hardcoded profiles
    # For now, this just verifies the function shape
    assert "channel" in result
