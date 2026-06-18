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


# --- P1-1: Override engine not applied (compile.py:36-76,229-233) ---
# The documented priority/merge engine is not on the compilation path;
# campaign overrides are stored but not applied.

@pytest.mark.xfail(reason="P1: compiled task ignores campaign overrides (compile.py:36-76)")
def test_campaign_override_applied():
    """Campaign overrides must appear in resolved-task, not just be stored."""
    from compile import compile_campaign
    campaign_path = Path(tempfile.mkdtemp())
    (campaign_path / "campaigns").mkdir(parents=True)
    (campaign_path / "brands" / "testbrand" / "products").mkdir(parents=True)
    (campaign_path / "channels").mkdir()

    brand_core = campaign_path / "brands" / "testbrand" / "brand-core.yaml"
    brand_core.write_text("brand:\n  name: TestBrand\n  colors:\n    primary: '#000'\n    secondary: '#666'\n    accent: '#888'\n    background: '#FFF'\n  typography:\n    latin:\n      heading: Inter\n      body: Inter\n  logo:\n    min_size_px: 48\n    clear_space_px: 24\n    allowed_backgrounds: [light, dark]\n  voice:\n    tone: [precise]\n    avoid: []\n  claims:\n    require_evidence: []")

    vs = campaign_path / "brands" / "testbrand" / "visual-spec.yaml"
    vs.write_text("visual:\n  default_ratio: '1:1'\nlayout:\n  density: low\n  product_coverage: '45%-60%'\n  safe_margin_px: 64\nproduct_image:\n  source_required: false\nscene_policy:\n  hero:\n    html_dominant: true\n    background_prompt: 'test'")

    cs = campaign_path / "brands" / "testbrand" / "content-spec.yaml"
    cs.write_text("content:\n  default_language: zh-CN\n  claim_rules:\n    forbidden: []\n  message_hierarchy: {}")

    prod = campaign_path / "brands" / "testbrand" / "products" / "test.yaml"
    prod.write_text("product:\n  id: test\n  name: Test\n  facts: {}\n  assets: {}")

    ch = campaign_path / "channels" / "tmall.yaml"
    ch.write_text("channel:\n  id: tmall\n  visual: {}\n  content:\n    product_title:\n      max_chars: 60")

    camp = campaign_path / "campaigns" / "test.yaml"
    camp.write_text("campaign:\n  brand_ref: brands/testbrand/brand-core.yaml\n  product_ref: brands/testbrand/products/test.yaml\n  outputs:\n    visual: [{type: hero, channel: tmall, format: png}]\n    content: []\n  override:\n    headline_max_lines: 3")

    resolved = compile_campaign(str(camp))
    # The override should be applied to the resolved output targets or constraints
    # Currently the override is stored in campaign.override but never applied
    for target in resolved.get("output_targets", []):
        if target.get("type") == "visual":
            constraints = target.get("constraints", {})
            assert constraints.get("headline_max_lines") == 3, \
                f"Override not applied: {constraints}"


# --- P1-2: Visual spec top-level fields dropped (compile.py:220-223) ---
# Compilation keeps only `visual:` and drops `layout`, `product_image`, `scene_policy`.

