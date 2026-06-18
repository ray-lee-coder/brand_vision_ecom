#!/usr/bin/env python3
"""
BrandKit 审计合规测试 (v0.3.0)
覆盖 GPT 审计要求的 9 个关键测试用例
"""

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

# Add scripts to path
SCRIPTS_DIR = Path(__file__).parent.parent / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

TEST_DIR = Path(__file__).parent / "tests"
TEST_DIR.mkdir(exist_ok=True)


class TestCompileMissingProduct(unittest.TestCase):
    """P0-6: product facts 缺 source → 阻断"""

    def test_missing_fact_source_detected(self):
        from compile import detect_conflicts
        resolved = {
            "product": {
                "facts": {
                    "noise_reduction": {
                        "value": 42, "unit": "dB",
                        "source": {},  # No ref
                    }
                }
            },
            "brand": {},
            "channels": {},
        }
        sources = {"campaign": {"outputs": {"visual": [], "content": []}}}
        conflicts = detect_conflicts(resolved, sources)
        has_missing = any(c["type"] == "missing_source" for c in conflicts)
        self.assertTrue(has_missing, "Should detect missing source ref")


class TestCompileUnknownChannel(unittest.TestCase):
    """P0-6: unknown channel → 阻断"""

    def test_unknown_channel_detected(self):
        from compile import detect_conflicts
        resolved = {
            "brand": {}, "product": {"facts": {}},
            "channels": {"tmall": {}},  # Only tmall registered
        }
        sources = {
            "campaign": {
                "outputs": {
                    "visual": [{"type": "hero", "channel": "unknown_ch"}],
                    "content": [],
                }
            }
        }
        conflicts = detect_conflicts(resolved, sources)
        has_unknown = any(c["type"] == "unknown_channel" for c in conflicts)
        self.assertTrue(has_unknown, "Should detect unknown channel")


class TestCompileForbiddenClaim(unittest.TestCase):
    """P0-6: 禁用宣称在 override 中 → 阻断"""

    def test_forbidden_color_override_detected(self):
        from compile import detect_conflicts
        resolved = {
            "brand": {"colors": {"forbidden": ["#FF00FF"]}},
            "product": {"facts": {}},
            "channels": {},
        }
        sources = {
            "campaign": {
                "override": {"headline": "use #FF00FF color"},
                "outputs": {"visual": [], "content": []},
            }
        }
        conflicts = detect_conflicts(resolved, sources)
        has_violation = any(c["type"] == "hard_constraint_violation" for c in conflicts)
        self.assertTrue(has_violation, "Should detect forbidden color in override")


class TestMessagePlanUsedByVisual(unittest.TestCase):
    """P0-2: visual renderer 读取 message-plan"""

    def test_visual_reads_message_plan(self):
        from render_visual import render_html
        resolved = {
            "campaign": {"name": "test-campaign"},
            "brand": {
                "name": "TestBrand",
                "colors": {"primary": "#000", "secondary": "#666", "accent": "#888", "background": "#FFF"},
                "typography": {"latin": {"heading": "Inter", "body": "Inter"}},
            },
            "visual_spec": {
                "product_image": {"source_required": False},
                "scene_policy": {},
            },
            "product": {"name": "Test", "assets": {}},
            "output_targets": [
                {"type": "visual", "scene": "hero", "channel": "tmall",
                 "ratio": "1:1", "constraints": {"safe_margin_px": 48}},
            ],
        }
        message_plan = {
            "visual": {
                "headline": "FromMessagePlan",
                "subtitle": "SubFromMessagePlan",
            }
        }
        out_dir = Path(tempfile.mkdtemp())
        rendered = render_html(resolved, out_dir, message_plan, allow_placeholder=True)
        self.assertGreater(len(rendered), 0)
        html_path = Path(rendered[0]["html_file"])
        with open(html_path) as f:
            content = f.read()
        self.assertIn("FromMessagePlan", content, "Visual should use headline from message-plan")
        self.assertIn("SubFromMessagePlan", content, "Visual should use subtitle from message-plan")


class TestClaimRequiresFactRef(unittest.TestCase):
    """P0-4: claims JSON 必须有 fact_ref"""

    def test_claim_with_fact_ref_passes(self):
        from verify import verify_content
        resolved = {
            "brand": {"claims": {"require_evidence": []}, "voice": {"avoid": []}},
            "content_spec": {"claim_rules": {"forbidden": []}},
            "product": {"facts": {"test_fact": {"source": {"ref": "doc.pdf"}, "status": "verified"}}},
        }
        tmp = Path(tempfile.mktemp(suffix=".md"))
        tmp.write_text("Test 42dB content")
        prov = tmp.with_suffix(".provenance.json")
        prov.write_text(json.dumps({
            "claims": [{"claim": "42dB", "fact_ref": "facts.test_fact", "source_ref": "doc.pdf", "status": "verified"}]
        }))
        # Create dummy evidence file for the provenance check (relative to CWD = repo root)
        evidence_path = Path("doc.pdf")
        evidence_path.write_text("dummy evidence")
        try:
            result = verify_content(tmp, resolved, {})
            self.assertEqual(result["failed"], 0, "Claim with fact_ref should pass")
        finally:
            if evidence_path.exists():
                evidence_path.unlink()
        tmp.unlink()
        prov.unlink()

    def test_missing_fact_ref_fails(self):
        from verify import verify_content
        resolved = {
            "brand": {"claims": {"require_evidence": ["best"]}, "voice": {"avoid": []}},
            "content_spec": {"claim_rules": {"forbidden": []}},
            "product": {"facts": {}},
        }
        tmp = Path(tempfile.mktemp(suffix=".md"))
        tmp.write_text("The best product")
        prov = tmp.with_suffix(".provenance.json")
        prov.write_text(json.dumps({"claims": []}))
        result = verify_content(tmp, resolved, {"primary_benefit": {"statement": ""}})
        self.assertGreater(result["failed"], 0, "Missing fact_ref for 'best' should fail")
        self.assertTrue(result["build_blocked"], "Build should be blocked")
        tmp.unlink()
        prov.unlink()


