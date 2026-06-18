# BrandKit Beta Reliability Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.
>
> **Strict reassessment 2026-06-18:** Recovery R1-R4 is complete and automated R5 evidence passes, but Beta remains **NOT CLEARED**. R6 Release Truth must precede R7 human acceptance. See `docs/reviews/2026-06-18-gstack-multirole-goal-review.md`.

## Current Execution Contract

Commit labels and file presence do not complete a task. A task is complete only when its focused tests and the applicable real CLI gates pass from a clean checkout.

| Batch | Current status | Blocking evidence |
|---|---|---|
| R1 Truth layer | DONE | `39 passed`; single build and `build-all --offline` exit zero |
| R2 Active contracts | DONE | Six documents enforced; field-to-content-type override tests pass; declared synthetic evidence fixtures require traceability metadata |
| R3 Run ownership | DONE | Explicit run roots isolate build/output/verify; manifests drive downstream artifact selection; concurrent and missing-artifact tests pass |
| R4 Trust boundary | DONE | Fact-bound templates, brand-neutral prompts, compiled channel contracts, strict provider response shape, and fail-closed manifest verification are tested |
| R5 Product evidence | PARTIAL | Five isolated offline modification trials pass with recorded hashes, boundaries, call counts, and timing; completed non-author rubric remains pending |
| R6 Release truth | IN PROGRESS | Public CLI, run ID safety, manifest failure semantics, documentation, license, fixed RC, and current CI evidence |
| R7 Beta evidence | NOT STARTED | PNG determinism, observed provider budgets/error matrix, and named non-author acceptance on one RC SHA |

Mandatory gates after each batch:

```bash
python3 -m pytest -q
bash scripts/brandkit build campaigns/618-launch.yaml --offline
bash scripts/brandkit build-all --offline
```

R3-R5 additionally require clean-clone and ordered/concurrent isolation tests. The detailed recovery order and acceptance evidence are maintained in `docs/reviews/2026-06-18-beta-reassessment.md`.

**Goal:** 将 BrandKit 从可运行的 Alpha/Demo 收敛为可供个人和小团队可靠使用、具备真实证据的 Beta。

**Architecture:** 保留现有 Python + YAML + Shell 架构，先建立可执行契约和失败关闭机制，再按单次运行清单隔离编译、渲染、验证与产物。离线与在线模式共享同一事实和渠道契约，但离线模式必须无网络且不生成品牌专属虚构内容。生产级租户、服务化、数据库和协作能力不在本轮范围。

**Tech Stack:** Python 3.11, PyYAML, jsonschema, pytest, Playwright/Chromium, Bash, GitHub Actions

---

## Outcome And Gates

| Stage | Target | Exit gate |
|---|---|---|
| 1. Contract | 把 15 个 P1 变成红灯测试，修正产品计划状态 | 干净克隆可运行测试；所有已知 P1 有稳定失败用例 |
| 2. Foundation | 修复编译契约、运行隔离、失败语义和离线可靠性 | macOS 14 与 Ubuntu 24.04 离线 E2E 通过；无网络调用；并发产物不串线 |
| 3. Evidence | 第二品牌、四个 campaign、非作者用户验收 | 自动门禁全绿；真实证据文件存在；人工 Beta rubric 达标 |

发布决定只能由 Gate 3 触发。M0-M3 报告只能作为历史实现记录，不能作为 Beta 验收证据。

## File Map

| File | Responsibility |
|---|---|
| `requirements.txt` | 固定运行与测试依赖 |
| `.github/workflows/test.yml` | 干净环境测试与离线 E2E |
| `schemas/*.schema.json` | 六类 YAML 输入的 versioned schema |
| `scripts/contracts.py` | schema 校验、路径解析、override allowlist |
| `scripts/compile.py` | 生成 resolved task、message plan 和 run manifest |
| `scripts/run_context.py` | 单次运行 ID、目录和 manifest 数据结构 |
| `scripts/brandkit` | 参数转发、子进程退出聚合、run-dir 传递 |
| `scripts/render_content.py` | 基于事实的离线内容和严格在线结果消费 |
| `scripts/render_visual.py` | 消费完整视觉契约并登记产物 |
| `scripts/copy_generator.py` | 严格 provider JSON contract |
| `scripts/background_generator.py` | 显式 provider 错误和可选缓存 |
| `scripts/verify.py` | campaign/run scoped fail-closed verification |
| `scripts/validate_channel.py` | 从 compiled channel contract 校验并正确退出 |
| `templates/*.html` | 只渲染传入的事实字段，不包含产品硬编码宣称 |
| `tests/fixtures/` | 两品牌、有效/无效 spec、provider 响应和证据文件 |
| `tests/unit/` | schema、override、事实绑定和诊断单元测试 |
| `tests/integration/` | 编译、渲染、验证和并发隔离测试 |
| `tests/cli/` | CLI flags、退出码、非仓库 cwd、build-all 测试 |
| `tests/e2e/` | 干净离线 Beta 主路径 |

