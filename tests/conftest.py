"""Shared pytest fixtures for BrandKit tests."""
import json
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = REPO_ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))


@pytest.fixture
def repo_root() -> Path:
    return REPO_ROOT


@pytest.fixture
def scripts_dir() -> Path:
    return SCRIPTS_DIR


@pytest.fixture
def minimal_resolved_task():
    """Minimal valid resolved-task for unit tests."""
    return {
        "campaign": {"name": "test-campaign"},
        "brand": {
            "name": "TestBrand",
            "colors": {
                "primary": "#000",
                "secondary": "#666",
                "accent": "#888",
                "background": "#FFF",
            },
            "typography": {"latin": {"heading": "Inter", "body": "Inter"}},
        },
        "visual_spec": {
            "product_image": {"source_required": False},
            "scene_policy": {},
        },
        "content_spec": {"claim_rules": {"forbidden": []}, "message_hierarchy": {}},
        "product": {"name": "T", "facts": {}, "assets": {}},
        "output_targets": [],
    }


@pytest.fixture
def minimal_message_plan():
    """Minimal message-plan for unit tests."""
    return {
        "primary_benefit": {"statement": "Benefit", "id": "benefit_1"},
        "secondary_benefits": [],
        "proof_points": [],
        "visual": {"headline": "H", "subtitle": "S"},
    }
