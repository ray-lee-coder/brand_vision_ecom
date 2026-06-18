# BrandKit Beta Reassessment

> Date: 2026-06-18
> Reviewed range: `3093c07..f754cbb`
> Target: reliable Beta for personal and small-team use
> Decision: **NOT CLEARED for Beta release**
> Review mode: gstack `/review` checklist plus goal-alignment and executable-gate audit
> gstack installation: **VERIFIED FOR CODEX SKILLS** (`v1.29.0.0`, commit `0660547`; generated `~/.codex/skills/gstack-*` links resolve). A global `gstack` command is not the Codex installation interface; skills such as `/review` are the interface.

## Current Result

Recovery R1-R4 and the automated portion of R5 are complete in the current working tree. The remaining Beta release blocker is real non-author acceptance; production hardening remains intentionally deferred.

| Gate | Result | Evidence |
|---|---|---|
| Stage 1: executable contract | **PASS locally** | Full suite has no expected failures; final command evidence is recorded below |
| Stage 2: Beta foundation | **PASS locally** | Run-scoped manifests, active contracts, fail-closed verification, and offline builds are covered |
| Stage 3: usage evidence | **PARTIAL** | Second brand and 5/5 automated modification trials exist; named non-author acceptance is pending |

## Product Plan Assessment

The product boundary is now correct: prove a useful and reliable personal/small-team Beta before production engineering. The four-layer source-based CLI shape remains appropriate, and production tenancy, services, databases, workflow UI, and collaboration remain deferred.

The plan itself is not yet an executable source of truth:

1. **[P1] (confidence 10/10) `PRODUCT-PLAN.md:538-543` and `docs/superpowers/plans/2026-06-18-beta-reliability.md:579-587`** - the Beta estimate is simultaneously 4-6 and 10-15 focused engineer days. Scheduling and release expectations cannot be trusted until one estimate governs both files.
2. **[P1] (confidence 10/10) `docs/superpowers/plans/2026-06-18-beta-reliability.md:51-556`** - every task checkbox remains open, while commits claim Tasks 4-8 complete. The plan has no verified/current status column, so commit messages can substitute for gate evidence.
3. **[P1] (confidence 9/10) `docs/superpowers/plans/2026-06-18-beta-reliability.md:228-500`** - completion is described mainly as file edits and focused tests. It does not require the real `brandkit build` and `build-all` paths to pass after each workstream, which allowed Stage 2 to be declared complete while both commands fail.
4. **[P2] (confidence 10/10) `PRODUCT-PLAN.md:390-508`** - M0-M3 exit checklists remain unverified while the header calls the Alpha implementation complete. These milestones may describe component history, but only the Beta gates may describe release readiness.

## Historical Baseline Findings

The findings in this section describe the reviewed baseline and are superseded where the later Recovery sections record a verified fix. They are retained for audit traceability.

1. **[P1] (confidence 10/10) `scripts/compile.py:204-210`** - schema validation results are discarded. `validate_document()` returns an error list, but the compiler neither checks the list nor calls `validate_document_or_raise`. A campaign with an unknown root field compiled successfully in the clean clone. The active compiler also does not validate brand, visual, content, product, or channel documents.

2. **[P1] (confidence 10/10) `scripts/run_context.py:24-33,105-111` and `scripts/compile.py:400-414`** - the claimed run isolation still writes shared `.build/` and `output/` paths. `run_id` is deterministic only from campaign and mode, the compiler always creates the default `offline` context, manifest errors are warnings, and the manifest records only compiled JSON files, not rendered artifacts or reports. Concurrent or repeated runs can overwrite each other.

3. **[P1] (confidence 10/10) `scripts/validate_channel.py:12-33,192-209,319-320`** - validation still uses hardcoded profiles and scans all output campaigns. It does not consume compiled channel YAML or a run manifest. A clean `brandkit build campaigns/618-launch.yaml --offline` returned exit 1 with four failed cross-channel checks, so the primary Beta path does not pass.

4. **[P1] (confidence 10/10) `scripts/verify.py:122-165,235-310`** - verification remains fail-open. Removing one provenance file produced an informational message and exit 0. Removing the campaign output produced `Visual: 0 passed, 0 failed`, `Content: 0 passed, 0 failed`, and exit 0. Artifact completeness is not enforced.

