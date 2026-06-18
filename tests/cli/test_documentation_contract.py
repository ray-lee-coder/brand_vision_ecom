from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]


def test_readme_uses_reproducible_offline_first_quick_start():
    readme = (REPO_ROOT / "README.md").read_text()

    assert "python3 -m pip install -r requirements.txt" in readme
    assert "python3 -m pytest -q" in readme
    offline = "bash scripts/brandkit build campaigns/618-launch.yaml --offline"
    online = "bash scripts/brandkit build campaigns/618-launch.yaml\n"
    assert offline in readme
    assert online in readme
    assert readme.index(offline) < readme.index(online)


def test_chinese_readme_describes_the_same_supported_cli():
    readme = (REPO_ROOT / "README.zh.md").read_text()

    assert "python3 -m pip install -r requirements.txt" in readme
    assert "bash scripts/brandkit build campaigns/618-launch.yaml --offline" in readme
    assert "output/runs/{run_id}/618-launch/" in readme
    assert "scripts/generate_image.py" not in readme
    assert "Instagram" not in readme


def test_skill_uses_only_supported_repository_cli_commands():
    skill = (REPO_ROOT / "SKILL.md").read_text()

    assert "bash scripts/brandkit build campaigns/{campaign}.yaml --offline" in skill
    assert "brandkit validate" not in skill
    assert "brandkit render" not in skill
    assert "抖音" not in skill
    assert "Instagram" not in skill


def test_mit_license_claim_has_license_file():
    license_text = (REPO_ROOT / "LICENSE").read_text()

    assert "MIT License" in license_text
    assert "Permission is hereby granted" in license_text


def test_runtime_http_dependency_is_declared():
    requirements = (REPO_ROOT / "requirements.txt").read_text().splitlines()

    assert any(line.startswith("requests==") for line in requirements)
    assert "urllib3==1.26.20" in requirements
