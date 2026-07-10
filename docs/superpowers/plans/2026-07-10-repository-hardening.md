# ShadowRocket Repository Hardening Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Preserve weekly/manual public rule publication while isolating untrusted build inputs, archiving XKeen privately, making release generation safe and reproducible, and enforcing the behavior in tests.

**Architecture:** Public data feeds remain floating, but executable GitHub Actions and V2Fly compiler sources are pinned to reviewed immutable commits. A read-only build job produces a path-limited artifact; a separate publish job owns write credentials. Local generators use staged outputs and validation before replacing tracked artifacts.

**Tech Stack:** Python 3.11 standard library, `unittest`, GitHub Actions YAML, Go 1.22 compiler projects pinned by Git commit.

---

### Task 1: Archive and remove the public XKeen pipeline

**Files:**
- Create: `../ShadowRocket_private/XKeen/archive/legacy-generator-2026-07-10/README.md`
- Create: `../ShadowRocket_private/XKeen/archive/legacy-generator-2026-07-10/scripts/build_xkeen_local.py`
- Create: `../ShadowRocket_private/XKeen/archive/legacy-generator-2026-07-10/scripts/build_clash_config.py`
- Create: `../ShadowRocket_private/XKeen/archive/legacy-generator-2026-07-10/tests/test_build_xkeen_local.py`
- Delete: `XKeen/README.md`
- Delete: `XKeen/example/02_dns.json`
- Delete: `XKeen/local/.gitkeep`
- Delete: `scripts/build_xkeen_local.py`
- Delete: `tests/test_build_xkeen_local.py`

- [ ] Copy the exact public generator, dependency and tests into the dated private archive.
- [ ] Add an archive README declaring `deprecated / unsupported`, documenting `python3 -m unittest discover -s tests -v`, and pointing runtime data to the existing private `XKeen/` folders.
- [ ] Run the archived tests from the archive root; expect all legacy XKeen tests to pass.
- [ ] Remove the public XKeen files with `apply_patch` and verify `rg -n 'XKeen|xkeen' README.md AGENTS.md .github scripts tests` only reports intentional historical design/plan text.
- [ ] Run public tests; expect the remaining suite to pass.

### Task 2: Add upstream payload and summary guards with TDD

**Files:**
- Create: `scripts/validate_distillate.py`
- Create: `tests/test_validate_distillate.py`
- Create: `tests/test_sync_lists.py`
- Modify: `scripts/build_distillate.py`
- Modify: `scripts/sync_lists.py`

- [ ] Add failing tests proving `fetch_text()` rejects non-HTTPS URLs, empty UTF-8 payloads and bodies larger than `64 * 1024 * 1024` bytes.
- [ ] Run `python3 -m unittest tests.test_sync_lists -v`; expect failures because size/scheme/content guards do not exist.
- [ ] Implement bounded streaming reads in `fetch_text()` and raise `DistillateError` before returning invalid payloads.
- [ ] Re-run the sync tests; expect pass.
- [ ] Add failing tests for `validate_summary_delta(previous, current, allow_large_diff=False)` covering a 40% allowed drop, a greater-than-40% rejected drop, a 100% allowed growth, a greater-than-100% rejected growth, empty required categories, and manual large-diff override.
- [ ] Run `python3 -m unittest tests.test_validate_distillate -v`; expect import/function failures.
- [ ] Implement `scripts/validate_distillate.py` with a CLI accepting `--previous`, `--current`, and `--allow-large-diff`; parser validity and non-empty requirements remain mandatory when override is set.
- [ ] Re-run validation tests; expect pass.

### Task 3: Make distillate generation staged and pin compiler code

**Files:**
- Modify: `scripts/build_distillate.py`
- Create: `tests/test_build_distillate.py`

Pinned compiler commits:

- `v2fly/domain-list-community`: `bb622a2b75b3dfbec83719c1eb6e748720ea698e`
- `v2fly/geoip`: `fbeec6d51a544ba4c19d75cf04260f74c965fbd7`

- [ ] Add a failing test that injects a category-build failure after staging starts and asserts the original `distillate/text`, `distillate/dat`, generated rules and modules are byte-identical.
- [ ] Add a failing test that checks compiler checkout commands include the exact reviewed commit SHA rather than executing repository HEAD.
- [ ] Run `python3 -m unittest tests.test_build_distillate -v`; expect failures against the current destructive implementation.
- [ ] Split the current implementation into `_build_distillate_in_place()` and a public `build_distillate()` that copies required inputs into a temporary staging root, builds there, then publishes only generated paths.
- [ ] Implement a transactional publisher that backs up destinations, uses same-filesystem temporary replacements, removes obsolete anti-ad chunks, and restores backups if publication raises.
- [ ] Clone compiler repositories with `--no-checkout`, checkout the exact constants above, then run their existing Go build commands.
- [ ] Re-run focused tests and the complete suite; expect pass.
- [ ] Perform a cached `--skip-compiled` rebuild in a temporary git archive and compare text, summary, rule and module outputs to HEAD.