5. **[P1] (confidence 10/10) `scripts/verify.py:143-151`** - a claim passes when its `fact_ref` exists and the canonical evidence path exists, but the declared `source_ref` is not compared with the fact source and the claim value is not required to appear in the artifact. Provenance can therefore describe facts that the content did not render or name a false source.

6. **[P1] (confidence 10/10) `scripts/brandkit:15-25`** - `build-all --offline` crashes before building on the system Bash with `PASSTHROUGH[@]: unbound variable`. The corresponding test checks only output strings and never asserts a zero exit code, so the suite reports success.

7. **[P1] (confidence 10/10) `.github/workflows/test.yml:17`** - CI invokes `tests/fixtures/campaigns/acme-launch.yaml`, which does not exist. Both matrix jobs will fail even if pytest passes.

8. **[P1] (confidence 10/10) `docs/*.pdf`** - all seven evidence files are 32-43 byte ASCII files containing `Dummy evidence`. Existence checks now pass, but there is no product specification, lab report, certification, issuer, date, or traceable evidence. This converts a missing-evidence failure into a false evidence pass.

9. **[P1] (confidence 10/10) `templates/feature-grid.html:95-107` and `scripts/render_visual.py:133-144`** - visual claims remain hardcoded (`42dB`, `38h`, `285g`, `0.2s`), while `product_coverage` and `logo_position` remain hardcoded. Visual facts are still outside the product-fact contract.

10. **[P1] (confidence 9/10) `scripts/contracts.py:85-108`** - overrides are copied into every output target without field-to-target mapping. For example, `headline_max_chars` appears on visual targets and all content target types. This is an allowlist, not the planned explicit application policy.

11. **[P1] (confidence 10/10) Stage 3 files** - the second non-audio brand, two-brand fixtures, `docs/beta/acceptance-rubric.md`, `docs/beta/evidence-report.md`, measured baseline, and non-author trial are absent. No product-use evidence exists yet.

## Important Non-Blocking Findings

1. **[P2] (confidence 10/10) `tests/unit/test_contracts.py:233-244`** - the channel-contract test is still marked xfail and only asserts that the legacy result contains `channel`; it XPASSes without proving compiled rules are used.
2. **[P2] (confidence 10/10) `tests/integration/test_verification_fail_closed.py:20-33`** - the browser test passes a string where `verify_visual` expects a `Path`; it can pass because `.resolve()` raises, not because Chromium launch failure is handled correctly.
3. **[P2] (confidence 9/10) `scripts/copy_generator.py:161-187`** - JSON parsing is strict, but response shape is not. Missing/wrong `text` and malformed `claims` are not rejected at the provider boundary.
4. **[P2] (confidence 10/10) `scripts/background_generator.py:71-113`** - the default background prompt still hardcodes premium audio and urban professionals, so a second brand would inherit Aether styling.
5. **[P2] (confidence 10/10) `README.md:30,65,104` and `TEST-REPORT.md:4,141`** - documentation still advertises 9/10 tests and v0.3 Alpha behavior, while the CLI identifies itself as v0.4 Beta and the suite collects 21 tests.

## Verification Evidence

| Command/check | Result |
|---|---|
| Clean clone `python3 -m pytest -q` | `20 passed, 1 xpassed` |
| Clean clone offline single build | Exit 1 in channel validation |
| `brandkit build-all --offline` | Exit 1 before build: unbound empty array |
| Compile campaign with unknown root schema field | Exit 0; invalid field ignored |
| Verify after deleting one provenance file | Exit 0 |
| Verify with zero campaign artifacts | Exit 0 |
| Inspect `docs/*.pdf` | All are short dummy ASCII text, not PDFs |
| gstack Codex setup | `./setup --host codex` completed; runtime links and sidecars resolve |
| gstack regression suite | `453 passed, 0 failed` |

## Plan Completion Audit

