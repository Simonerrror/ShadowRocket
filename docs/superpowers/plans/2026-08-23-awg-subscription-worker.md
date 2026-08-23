# Private AWG Subscription Worker Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build two private Shadowrocket subscription URLs, each backed by exactly five independent AmneziaWG 2.0 device profiles and replaced as one complete set.

**Architecture:** A local Python generator converts two ignored directories of five native AWG2 `.conf` files into a mode-`0600` JSON payload for Cloudflare Worker secrets. Each generated link occupies its own secret to remain below Cloudflare's 5 KB per-variable limit. A separate neutral Worker named `potato-box` maps two opaque secret paths to two plain-text subscriptions assembled at request time; neither credentials, generated links, owner names, nor subscription URLs are committed.

**Tech Stack:** Python 3 standard library, Cloudflare Workers JavaScript, Node test runner, Wrangler 4.114.0.

---

## Verification portfolio

| Category | Capability or risk | Primary proof | Why this level |
|---|---|---|---|
| Behavior | Five AWG2 configs become five importable `wg://` lines per owner | Python integration test over realistic temporary config directories | Exercises parsing, naming, URL encoding, and final payload together |
| Security | Secrets and bearer paths never enter tracked artifacts or error output | Generator rejection tests plus ignored-output contract | Owns the boundary before Cloudflare upload |
| Integrity | Wrong count, duplicate device keys, placeholders, and AWG3 fields fail closed | Table-driven generator test | Prevents partial or silently incompatible subscriptions |
| HTTP contract | Only the two exact secret paths serve feeds; unknown paths reveal nothing | Node Worker integration test | Exercises the deployed request boundary |
| Deployment | Exact dependency, dry-run bundle, and authenticated Worker deployment | Wrangler dry run and production smoke request | Proves Cloudflare accepts the artifact and serves no indexed directory |

### Task 1: Local AWG2 subscription generator

**Files:**
- Create: `scripts/build_private_awg_subscriptions.py`
- Create: `tests/test_build_private_awg_subscriptions.py`
- Modify: `.gitignore`

**Risk/capability:** Exactly five unique device configs per owner become complete Shadowrocket links; malformed input produces no replacement output.

**Primary proof:** One integration test builds both owner feeds and decodes every URL; one table-driven rejection test owns all fail-closed validation.

- [ ] Write tests that create ten realistic AWG2 configs with synthetic 32-byte keys, invoke `build_secret_payload()`, and require five newline-terminated `wg://` entries in each feed plus stable opaque paths.
- [ ] Run `python3 -m unittest tests/test_build_private_awg_subscriptions.py -v` and confirm failure because the module is absent.
- [ ] Implement strict `[Interface]`/`[Peer]` parsing, required AWG2 fields, placeholder rejection, AWG3 rejection, unique private-key enforcement across both owners, filename-derived country labels, URL-safe JSON `obfsParam`, atomic mode-`0600` output, and path reuse from an existing payload.
- [ ] Add `private/` to `.gitignore`; the default output is `private/awg/worker-secrets.json` and the default input directories are `private/awg/primary` and `private/awg/secondary`.
- [ ] Re-run the focused tests and confirm they pass.

### Task 2: Neutral two-feed Worker

**Files:**
- Create: `cloudflare/potato-box/src/worker.js`
- Create: `cloudflare/potato-box/test/worker.test.mjs`
- Create: `cloudflare/potato-box/wrangler.jsonc`
- Create: `cloudflare/potato-box/package.json`
- Create: `cloudflare/potato-box/package-lock.json`

**Risk/capability:** Only exact bearer paths return subscriptions and no route enumeration, caching, referrer, or unsupported method exposes them.

**Primary proof:** Node integration tests call the exported Worker with synthetic secrets and verify GET/HEAD, 404, 405, missing-secret, and security-header behavior.

- [ ] Write Worker tests requiring exact path matching, plain-text feeds, empty HEAD bodies, `no-store`, `no-referrer`, `nosniff`, `noindex`, generic 404s, and 405 responses.
- [ ] Run `node --test cloudflare/potato-box/test/*.test.mjs` and confirm failure because the Worker is absent.
- [ ] Implement a dependency-free module Worker using two secret paths and ten individual link secrets; never log or echo secret values.
- [ ] Pin Wrangler to the already reviewed exact `4.114.0` version and set compatibility date `2026-08-23`.
- [ ] Re-run the Worker tests and confirm they pass.

### Task 3: Operator workflow and deployment proof

**Files:**
- Create: `cloudflare/potato-box/README.md`
- Create: `.github/workflows/deploy-potato-box.yml`
- Modify: `tests/test_workflows.py`

**Risk/capability:** Code deploys reproducibly while generated credentials stay local; rotating either batch replaces the complete deployed feed.

**Primary proof:** Workflow contract test plus local full suite, compile check, dependency audit, and Wrangler dry run.

- [ ] Add a workflow test requiring immutable action pins, `npm ci --ignore-scripts`, tests before deploy, read-only repository permissions, and no subscription payload in workflow inputs.
- [ ] Run the focused workflow test and confirm it fails because the workflow is absent.
- [ ] Add the deployment workflow and an operator README with the exact sequence: place five files in each ignored directory, build payload, deploy code, bulk-upload secrets, retrieve two URLs locally, and rotate by rebuilding and bulk-uploading the complete payload.
- [ ] Run `python3 -m unittest discover -s tests -v`, `python3 -m compileall -q scripts tests`, `npm test --prefix cloudflare/potato-box`, `npm audit --omit=dev --prefix cloudflare/potato-box`, and `npm run deploy:dry --prefix cloudflare/potato-box`.
- [ ] Inspect `git diff`, `git status --short`, and `git ls-files` to prove no `.conf`, generated `wg://`, secret JSON, or bearer URL is tracked.