## Stage 1: Executable Contract

### Task 1: Correct Product Status And Freeze Beta Scope

**Files:**
- Modify: `PRODUCT-PLAN.md:1-15`
- Modify: `M0-REPORT.md`, `M1-REPORT.md`, `M2-REPORT.md`, `M3-REPORT.md`
- Reference: `docs/reviews/2026-06-18-gstack-engineering-review.md`

- [ ] **Step 1: Replace the current execution claim**

Use this status block in `PRODUCT-PLAN.md`:

```markdown
> 版本：Product Plan v2.2-beta-recovery
> 产品阶段：Alpha implementation complete; Beta validation pending
> 当前目标：个人/小团队可可靠使用的 Beta
> 发布状态：NOT CLEARED；必须通过 Stage 1-3 gates
> 生产级改造：明确不在本轮范围，待 Beta 使用证据成立后评估
```

- [ ] **Step 2: Mark milestone reports as historical evidence**

Add directly below each report title:

```markdown
> Status: Historical implementation note. This document does not prove Beta readiness.
> Authoritative gates: PRODUCT-PLAN.md and docs/superpowers/plans/2026-06-18-beta-reliability.md.
```

- [ ] **Step 3: Verify status language**

Run: `rg -n "Beta validation pending|Historical implementation note|NOT CLEARED" PRODUCT-PLAN.md M?-REPORT.md`

Expected: one Beta status in the plan and one historical disclaimer in each M0-M3 report.

- [ ] **Step 4: Commit**

```bash
git add PRODUCT-PLAN.md M0-REPORT.md M1-REPORT.md M2-REPORT.md M3-REPORT.md
git commit -m "docs: align roadmap with beta validation status"
```

### Task 2: Make Tests Hermetic And Install Reproducible

**Files:**
- Create: `requirements.txt`
- Create: `.github/workflows/test.yml`
- Modify: `tests/test_audit.py:225-237`
- Create: `tests/conftest.py`
- Create: `tests/e2e/test_offline_beta.py`

- [ ] **Step 1: Replace the state-dependent offline test**

```python
def test_offline_render_uses_explicit_fixture(tmp_path, resolved_task, message_plan):
    resolved = tmp_path / "resolved-task.json"
    message = tmp_path / "message-plan.json"
    resolved.write_text(json.dumps(resolved_task), encoding="utf-8")
    message.write_text(json.dumps(message_plan), encoding="utf-8")
    result = subprocess.run(
        [sys.executable, "scripts/render_content.py", "--dry-run",
         "--resolved", str(resolved), "--message-plan", str(message),
         "--output-dir", str(tmp_path / "output")],
        capture_output=True, text=True, cwd=REPO_ROOT,
    )
    assert result.returncode == 0, result.stderr
    assert "Content mode: dry-run fallback" in result.stdout
```

- [ ] **Step 2: Run before implementation state exists**

Run: `tmp="$(mktemp -d)" && git clone --local . "$tmp/repo" && cd "$tmp/repo" && python3 -m pytest tests/test_audit.py -v`

Expected: all tests pass in the clean clone before any command creates `.build` state.

- [ ] **Step 3: Pin dependencies**

```text
PyYAML==6.0.2
jsonschema==4.23.0
playwright==1.52.0
pytest==8.3.5
```

- [ ] **Step 4: Add CI matrix**

```yaml
name: test
on: [push, pull_request]
jobs:
  test:
    strategy:
      matrix:
        os: [ubuntu-24.04, macos-14]
        python: ["3.11"]
    runs-on: ${{ matrix.os }}
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: {python-version: "3.11"}
      - run: pip install -r requirements.txt
      - run: python -m playwright install chromium
      - run: python -m pytest -q
      - run: bash scripts/brandkit build tests/fixtures/campaigns/acme-launch.yaml --offline
```