| Task | Status | Reason |
|---|---|---|
| 1. Product status | DONE | Plan and milestone reports now say Beta is not cleared |
| 2. Hermetic tests/install | PARTIAL | Local clean tests run; E2E fixture is absent and CI is broken |
| 3. P1 red tests | PARTIAL | Several critical cases are absent or too weak to fail correctly |
| 4. Schemas/overrides | PARTIAL | Files exist, but active compilation does not enforce schemas and override targeting is wrong |
| 5. Run manifests/isolation | NOT DONE | Shared paths remain; manifest is incomplete and unused downstream |
| 6. Fact-bound rendering | PARTIAL | Some copy is brand-neutral; visual claims and background defaults remain hardcoded |
| 7. Fail-closed gates | PARTIAL | Some forged fact IDs block; missing provenance and zero checks still pass; channels remain hardcoded |
| 8. Provider/CLI contracts | PARTIAL | Some errors are explicit; response shape and build-all behavior remain broken |
| 9. Multi-brand evidence | NOT DONE | No second brand or human acceptance evidence |

## Goal-Aligned Recovery Order

1. Fix the test/CI truth layer: make XPASS strict or remove xfail after real fixes, add missing fixtures, assert CLI exit codes, and add missing-provenance/zero-artifact/schema/run-isolation tests.
2. Enforce contracts on the active compiler path: validate all six documents, reject unknown nested fields and path escape, and map each override to its permitted target fields.
3. Implement actual run directories and one manifest consumed by render, verify, and validate. Require one artifact per target and fail when checks are zero.
4. Replace dummy evidence with legitimate sample evidence or clearly licensed synthetic fixtures carrying issuer/date/method metadata. Compare claim text, value, `fact_ref`, and `source_ref` end to end.
5. Remove hardcoded product claims and audio styling from templates/background generation. Make channel validation derive only from compiled YAML.
6. Re-run the clean offline path on macOS and Ubuntu. Only after it passes, add the second brand and perform the non-author usability trial.

## Revised Work Plan

Work is accepted by gates, not by files changed or commit labels.

| Batch | Scope | Required evidence | Exit condition |
|---|---|---|---|
| R1 Truth layer | Fix Bash empty-array handling, CI fixture, strict xfail, schema-path tests, zero-artifact and missing-provenance tests | Full pytest has no XPASS/XFAIL; CI command exists; `build-all --offline` reaches children | Test suite fails for every remaining known P1 before implementation fixes |
| R2 Active contracts | Validate all six documents on the production compiler path; implement target-specific overrides; replace dummy evidence with declared synthetic fixtures or legitimate sample evidence | Invalid fixture matrix through `scripts/brandkit`; evidence metadata checks | No invalid spec or false evidence can compile |
| R3 Run ownership | Run-scoped build/output/report directories; one manifest passed through compile, render, verify, and validate | Ordered, repeated, and concurrent two-campaign tests with sentinels | No shared mutable campaign artifact paths; every target has one declared artifact |
| R4 Trust boundary | Fact-bound text and visual slots; source/value binding; compiled channel rules; strict provider response schema | Missing/forged provenance, unrelated fact ID, malformed provider and zero-output cases fail non-zero | Offline single build and `build-all` pass from a clean clone without network |
| R5 Product evidence | Second materially different brand, four campaigns, five modification tasks, non-author trial | Evidence report, hashes, call logs, edit/time records, acceptance rubric | All 11 Beta exit criteria pass; only then tag prerelease |

Required gate command set after every batch:

```bash
python3 -m pytest -q
bash scripts/brandkit build campaigns/618-launch.yaml --offline
bash scripts/brandkit build-all --offline
```

R3 and later must also run a clean-clone smoke test and the ordered/concurrent isolation suite. R5 must run in the macOS 14 and Ubuntu 24.04 CI matrix.

### Progress Recheck 2026-06-18 (`7dd02c7`)

| Batch | Verified status | Fresh evidence |
|---|---|---|
| R1 | PARTIAL | `23 passed, 1 xfailed`; the strict missing-provenance regression still fails as expected |
| R2 | PARTIAL | Active six-document schema checks exist; override targeting and evidence authenticity remain open |
| R3 | PARTIAL | `.build/manifest.json` contains only compiled JSON; downstream stages ignore it and shared paths remain |
| R4 | PARTIAL | Channel validator reports four failed dimensions but returns zero; hardcoded channel profiles and provider examples remain |
| R5 | PARTIAL | Acme adds a second fixture, not the required evidence report, five modification trials, or non-author acceptance |

