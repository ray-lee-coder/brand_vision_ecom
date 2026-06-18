import json
from pathlib import Path

import pytest


def test_content_overrides_apply_only_to_matching_content_targets():
    from contracts import apply_overrides

    resolved = {
        "output_targets": [
            {"type": "visual", "scene": "hero", "constraints": {}},
            {"type": "content", "content_type": "product_title", "constraints": {}},
            {"type": "content", "content_type": "bullet_points", "constraints": {}},
        ]
    }

    result = apply_overrides(
        resolved,
        {"product_title_max_chars": 32, "bullet_count": 3},
    )

    visual, title, bullets = result["output_targets"]
    assert "product_title_max_chars" not in visual["constraints"]
    assert "bullet_count" not in visual["constraints"]
    assert title["constraints"]["product_title_max_chars"] == 32
    assert "bullet_count" not in title["constraints"]
    assert bullets["constraints"]["bullet_count"] == 3
    assert "product_title_max_chars" not in bullets["constraints"]


def test_run_context_uses_explicit_run_scoped_paths(tmp_path):
    from run_context import create_run_context

    ctx = create_run_context("campaign-a", tmp_path, run_id="run-a")

    assert ctx.build_dir == tmp_path / ".build" / "runs" / "run-a" / "build"
    assert ctx.output_dir == tmp_path / "output" / "runs" / "run-a"
    assert ctx.verify_dir == tmp_path / ".build" / "runs" / "run-a" / "verify"
    assert ctx.manifest_path() == tmp_path / ".build" / "runs" / "run-a" / "manifest.json"


def test_manifest_content_paths_are_authoritative(tmp_path):
    from run_context import manifest_artifact_paths

    declared = tmp_path / "output" / "declared.md"
    undeclared = tmp_path / "output" / "undeclared.md"
    declared.parent.mkdir(parents=True)
    declared.write_text("declared")
    undeclared.write_text("undeclared")
    manifest = {
        "artifacts": {
            str(declared.relative_to(tmp_path)): {"category": "content"},
            str(undeclared.relative_to(tmp_path)): {"category": "other"},
        }
    }

    assert manifest_artifact_paths(manifest, tmp_path, category="content") == [declared]


def test_channel_validator_uses_compiled_contract(tmp_path):
    from validate_channel import validate_channel

    content = tmp_path / "custom-product_title.md"
    content.write_text("123456")
    compiled_channel = {"content": {"product_title": {"max_chars": 5}}}

    result = validate_channel(
        content,
        "custom",
        channel_contract=compiled_channel,
        content_type="product_title",
    )

    assert result["failed"] == 1
    assert any(c["check"] == "max_chars" for c in result["signal_checks"])


def test_cross_channel_non_match_uses_informational_icon():
    from validate_channel import format_diff_icon

    assert format_diff_icon(True) == "✅"
    assert format_diff_icon(False) == "ℹ"


def test_scene_policy_preserves_brand_background_prompt():
    from render_visual import get_scene_policy

    policy = get_scene_policy(
        {"scene_policy": {"lifestyle": {"regenerate_background": True, "background_prompt": "citrus picnic"}}},
        "lifestyle",
    )

    assert policy["background_prompt"] == "citrus picnic"


def test_default_background_prompt_is_brand_neutral():
    from background_generator import build_background_prompt

    prompt = build_background_prompt(
        "lifestyle",
        {"primary": "#E85D2C", "accent": "#2A9D8F", "background": "#FFF8F0"},
        "Sparkling Citrus",
        brand_name="Acme Beverages",
        brand_category="food-beverage",
        brand_keywords=["vibrant", "refreshing"],
    )

    assert "Acme Beverages" in prompt
    assert "food-beverage" in prompt
    assert "premium audio" not in prompt.lower()


def test_copy_system_prompt_uses_schema_examples_not_aether_claims():
    from copy_generator import build_system_prompt

    prompt = build_system_prompt({}, {}, {}, {}, "product_title")

    assert "42dB" not in prompt
    assert "x1-noise-test" not in prompt


def test_synthetic_evidence_requires_traceability_metadata(tmp_path):
    from contracts import ContractError, require_file

    evidence = tmp_path / "evidence.yaml"
    evidence.write_text("evidence_type: synthetic_fixture\nissuer: BrandKit test suite\n")
    with pytest.raises(ContractError, match="invalid_evidence_fixture"):
        require_file(tmp_path, "evidence.yaml")

    evidence.write_text(
        "evidence_type: synthetic_fixture\n"
        "issuer: BrandKit test suite\n"
        "issued_at: 2026-06-18\n"
        "method: deterministic fixture for contract testing\n"
        "fact_ids: [facts.example]\n"
    )
    assert require_file(tmp_path, "evidence.yaml").endswith("evidence.yaml")


@pytest.mark.parametrize(
    "payload",
    [
        {},
        {"text": 123, "claims": []},
        {"text": "copy", "claims": {}},
        {"text": "copy", "claims": [{"claim": "x"}]},
    ],
)
def test_copy_provider_rejects_invalid_response_shape(monkeypatch, payload):
    import copy_generator

    monkeypatch.setattr(copy_generator, "call_llm", lambda *args, **kwargs: json.dumps(payload))

    with pytest.raises(copy_generator.ProviderError, match="INVALID_RESPONSE_SCHEMA"):
        copy_generator.generate_copy({}, {}, {}, {}, "title", "tmall")