- [ ] **Step 5: Commit**

```bash
git add requirements.txt .github/workflows/test.yml tests
git commit -m "test: make clean checkout beta path reproducible"
```

### Task 3: Encode P1 Failures As Red Tests

**Files:**
- Create: `tests/unit/test_contracts.py`
- Create: `tests/integration/test_run_isolation.py`
- Create: `tests/integration/test_verification_fail_closed.py`
- Create: `tests/cli/test_brandkit_cli.py`
- Create: `tests/fixtures/providers/`

- [ ] **Step 1: Add compiler contract cases**

```python
@pytest.mark.parametrize("mutation,error_code", [
    (lambda c: c.update(outputs={}), "empty_output_targets"),
    (lambda c: c.update(override={"unknown": 1}), "unknown_override"),
])
def test_compile_rejects_invalid_contract(campaign, mutation, error_code):
    mutation(campaign)
    result = compile_fixture(campaign)
    assert result["status"] == "failed"
    assert error_code in {item["type"] for item in result["conflicts"]}
```

- [ ] **Step 2: Add fail-closed verification cases**

```python
@pytest.mark.parametrize("case", [
    "missing_provenance", "unknown_fact_ref", "missing_evidence_file",
    "browser_launch_error", "zero_artifacts",
])
def test_verification_blocks(case, verification_case):
    result = verification_case(case).run()
    assert result.returncode != 0
    assert result.report["failed"] >= 1
```

- [ ] **Step 3: Add CLI flag and aggregation cases**

```python
def test_build_all_offline_never_calls_provider(cli, provider_spy):
    result = cli("build-all", "--offline")
    assert result.returncode == 0
    assert provider_spy.calls == []

def test_build_all_returns_nonzero_when_child_fails(cli, failing_campaign):
    result = cli("build-all", "--offline", env=failing_campaign.env)
    assert result.returncode != 0
    assert "All campaigns built" not in result.stdout
```

- [ ] **Step 4: Confirm tests fail for the intended reasons**

Run: `python3 -m pytest tests/unit tests/integration tests/cli -v`

Expected: failures identify the current override, isolation, provenance, empty-output, channel-exit, provider, and CLI bugs; no fixture/setup errors.

- [ ] **Step 5: Commit red tests**

```bash
git add tests
git commit -m "test: encode beta reliability failures"
```

## Stage 2: Beta Foundation

### Task 4: Add Versioned Schemas And Explicit Override Policy

**Files:**
- Create: `schemas/brand-core.schema.json`
- Create: `schemas/visual-spec.schema.json`
- Create: `schemas/content-spec.schema.json`
- Create: `schemas/product.schema.json`
- Create: `schemas/channel.schema.json`
- Create: `schemas/campaign.schema.json`
- Create: `scripts/contracts.py`
- Modify: `scripts/compile.py:49-233`
- Test: `tests/unit/test_contracts.py`

- [ ] **Step 1: Define the only permitted overrides**

```python
OVERRIDE_PATHS = {
    "visual.headline_max_lines",
    "visual.safe_margin_px",
    "content.product_title.max_chars",
    "content.bullets.count",
    "content.bullets.max_chars_each",
}

def apply_overrides(resolved: dict, overrides: dict) -> dict:
    unknown = set(overrides) - OVERRIDE_PATHS
    if unknown:
        raise ContractError("unknown_override", sorted(unknown))
    result = copy.deepcopy(resolved)
    for dotted_path, value in overrides.items():
        set_path(result, dotted_path, value)
    return result
```

- [ ] **Step 2: Preserve the full visual contract**

```python
resolved["visual_spec"] = {
    "visual": visual_spec.get("visual", {}),
    "layout": visual_spec.get("layout", {}),
    "product_image": visual_spec.get("product_image", {}),
    "scene_policy": visual_spec.get("scene_policy", {}),
}
```

- [ ] **Step 3: Validate schemas, refs, evidence, and non-empty targets before writing**

```python
validate_document("campaign", campaign)
require_file(project_root, campaign["campaign"]["brand_ref"])
require_file(project_root, campaign["campaign"]["product_ref"])
for fact_id, fact in product["product"]["facts"].items():
    require_file(project_root, fact["source"]["ref"], code="missing_evidence")
if not output_targets:
    raise ContractError("empty_output_targets", campaign_name)
```

