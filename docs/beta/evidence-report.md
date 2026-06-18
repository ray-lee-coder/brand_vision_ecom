# BrandKit Beta Evidence Report

> Status: **R6 LOCAL GATES COMPLETE; REMOTE CI AND R7 EVIDENCE PENDING**
> Recovery baseline commit: `e335f14`; final release SHA must be recorded after the R6 branch lands

## Automated Gates

| Gate | Evidence | Status |
|---|---|---|
| Test suite | Full pytest in the R6 worktree | 60 passed; clean-clone result recorded after candidate commit |
| Offline single build | `bash scripts/brandkit build campaigns/618-launch.yaml --offline` | PASS |
| Offline all campaigns | `bash scripts/brandkit build-all --offline` | PASS (5 campaigns) |
| Concurrent isolation | `tests/integration/test_run_isolation.py` | Automated |
| Provider response schema | `tests/unit/test_recovery_contracts.py` | Automated |
| Evidence fixtures | `docs/fixtures/evidence/*.yaml` | Synthetic test evidence only |

Synthetic fixtures prove contract behavior. They are not real product substantiation and must not be represented as such.

## Five Modification Trials

The automated runner uses isolated Acme workspaces and records before/after artifact hashes, changed boundaries, model-call counts, online budgets, and elapsed time in [`modification-evidence.json`](modification-evidence.json). These are offline contract trials, not human usability results or online-provider tests.

| Task | Expected boundary | Model-call budget | Evidence | Status |
|---|---|---:|---|---|
| Change brand primary color | Visual token outputs only | 0 | 2 visual changed; content unchanged | PASS (offline) |
| Change primary benefit | Message plan and affected copy | Copy only online | 2 content + 1 affected visual changed | PASS (offline) |
| Remove unsupported claim | Affected copy/provenance only | Copy only online | Xiaohongshu note + provenance changed | PASS (offline) |
| Change Tmall copy to Xiaohongshu | Channel content only | Copy only online | Content target/provenance changed; visuals unchanged | PASS (offline) |
| Replace visual background | Background artifact only | Exactly 1 image call online | Xiaohongshu lifestyle visual only changed | PASS (offline) |

## Human Acceptance

Use `docs/beta/acceptance-rubric.md`. Do not mark Beta cleared until the completed rubric identifies a real non-author tester and contains artifact-level scores and notes.

| Requirement | Evidence | Status |
|---|---|---|
| Non-author clean-clone onboarding | | PENDING |
| Four Acme artifacts scored | | PENDING |
| No factual/compliance defects | | PENDING |
| Practical usability threshold | | PENDING |

## Release Decision

**NOT CLEARED.** Local R6 gates and five automated modification trials pass, but the current candidate still needs remote Ubuntu/macOS CI. R7 must then cover PNG determinism, observed online call/error behavior, and named non-author product-use evidence on one fixed SHA.