@pytest.mark.xfail(reason="P1: compile.py drops layout/product_image/scene_policy")
def test_visual_spec_preserves_top_level_keys():
    """resolved-task must retain layout, product_image, scene_policy from visual-spec."""
    from compile import compile_campaign
    campaign_path = Path(tempfile.mkdtemp())
    (campaign_path / "campaigns").mkdir(parents=True)
    (campaign_path / "brands" / "testbrand" / "products").mkdir(parents=True)
    (campaign_path / "channels").mkdir()

    # Write minimal spec files
    brand_core = campaign_path / "brands" / "testbrand" / "brand-core.yaml"
    brand_core.write_text("brand:\n  name: TestBrand\n  colors:\n    primary: '#000'\n    secondary: '#666'\n    accent: '#888'\n    background: '#FFF'\n  typography:\n    latin:\n      heading: Inter\n      body: Inter\n  logo:\n    min_size_px: 48\n    clear_space_px: 24\n    allowed_backgrounds: [light, dark]\n  voice:\n    tone: [precise]\n    avoid: []\n  claims:\n    require_evidence: []")

    vs = campaign_path / "brands" / "testbrand" / "visual-spec.yaml"
    vs.write_text("visual:\n  default_ratio: '1:1'\nlayout:\n  density: low\n  product_coverage: '45%-60%'\n  safe_margin_px: 64\nproduct_image:\n  source_required: true\nscene_policy:\n  hero:\n    html_dominant: true\n    background_prompt: 'test prompt'")

    cs = campaign_path / "brands" / "testbrand" / "content-spec.yaml"
    cs.write_text("content:\n  default_language: zh-CN\n  claim_rules:\n    forbidden: []\n  message_hierarchy: {}")

    prod = campaign_path / "brands" / "testbrand" / "products" / "test.yaml"
    prod.write_text("product:\n  id: test\n  name: Test\n  facts: {}\n  assets: {}")

    ch = campaign_path / "channels" / "tmall.yaml"
    ch.write_text("channel:\n  id: tmall\n  visual: {}\n  content: {}")

    camp = campaign_path / "campaigns" / "test.yaml"
    camp.write_text("campaign:\n  brand_ref: brands/testbrand/brand-core.yaml\n  product_ref: brands/testbrand/products/test.yaml\n  outputs:\n    visual: [{type: hero, channel: tmall, format: png}]\n    content: []")

    resolved = compile_campaign(str(camp))
    vspec = resolved.get("visual_spec", {})
    assert "layout" in vspec, "layout should be in visual_spec"
    assert "product_image" in vspec, "product_image should be in visual_spec"
    assert "scene_policy" in vspec, "scene_policy should be in visual_spec"


# --- P1-3: Empty output targets pass silently (compile.py:287) ---
# An empty target/output set can compile, render, verify, and exit zero.

@pytest.mark.xfail(reason="P1: empty output targets should block compilation")
def test_empty_output_targets_blocked():
    """Compilation with no output targets must fail."""
    from compile import compile_campaign
    campaign_path = Path(tempfile.mkdtemp())
    (campaign_path / "campaigns").mkdir(parents=True)
    (campaign_path / "brands" / "testbrand" / "products").mkdir(parents=True)
    (campaign_path / "channels").mkdir()

    brand_core = campaign_path / "brands" / "testbrand" / "brand-core.yaml"
    brand_core.write_text("brand:\n  name: T\n  colors:\n    primary: '#000'\n    secondary: '#666'\n    accent: '#888'\n    background: '#FFF'\n  typography:\n    latin:\n      heading: Inter\n      body: Inter\n  logo:\n    min_size_px: 48\n    clear_space_px: 24\n    allowed_backgrounds: [light, dark]\n  voice:\n    tone: [precise]\n    avoid: []\n  claims:\n    require_evidence: []")

    vs = campaign_path / "brands" / "testbrand" / "visual-spec.yaml"
    vs.write_text("visual:\n  default_ratio: '1:1'\nlayout:\n  density: low\n  product_coverage: '45%-60%'\n  safe_margin_px: 64\nproduct_image:\n  source_required: false\nscene_policy:\n  hero:\n    html_dominant: true")

    cs = campaign_path / "brands" / "testbrand" / "content-spec.yaml"
    cs.write_text("content:\n  default_language: zh-CN\n  claim_rules:\n    forbidden: []\n  message_hierarchy: {}")

    prod = campaign_path / "brands" / "testbrand" / "products" / "test.yaml"
    prod.write_text("product:\n  id: test\n  name: Test\n  facts: {}\n  assets: {}")

    ch = campaign_path / "channels" / "tmall.yaml"
    ch.write_text("channel:\n  id: tmall\n  visual: {}\n  content: {}")

    camp = campaign_path / "campaigns" / "test.yaml"
    camp.write_text("campaign:\n  brand_ref: brands/testbrand/brand-core.yaml\n  product_ref: brands/testbrand/products/test.yaml\n  outputs:\n    visual: []\n    content: []")

    with pytest.raises((SystemExit, RuntimeError)):
        compile_campaign(str(camp))