- [ ] **Step 4: Run focused tests**

Run: `python3 -m pytest tests/unit/test_contracts.py -v`

Expected: schema, refs, allowed overrides, rejected overrides, complete visual spec, evidence existence, and non-empty target tests pass.

- [ ] **Step 5: Commit**

```bash
git add schemas scripts/contracts.py scripts/compile.py tests/unit/test_contracts.py
git commit -m "feat: enforce versioned compilation contracts"
```

### Task 5: Introduce Run-Scoped Manifests And Artifact Isolation

**Files:**
- Create: `scripts/run_context.py`
- Modify: `scripts/compile.py:320-333`
- Modify: `scripts/render_visual.py:212-256`
- Modify: `scripts/render_content.py:201-230`
- Modify: `scripts/verify.py:197-282`
- Modify: `scripts/validate_channel.py:188-319`
- Modify: `scripts/brandkit:35-86`
- Test: `tests/integration/test_run_isolation.py`

- [ ] **Step 1: Define one manifest contract**

```python
@dataclass(frozen=True)
class RunContext:
    run_id: str
    campaign: str
    root: Path

    @property
    def build_dir(self) -> Path: return self.root / "build"
    @property
    def output_dir(self) -> Path: return self.root / "output"
    @property
    def report_dir(self) -> Path: return self.root / "reports"
```

Manifest JSON must contain `run_id`, `campaign`, `mode`, `inputs`, `targets`, `artifacts`, `reports`, and SHA-256 hashes. It must not contain timestamps in canonical hash inputs.

- [ ] **Step 2: Route every command through the same run directory**

```bash
RUN_ID="${BRANDKIT_RUN_ID:-$(date -u +%Y%m%dT%H%M%SZ)-$$}"
RUN_DIR="${BRANDKIT_RUN_ROOT:-.runs}/$RUN_ID"
python3 scripts/compile.py "$CAMPAIGN" --build-dir "$RUN_DIR/build" --manifest "$RUN_DIR/manifest.json"
python3 scripts/render_visual.py --resolved "$RUN_DIR/build/resolved-task.json" --output-dir "$RUN_DIR/output" --manifest "$RUN_DIR/manifest.json"
```

- [ ] **Step 3: Verify only manifest-declared artifacts**

Remove directory-wide iteration over `output/*`. Load the manifest and reject an artifact when its campaign, path, or hash is absent/mismatched.

- [ ] **Step 4: Run isolation tests**

Run: `python3 -m pytest tests/integration/test_run_isolation.py -v`

Expected: both build orders and two concurrent processes produce independent manifests, artifacts, and reports.

- [ ] **Step 5: Commit**

```bash
git add scripts tests/integration/test_run_isolation.py
git commit -m "feat: isolate campaign work with run manifests"
```

### Task 6: Make Offline Rendering Brand-Neutral And Fact-Bound

**Files:**
- Modify: `scripts/render_content.py:73-171`
- Modify: `scripts/render_visual.py:54-154`
- Modify: `templates/feature-grid.html:80-110`
- Modify: other `templates/*.html` containing product claims
- Create: `tests/unit/test_fact_rendering.py`

- [ ] **Step 1: Replace Aether copy with deterministic fact segments**

```python
def offline_segments(message_plan, facts, target):
    proof = [
        {"text": format_fact(ref, fact), "fact_ref": f"facts.{ref}",
         "source_ref": fact["source"]["ref"], "status": fact["status"]}
        for ref, fact in facts.items()
    ]
    return {
        "text": render_target_text(target, message_plan, proof),
        "claims": proof,
    }
```

No literal `Aether`, `618`, `42dB`, `38h`, product category, or usage-duration claim may exist in renderer source or templates.

- [ ] **Step 2: Bind visual fact slots**

Replace template literals with named values such as `{{FACT_1_VALUE}}`, `{{FACT_1_LABEL}}`, and `{{FACT_1_REF}}`; render only values selected from the current product facts.

- [ ] **Step 3: Consume compiled layout and scene policy**

```python
layout = resolved["visual_spec"]["layout"]
scene = resolved["visual_spec"]["scene_policy"].get(target["scene"], {})
coverage = target["constraints"].get("product_coverage", layout["product_coverage"])
background_prompt = scene.get("background_prompt")
```

- [ ] **Step 4: Run tests and literal scan**