class TestMissingPackshotFails(unittest.TestCase):
    """P0-5: 产品素材缺失 → BUILD FAILED"""

    def test_missing_packshot_raises(self):
        from render_visual import resolve_product_image
        with self.assertRaises(RuntimeError):
            resolve_product_image({"assets": {}}, source_required=True, allow_placeholder=False)


class TestChannelValidationBlocks(unittest.TestCase):
    """P0-1: channel validation 默认阻断"""

    def test_channel_validation_blocks(self):
        from validate_channel import validate_channel
        tmp = Path(tempfile.mktemp(suffix=".md"))
        tmp.write_text("限时抢购！爆款降价！")
        result = validate_channel(tmp, "xiaohongshu")
        self.assertGreater(result["failed"], 0, "Hard sell should fail xiaohongshu validation")
        tmp.unlink()


class TestBuildOutputStructure(unittest.TestCase):
    """P1-3: output 按 campaign 分层"""

    def test_output_campaign_structure(self):
        from render_visual import render_html
        from render_content import render_content

        message_plan = {
            "primary_benefit": {"statement": "test"},
            "secondary_benefits": [],
            "proof_points": [],
            "visual": {"headline": "Test", "subtitle": "Test"},
        }
        resolved = {
            "campaign": {"name": "test-campaign"},
            "brand": {
                "name": "T",
                "colors": {"primary": "#000", "secondary": "#666", "accent": "#888", "background": "#FFF"},
                "typography": {"latin": {"heading": "Inter", "body": "Inter"}},
            },
            "visual_spec": {"product_image": {"source_required": False}, "scene_policy": {}},
            "content_spec": {"claim_rules": {"forbidden": []}, "message_hierarchy": {}},
            "product": {"name": "T", "assets": {}, "facts": {}},
            "output_targets": [
                {"type": "visual", "scene": "hero", "channel": "tmall", "ratio": "1:1", "constraints": {}},
                {"type": "content", "content_type": "product_title", "channel": "tmall", "constraints": {}},
            ],
        }
        out_dir = Path(tempfile.mkdtemp())
        render_html(resolved, out_dir, message_plan, allow_placeholder=True)
        render_content(resolved, out_dir, message_plan, dry_run=True)

        # Check campaign-level dir
        visual_dir = out_dir / "test-campaign" / "visual"
        content_dir = out_dir / "test-campaign" / "content"
        self.assertTrue(visual_dir.exists(), "Visual output should be under output/{campaign}/visual/")
        self.assertTrue(content_dir.exists(), "Content output should be under output/{campaign}/content/")


class TestOfflineModeExplicit(unittest.TestCase):
    """P0-1: dry-run 必须显式使用 --offline"""

    def test_offline_only_with_flag(self):
        """Verify --dry-run produces offline content without .build dependency"""
        import json
        from render_content import render_content

        tmp = Path(tempfile.mkdtemp())
        message_plan = {
            "primary_benefit": {"statement": "Test benefit", "id": "test_benefit"},
            "secondary_benefits": [],
            "proof_points": [],
            "visual": {"headline": "H", "subtitle": "S"},
        }
        resolved = {
            "campaign": {"name": "offline-test"},
            "brand": {
                "name": "T", "category": "electronics",
                "colors": {"primary": "#000", "secondary": "#666", "accent": "#888", "background": "#FFF"},
                "typography": {"latin": {"heading": "Inter", "body": "Inter"}},
            },
            "visual_spec": {"product_image": {"source_required": False}, "scene_policy": {}},
            "content_spec": {"claim_rules": {"forbidden": []}, "message_hierarchy": {}},
            "product": {"name": "T", "facts": {}, "assets": {}},
            "output_targets": [
                {"type": "content", "content_type": "product_title", "channel": "tmall", "constraints": {}},
            ],
        }
        result = render_content(resolved, tmp, message_plan, dry_run=True)
        self.assertIn("product_title", str(result))
        output_files = list(tmp.rglob("*"))
        self.assertGreater(len(output_files), 0, "Offline render should produce files")


if __name__ == "__main__":
    unittest.main()