# --- P1-9: Evidence files don't exist (brands/aether/products/*.yaml) ---
# Evidence references like docs/x1-spec.pdf do not exist on disk.

@pytest.mark.xfail(reason="P1: evidence file existence is not checked during compile")
def test_evidence_file_exists():
    """Compilation must reject a fact whose source ref file does not exist on disk."""
    from compile import compile_campaign
    campaign_path = Path(tempfile.mkdtemp())
    (campaign_path / "campaigns").mkdir(parents=True)
    (campaign_path / "brands" / "testbrand" / "products").mkdir(parents=True)
    (campaign_path / "channels").mkdir()

    brand_core = campaign_path / "brands" / "testbrand" / "brand-core.yaml"
    brand_core.write_text("brand:\n  name: T\n  colors:\n    primary: '#000'\n    secondary: '#666'\n    accent: '#888'\n    background: '#FFF'\n  typography:\n    latin:\n      heading: Inter\n      body: Inter\n  logo:\n    min_size_px: 48\n    clear_space_px: 24\n    allowed_backgrounds: [light, dark]\n  voice:\n    tone: [precise]\n    avoid: []\n  claims:\n    require_evidence: []")

    vs = campaign_path / "brands" / "testbrand" / "visual-spec.yaml"
    vs.write_text("visual:\n  default_ratio: '1:1'\nlayout:\n  density: low\nproduct_image:\n  source_required: false\nscene_policy: {}")

    cs = campaign_path / "brands" / "testbrand" / "content-spec.yaml"
    cs.write_text("content:\n  default_language: zh-CN\n  claim_rules:\n    forbidden: []\n  message_hierarchy: {}")

    # Product with evidence file ref that does NOT exist
    prod = campaign_path / "brands" / "testbrand" / "products" / "test.yaml"
    prod.write_text("product:\n  id: test\n  name: Test\n  facts:\n    noise_reduction:\n      value: 42\n      unit: dB\n      source:\n        type: lab_report\n        ref: does-not-exist-on-disk.pdf\n      status: verified\n  assets: {}")

    ch = campaign_path / "channels" / "tmall.yaml"
    ch.write_text("channel:\n  id: tmall\n  visual: {}\n  content: {}")

    camp = campaign_path / "campaigns" / "test.yaml"
    camp.write_text("campaign:\n  brand_ref: brands/testbrand/brand-core.yaml\n  product_ref: brands/testbrand/products/test.yaml\n  outputs:\n    visual: [{type: hero, channel: tmall, format: png}]\n    content: []")

    with pytest.raises((SystemExit, RuntimeError)):
        compile_campaign(str(camp))


# --- P1-14/15: Unknown channel detection ---
# (redundant with existing test_audit, but committed as a P1 regression marker)

@pytest.mark.xfail(reason="P1: verification validates against hardcoded profiles, not compiled channel YAML (validate_channel.py:12,56)")
def test_channel_validation_uses_compiled_contract():
    """Channel validation must read from compiled channel YAML, not hardcoded profiles."""
    from validate_channel import validate_channel
    tmp = Path(tempfile.mktemp(suffix=".md"))
    # A subtle violation: no hard sell but uses imperative CTA without parameter-first structure
    # The compiled tmall YAML says: style: direct_conversion, avoid: [overly literary tone]
    # Hardcoded profile checks for has_parameter/has_bullets — different rules
    tmp.write_text("沉浸式听觉体验，感受每一个音符的细节")
    result = validate_channel(tmp, "tmall")
    tmp.unlink()
    # The compiled tmall contract would reject literary tone, but hardcoded
    # profile only checks parameter-first/bullets structure
    from compile import compile_campaign
    Path(tmp.parent / "channels").mkdir(exist_ok=True)
    # The divergence: hardcoded profile has different rules than channel YAML
    compiled_rules_known = result.get("signal_checks", [])
    has_parameter_check = any(c["check"] == "参数优先" for c in compiled_rules_known)
    assert has_parameter_check, "Must use channel YAML rules, not hardcoded profiles"