Run: `python3 -m pytest tests/unit/test_fact_rendering.py -v && ! rg -n "Aether|42dB|38h|两周|#Aether" scripts/render_content.py templates`

Expected: two fixture brands render only their own facts; literal scan returns no matches.

- [ ] **Step 5: Commit**

```bash
git add scripts/render_content.py scripts/render_visual.py templates tests/unit/test_fact_rendering.py
git commit -m "fix: bind offline and visual output to product facts"
```

### Task 7: Fail Closed In Verification And Channel Validation

**Files:**
- Modify: `scripts/verify.py:27-282`
- Modify: `scripts/validate_channel.py:12-319`
- Test: `tests/integration/test_verification_fail_closed.py`

- [ ] **Step 1: Treat skipped checks as failures**

```python
except Exception as exc:
    result["checks"].append({"name": "browser_render", "status": "failed", "error": str(exc)})
    result["failed"] += 1
    result["build_blocked"] = True
```

- [ ] **Step 2: Validate provenance against source data**

For every objective claim: require provenance; parse `facts.<id>`; verify the fact exists; compare `source_ref`; require the evidence path to exist under project root; require the claim text or normalized value to occur in the artifact. Missing provenance is a failure even when no restricted keyword is present.

- [ ] **Step 3: Remove hardcoded channel profiles**

```python
def validate_channel(content_path, channel_id, channels):
    contract = channels[channel_id]["content"]
    return validate_text(content_path.read_text(), contract)
```

- [ ] **Step 4: Aggregate all failures into the process exit**

```python
failed = sum(item["failed"] for item in file_results) + diff_result["failed"]
sys.exit(1 if failed and not args.allow_warnings else 0)
```

- [ ] **Step 5: Run fail-closed tests**

Run: `python3 -m pytest tests/integration/test_verification_fail_closed.py -v`

Expected: missing browser, missing/forged provenance, missing evidence, prohibited single-channel copy, stale output, and zero checks all return non-zero.

- [ ] **Step 6: Commit**

```bash
git add scripts/verify.py scripts/validate_channel.py tests/integration/test_verification_fail_closed.py
git commit -m "fix: make verification and channel gates fail closed"
```

### Task 8: Enforce Provider And CLI Failure Contracts

**Files:**
- Modify: `scripts/copy_generator.py:32-171`
- Modify: `scripts/background_generator.py:35-145`
- Modify: `scripts/brandkit:15-86`
- Test: `tests/unit/test_provider_contracts.py`
- Test: `tests/cli/test_brandkit_cli.py`

- [ ] **Step 1: Use structured provider errors**

```python
class ProviderError(RuntimeError):
    def __init__(self, provider, code, detail):
        self.provider = provider
        self.code = code
        self.detail = detail
        super().__init__(f"{provider}:{code}: {detail}")
```

Timeout, auth, rate limit, server error, malformed JSON, missing `text`, invalid `claims`, and invalid image payload must raise `ProviderError`. Online mode must never convert these failures into empty copy or placeholders.

- [ ] **Step 2: Parse CLI flags without rewriting offline into dry-run**

Keep `OFFLINE=1`, remove the flag from a rebuilt argument array, and pass the correct child-specific options: `--placeholder` only to visual rendering and `--dry-run` only to content rendering.

- [ ] **Step 3: Aggregate build-all failures**

```bash
status=0
for f in campaigns/*.yaml; do
  child_args=(build "$f")
  [[ "$OFFLINE" == 1 ]] && child_args+=(--offline)
  bash "$0" "${child_args[@]}" || status=1
done
[[ $status -eq 0 ]] && echo "[DONE] All campaigns built."
exit "$status"
```

- [ ] **Step 4: Run contract and CLI tests**

Run: `python3 -m pytest tests/unit/test_provider_contracts.py tests/cli/test_brandkit_cli.py -v`

Expected: provider failures are explicit; malformed responses block; offline build-all makes zero provider calls; one child failure makes the command non-zero.

- [ ] **Step 5: Commit**

```bash
git add scripts tests/unit/test_provider_contracts.py tests/cli/test_brandkit_cli.py
git commit -m "fix: enforce provider and cli failure contracts"
```

## Stage 3: Evidence And Prerelease

### Task 9: Prove Multi-Brand Usefulness