### Task 4: Fix HAPP stamp and public whitelist portability with TDD

**Files:**
- Modify: `scripts/build_happ_routing.py`
- Create: `tests/test_build_happ_routing.py`
- Modify: `shadowrocket_whitelist.conf`
- Modify: `tests/test_shadowrocket_whitelist_config.py`

- [ ] Add a failing HAPP test: with an existing `DEFAULT.JSON` and no explicit stamp, rebuilding preserves its `LastUpdated` in JSON and deeplink.
- [ ] Add a second failing/confirming test: explicit `--build-stamp` replaces the stored value.
- [ ] Run the focused HAPP tests; expect the preservation test to fail because HEAD timestamp is currently substituted.
- [ ] Implement `existing_build_stamp(out_dir)` and resolve the stamp in order: explicit argument, existing JSON value, git timestamp fallback.
- [ ] Add a failing whitelist test that rejects `GERMANY(Y)` and requires `PROXY = select,policy-regex-filter=WL`.
- [ ] Run it and confirm failure against the personal node name.
- [ ] Replace the public group definition with the portable WL filter and run all profile tests.

### Task 5: Isolate weekly build and publish credentials

**Files:**
- Modify: `.github/workflows/sync-lists.yml`
- Modify: `.github/workflows/build-happ-routing.yml`
- Create: `tests/test_workflows.py`

Immutable Action pins:

- `actions/checkout`: `34e114876b0b11c390a56381ad16ebd13914f8d5` (`v4`)
- `actions/setup-python`: `a26af69be951a213d495a4c3e4e4022e16d87065` (`v5`)
- `actions/setup-go`: `40f1582b2485089dde7abd97c1529aa768e1baff` (`v5`)
- `actions/upload-artifact`: `ea165f8d65b6e75b540449e92b4886f43607fa02` (`v4`)
- `actions/download-artifact`: `d3f86a106a0bac45b974a628896c90dbdf5c8093` (`v4`)

- [ ] Add failing text-structure tests requiring: pinned Action SHAs, `workflow_dispatch.inputs.allow_large_diff`, `concurrency`, read-only build permissions, `persist-credentials: false`, test execution before upload, a separate write-only publish job, explicit artifact paths, changed-path allowlist, and a no-checkout issue notification job.
- [ ] Run `python3 -m unittest tests.test_workflows -v`; expect failures against current single-job workflows.
- [ ] Rewrite `sync-lists.yml` into `build`, `publish`, and `notify` jobs. Preserve weekly cron and manual dispatch. Build uploads only `distillate/**`, generated `rules/*.list`, `modules/anti_advertising*.module`, `clash_config.yaml`, and `HAPP/DEFAULT.*`.
- [ ] Make publish use a fresh checkout, download only the named artifact, reject changed paths outside the allowlist, and push the bot commit.
- [ ] Make notify create a GitHub issue containing the failed run URL using `gh api`; it receives only `issues: write` and does not checkout code.
- [ ] Convert `build-happ-routing.yml` to a read-only verification workflow that runs tests and fails on generated drift instead of writing commits, preventing competing publishers.
- [ ] Re-run workflow structure tests; expect pass.

### Task 6: Synchronize public documentation

**Files:**
- Modify: `README.md`
- Modify: `AGENTS.md`
- Modify: `XKeen` references in tracked docs where they describe current behavior

- [ ] Remove current-support references to XKeen and nonexistent generated/manual files.
- [ ] Document the WL selection step for the emergency profile.
- [ ] Document weekly auto-publish, manual rebuild, delta guard override and anomaly issues.
- [ ] Replace the statement that tests are absent with the exact unittest/compileall commands.
- [ ] Run `rg` checks for public absolute `/Users/sergio` paths, personal node names and stale XKeen operational instructions; expect no current-support matches.

### Task 7: Full verification and review

**Files:**
- Verify all modified files.

- [ ] Run `python3 -m unittest discover -s tests -v`; expect zero failures.
- [ ] Run `python3 -m compileall -q scripts tests`; expect exit 0.
- [ ] Run cached deterministic rebuild checks for distillate, Clash and HAPP; expect no unexpected diff.
- [ ] Run `git diff --check` and inspect `git diff --stat` plus the full diff.
- [ ] Run a sensitive-marker scan over tracked content and confirm private subscriptions, credentials and absolute user paths are absent.
- [ ] Perform a final code review against `docs/superpowers/specs/2026-07-10-repository-hardening-design.md` and fix any P0/P1 regressions before completion.
- [ ] Create logical local commits using the repository `commit-line` contract; do not push.