Decision: continue R3 now. It is Beta correctness work, not production hardening. Do not start the R3 refactor under the assumption that it is the only remaining gap; after R3, close the explicit R1/R2/R4 gates before beginning real R5 acceptance.

### Progress Recheck 2026-06-18 (`794143f`)

| Batch | Verified status | Fresh evidence |
|---|---|---|
| R1 | DONE | Local and clean-clone suites both report `24 passed`; clean single build and local `build-all --offline` exit zero |
| R2 | PARTIAL | Six active schemas are enforced. `apply_overrides()` selects `target.type` before `content_type`, so content-specific overrides are not applied; evidence remains dummy ASCII text |
| R3 | PARTIAL | Render/verify append to campaign-named manifests, but `.build/resolved-task.json`, `.build/message-plan.json`, `.build/verify/*`, and deterministic campaign run IDs remain shared. Validator still scans every output campaign and guesses the first directory. No ordered or concurrent isolation test exists |
| R4 | PARTIAL | Template claim literals were reduced, but `background_generator.py` still defaults to premium audio/urban professionals and `validate_channel.py` still uses hardcoded `CHANNEL_PROFILES` instead of compiled channel YAML |
| R5 | PARTIAL | Acme is a useful second fixture. Required modification evidence, artifact hashes/call budgets, evidence report, and non-author rubric results are absent |

The CLI gates are green, but they do not prove R2-R5 completion because current tests do not exercise content override targeting, concurrent run isolation, compiled channel-rule validation, or human acceptance.

### Recovery Implementation 2026-06-18 (working tree after `794143f`)

| Batch | Status | Verification |
|---|---|---|
| R1 | DONE | `39 passed`; normal single build and all five offline campaigns exit zero |
| R2 | DONE | Six schemas remain on the active compiler path; content override targeting has direct regression coverage; product refs now use declared synthetic evidence fixtures with issuer/date/method/fact IDs |
| R3 | DONE | Every CLI build receives a unique run root. Compile, render, verify, and channel validation receive explicit paths and one manifest. Concurrent two-campaign and deleted-declared-artifact tests pass |
| R4 | DONE | Scene prompts preserve brand policy, default prompts and provider schema examples are brand-neutral, channel validation consumes the compiled contract, provider response shape is strict, and missing manifest artifacts fail closed |
| R5 | PARTIAL | Acme fixture and acceptance materials exist; 5/5 isolated offline modification trials now pass with hashes, boundaries, call counts, and timing. A named non-author result is still required |

Fresh evidence:

```text
pytest: 39 passed
single offline build: exit 0, 6 targets, 14 artifacts, 3 reports
build-all offline: exit 0, 5 campaign manifests
concurrent isolation: pass
manifest hash/path audit: pass (SHA-256, run-scoped)
```

Production tenancy, hosted services, databases, queues, authentication, and collaboration remain correctly deferred. None of those should be started before the remaining non-author Beta acceptance gate is satisfied.

### R5 Automated Evidence Closure 2026-06-18

`docs/beta/modification-evidence.json` records all five required Acme modifications. Each trial builds in an isolated workspace, compares normalized artifact hashes, checks the changed artifact category boundary, records elapsed time and the online call budget, and confirms zero actual model calls in offline mode. Result: **5 passed, 0 failed**.

This closes the automated R5 modification-evidence gap only. The release decision remains **NOT CLEARED** until `docs/beta/acceptance-rubric.md` contains a real named non-author result meeting the rubric thresholds. Online provider budgets also remain unverified by these offline trials.

Final local verification:

```text
project pytest: 41 passed, no warnings
clean-copy pytest: 41 passed, no warnings
single offline build: exit 0
build-all offline: exit 0, 5 campaigns
R5 modification trials: 5 passed, 0 failed
gstack full regression: exit 0
```

The final output audit also separates state from presentation: unmet cross-channel preferences remain non-blocking `Informational` findings and now render with `ℹ`, not the failure icon used by blocking file-validation errors.
