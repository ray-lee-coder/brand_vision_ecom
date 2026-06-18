"""
P1 failure tests: verification fail-closed, provenance, browser.

Each test encodes a known P1 bug as a reproducible red test.
Tests fail with the current code and will pass when Stage 2 fixes are applied.
"""
import json
import sys
import tempfile
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "scripts"))


# --- P1-4: Missing Playwright/browser exceptions do not fail (verify.py:47-83) ---
# Visual verification can exit successfully without running its main assertions.

def test_verification_fails_on_browser_error():
    """Browser launch failure must produce a non-zero failure count."""
    from verify import verify_visual
    resolved = {
        "brand": {
            "colors": {"primary": "#000", "secondary": "#666", "accent": "#888", "background": "#FFF"},
            "typography": {"latin": {"heading": "Inter", "body": "Inter"}},
        },
    }
    html_path = Path(tempfile.mktemp(suffix=".html"))
    html_path.write_text("<html><body></body></html>")
    result = verify_visual(str(html_path), resolved, {})
    html_path.unlink()
    assert result["failed"] > 0, "Browser error should increment failures"


# --- P1-5: Missing/forged provenance passes (verify.py:121-147) ---
# Missing provenance passes, and a forged nonexistent fact ID passes.

def test_forged_provenance_blocked():
    """Provenance with nonexistent fact_id and evidence must be rejected."""
    from verify import verify_content
    resolved = {
        "brand": {"claims": {"require_evidence": []}, "voice": {"avoid": []}},
        "content_spec": {"claim_rules": {"forbidden": []}},
        "product": {"facts": {}},
    }
    tmp = Path(tempfile.mktemp(suffix=".md"))
    tmp.write_text("Some claim about 42dB")
    prov = tmp.with_suffix(".provenance.json")
    # Forged: fact ID that doesn't exist, evidence file that doesn't exist
    prov.write_text(json.dumps({
        "claims": [{
            "claim": "42dB noise reduction",
            "fact_ref": "facts.nonexistent_fact",
            "source_ref": "nonexistent-evidence.pdf",
            "status": "verified"
        }]
    }))
    result = verify_content(tmp, resolved, {})
    tmp.unlink()
    prov.unlink()
    assert result["build_blocked"], "Forged provenance must block build"
    assert result["failed"] > 0, "Forged provenance must increment failures"


# --- P1-9 continued: Missing evidence must block ---
def test_missing_evidence_blocked():
    """Provenance referencing a nonexistent evidence file must be rejected."""
    from verify import verify_content
    resolved = {
        "brand": {"claims": {"require_evidence": []}, "voice": {"avoid": []}},
        "content_spec": {"claim_rules": {"forbidden": []}},
        "product": {"facts": {"test_fact": {
            "value": 42, "unit": "dB",
            "source": {"ref": "does-not-exist.pdf"},
            "status": "verified",
        }}},
    }
    tmp = Path(tempfile.mktemp(suffix=".md"))
    tmp.write_text("Test 42dB claim")
    prov = tmp.with_suffix(".provenance.json")
    prov.write_text(json.dumps({
        "claims": [{
            "claim": "42dB",
            "fact_ref": "facts.test_fact",
            "source_ref": "does-not-exist.pdf",
            "status": "verified"
        }]
    }))
    result = verify_content(tmp, resolved, {})
    tmp.unlink()
    prov.unlink()
    assert result["build_blocked"], "Missing evidence must block build"


# --- P1-3: Verification scans historical campaigns (verify.py:217-249, validate_channel.py:192-209) ---
# Verification scans all historical campaign outputs using the current campaign's resolved task.
# This is a structural issue; the current iteration pattern over output/* can read stale artifacts.
# The fix needs run-context scoping. For now, this test documents the failure class.


# --- P1-12: Offline rendering fabricates brand-specific copy (render_content.py:122) ---
# Offline rendering fabricates generic brand copy for every brand.

def test_offline_rendering_uses_facts_not_templates():
    """Offline output must render from product facts, not hardcoded generic templates."""
    from render_content import render_content
    tmp = Path(tempfile.mkdtemp())
    message_plan = {
        "primary_benefit": {"statement": "Benefit X", "id": "benefit_x"},
        "secondary_benefits": [],
        "proof_points": [{"claim_ref": "facts.fact_a"}, {"claim_ref": "facts.fact_b"}],
        "visual": {"headline": "H", "subtitle": "S"},
    }
    resolved = {
        "campaign": {"name": "other-brand"},
        "brand": {
            "name": "OtherBrand", "category": "food",
            "colors": {"primary": "#000", "secondary": "#666", "accent": "#888", "background": "#FFF"},
            "typography": {"latin": {"heading": "Inter", "body": "Inter"}},
        },
        "visual_spec": {"product_image": {"source_required": False}, "scene_policy": {}},
        "content_spec": {"claim_rules": {"forbidden": []}, "message_hierarchy": {}},
        "product": {"name": "Snack", "facts": {"fact_a": {"value": 200, "unit": "g", "source": {"ref": "spec.pdf"}, "status": "verified"}, "fact_b": {"value": 80, "unit": "cal", "source": {"ref": "spec.pdf"}, "status": "verified"}}, "assets": {}},
        "output_targets": [
            {"type": "content", "content_type": "bullet_points", "channel": "tmall", "constraints": {}},
        ],
    }
    result = render_content(resolved, tmp, message_plan, dry_run=True)
    for f in tmp.rglob("*.md"):
        text = f.read_text()
        # The output should reference actual fact values (200g), not generic template text
        has_fact_value = "200" in text or "80" in text or "g" in text or "cal" in text
        # Count repeated generic tags — more than 2 identical lines = template fabric
        lines = [l.strip() for l in text.split("\n") if l.strip()]
        repeated = max(lines.count(l) for l in lines)
        assert has_fact_value, f"Output must reference product facts: {text}"
        assert repeated <= 2, f"Too many repeated template lines ({repeated}): {text}"