**Files:**
- Create: `tests/fixtures/brands/acme/`
- Create: `tests/fixtures/campaigns/acme-launch.yaml`
- Create: `docs/beta/acceptance-rubric.md`
- Create: `docs/beta/evidence-report.md`
- Modify: `scripts/run_baseline.py`

- [ ] **Step 1: Add a genuinely different second brand**

The fixture must use a non-audio category, different channel constraints, real local evidence files, and no Python changes. It cannot be another Aether SKU.

- [ ] **Step 2: Define the non-author rubric**

```markdown
| Task | Pass condition |
|---|---|
| Install | Fresh checkout to first offline build in <= 15 minutes |
| New campaign | User creates a valid campaign without editing Python |
| Constraint change | One allowed override changes only its declared target |
| Failure diagnosis | User resolves one invalid fact/source using CLI diagnostics |
| Output trust | User maps every objective claim to an existing evidence file |
```

Pass requires all five tasks from the primary tester and at least four from the backup tester, with commands, elapsed time, and observed errors recorded.

- [ ] **Step 3: Measure instead of estimate baseline data**

Record actual provider calls, wall time, generated artifacts, manual edits, failed checks, and reruns. Remove inferred “LLM call reduction equals revision reduction” language.

- [ ] **Step 4: Run the release candidate suite**

```bash
python3 -m pytest -q
bash scripts/brandkit build tests/fixtures/campaigns/aether-launch.yaml --offline
bash scripts/brandkit build tests/fixtures/campaigns/acme-launch.yaml --offline
bash scripts/brandkit build-all --offline
git diff --exit-code
```

Expected: all tests pass; each run has a complete isolated manifest; no network credentials are needed; tracked files remain unchanged.

- [ ] **Step 5: Record Beta decision**

`docs/beta/evidence-report.md` must list every gate as `PASS` or `FAIL`, link its machine/manual evidence, name both testers, and state `Beta prerelease approved` only when no gate is failed or missing.

- [ ] **Step 6: Commit**

```bash
git add tests/fixtures docs/beta scripts/run_baseline.py
git commit -m "test: add multi-brand beta acceptance evidence"
```

## Execution Order And Ownership

```text
Task 1 -> Task 2 -> Task 3
                   |
                   +-> Task 4 -> Task 5 -> Task 7 -> Task 8
                              \-> Task 6 ---/
                                           \-> Task 9
```

- Tasks 1-3 are sequential because they define authoritative status and red tests.
- After Task 4, Task 6 may proceed alongside Task 5 if interfaces in `resolved-task.json` are frozen first.
- Tasks 5 and 7 should remain sequential because both change artifact ownership and verification scope.
- Task 9 is sequential and starts only after all foundation gates pass.

## Effort And Checkpoints

| Checkpoint | Tasks | Estimate | Decision |
|---|---|---:|---|
| C1 Contract | 1-3 | 2-3 engineer days | Confirm all P1 cases are executable red tests |
| C2 Compiler/run foundation | 4-5 | 4-6 engineer days | Confirm stable manifest and concurrent isolation |
| C3 Trust boundary | 6-8 | 4-6 engineer days | Confirm factual output and fail-closed behavior |
| C4 Evidence | 9 | 3-5 elapsed days | Decide Beta prerelease from real user evidence |

Total engineering estimate: 10-15 focused engineer days, plus tester scheduling. Estimates exclude provider outages and acquisition of licensed second-brand assets.

## Explicitly Deferred

- Authentication, tenancy, database, queue, hosted API, Web UI, approvals, and collaboration.
- SLOs, autoscaling, production observability, schema migration framework, and package-index publication.
- New channels/templates beyond what is necessary for two-brand Beta evidence.
- Performance work other than removing duplicate Chromium startup and exact background regeneration after correctness is proven.

## Final Acceptance Checklist

- [ ] Fresh clone tests pass before any build.
- [ ] Offline mode performs zero network/provider calls.
- [ ] Every declared target produces a manifest entry and artifact; zero work fails.
- [ ] Every objective text or visual claim resolves to an existing product fact and evidence file.
- [ ] Browser/provider/channel errors return non-zero with actionable diagnostics.
- [ ] Historical campaigns cannot affect the current run.
- [ ] Two concurrent campaigns cannot overwrite each other.
- [ ] Two genuinely different brands and four campaigns pass without Python edits.
- [ ] Primary and backup non-author acceptance evidence is recorded.
- [ ] Only after all items pass is a Beta prerelease allowed.
