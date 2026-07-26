# Potato Link Worker Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Publish two neutral `workers.dev` links that open the generated HAPP default and RU profiles, with automatic redeployment after either deeplink changes.

**Architecture:** A Python build script validates both generated deeplinks and writes a small committed JavaScript data module. A dependency-free Cloudflare Worker maps `/` and `/ru` to those embedded destinations; a hardened GitHub Actions workflow verifies generated output and deploys it with repository secrets.

**Tech Stack:** Python 3.11 standard library, JavaScript Web APIs, Node.js 22.17.1 built-in test runner, Cloudflare Wrangler 4.114.0, GitHub Actions.

---

## File map

- Create `scripts/build_potato_link_worker.py`: validate both deeplinks and generate the embedded destination module.
- Create `tests/test_build_potato_link_worker.py`: unit tests for valid generation and malformed input rejection.
- Create `cloudflare/potato-link/src/worker.js`: request routing and redirect responses.
- Create `cloudflare/potato-link/dist/destinations.js`: committed generated deeplink constants.
- Create `cloudflare/potato-link/test/worker.test.mjs`: Worker behavior tests using Node Web APIs.
- Create `cloudflare/potato-link/wrangler.jsonc`: Worker name, entry point, compatibility date, and `workers.dev` publication.
- Create `cloudflare/potato-link/package.json`: exact Wrangler dependency and local scripts.
- Create `cloudflare/potato-link/package-lock.json`: deterministic npm dependency graph.
- Create `.github/workflows/deploy-potato-link.yml`: verification and deployment automation.
- Modify `tests/test_workflows.py`: enforce permissions, immutable actions, triggers, secret placement, and exact install behavior.
- Modify `.github/workflows/build-happ-routing.yml`: regenerate the embedded destinations during repository verification.
- Modify `.github/workflows/sync-lists.yml`: include the embedded destinations in the release candidate and published generated outputs.
- Modify `scripts/validate_publish_paths.py`: permit only the generated destination module as an additional publication output.
- Modify `HAPP/README.md`: document both clickable links after the real `workers.dev` hostname is known.

### Task 1: Generate embedded destinations

**Files:**
- Create: `tests/test_build_potato_link_worker.py`
- Create: `scripts/build_potato_link_worker.py`
- Create: `cloudflare/potato-link/dist/destinations.js`

- [ ] **Step 1: Write failing generator tests**

Create tests that import `build_module`, `read_deeplink`, and
`validate_deeplink`. Cover one trailing LF, the exact two exported keys,
multiline input, an incorrect scheme, invalid base64 characters, and a payload
over 16 KiB:

```python
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from scripts.build_potato_link_worker import (
    MAX_DEEPLINK_LENGTH,
    build_module,
    read_deeplink,
    validate_deeplink,
)


VALID_DEFAULT = "happ://routing/onadd/eyJOYW1lIjoiZGVmYXVsdCJ9"
VALID_RU = "happ://routing/onadd/eyJOYW1lIjoicnUifQ=="


class PotatoLinkBuildTests(unittest.TestCase):
    def test_build_module_embeds_both_destinations(self) -> None:
        module = build_module(VALID_DEFAULT, VALID_RU)
        self.assertIn(f'default: "{VALID_DEFAULT}"', module)
        self.assertIn(f'ru: "{VALID_RU}"', module)

    def test_read_deeplink_accepts_one_trailing_lf(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "profile.DEEPLINK"
            path.write_text(VALID_DEFAULT + "\n", encoding="utf-8")
            self.assertEqual(read_deeplink(path), VALID_DEFAULT)

    def test_rejects_multiline_input(self) -> None:
        with self.assertRaisesRegex(ValueError, "single line"):
            validate_deeplink(VALID_DEFAULT + "\n" + VALID_RU, Path("bad"))

    def test_rejects_unexpected_scheme(self) -> None:
        with self.assertRaisesRegex(ValueError, "prefix"):
            validate_deeplink("https://example.com/value", Path("bad"))

    def test_rejects_invalid_base64(self) -> None:
        with self.assertRaisesRegex(ValueError, "base64"):
            validate_deeplink("happ://routing/onadd/not-valid!", Path("bad"))

    def test_rejects_oversized_input(self) -> None:
        value = "happ://routing/onadd/" + ("A" * MAX_DEEPLINK_LENGTH)
        with self.assertRaisesRegex(ValueError, "16 KiB"):
            validate_deeplink(value, Path("bad"))
```

- [ ] **Step 2: Run the tests and verify RED**

Run:

```bash
python3 -m unittest tests/test_build_potato_link_worker.py -v
```

Expected: import failure because `scripts.build_potato_link_worker` does not
exist.

- [ ] **Step 3: Implement the minimal deterministic generator**

Implement:

```python
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT = REPO_ROOT / "HAPP/DEFAULT.DEEPLINK"
RU_INPUT = REPO_ROOT / "HAPP/RU-VPN.DEEPLINK"
DEFAULT_OUTPUT = REPO_ROOT / "cloudflare/potato-link/dist/destinations.js"
DEEPLINK_PREFIX = "happ://routing/onadd/"
MAX_DEEPLINK_LENGTH = 16 * 1024
BASE64_RE = re.compile(r"[A-Za-z0-9+/]+={0,2}")


def validate_deeplink(raw: str, path: Path) -> str:
    lines = raw.splitlines()
    if len(lines) != 1 or not lines[0]:
        raise ValueError(f"{path}: deeplink must be a single line")
    value = lines[0]
    if len(value) > MAX_DEEPLINK_LENGTH:
        raise ValueError(f"{path}: deeplink exceeds 16 KiB")
    if not value.startswith(DEEPLINK_PREFIX):
        raise ValueError(f"{path}: unexpected deeplink prefix")
    payload = value.removeprefix(DEEPLINK_PREFIX)
    if BASE64_RE.fullmatch(payload) is None:
        raise ValueError(f"{path}: invalid base64 payload")
    return value


def read_deeplink(path: Path) -> str:
    return validate_deeplink(path.read_text(encoding="utf-8"), path)


def build_module(default: str, ru: str) -> str:
    return (
        "// Generated by scripts/build_potato_link_worker.py; do not edit.\\n"
        "export const DESTINATIONS = Object.freeze({\\n"
        f"  default: {json.dumps(default)},\\n"
        f"  ru: {json.dumps(ru)},\\n"
        "});\\n"
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--default-input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--ru-input", type=Path, default=RU_INPUT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()

    output = build_module(
        read_deeplink(args.default_input),
        read_deeplink(args.ru_input),
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(output, encoding="utf-8", newline="\n")


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Generate output and verify GREEN**

Run:

```bash
python3 scripts/build_potato_link_worker.py
python3 -m unittest tests/test_build_potato_link_worker.py -v
git diff --check
```

Expected: six tests pass and `dist/destinations.js` contains distinct `default`
and `ru` constants.

- [ ] **Step 5: Commit the generator**

```bash
git add scripts/build_potato_link_worker.py tests/test_build_potato_link_worker.py cloudflare/potato-link/dist/destinations.js
git commit -m "feat: embed HAPP deeplink destinations"
```

### Task 2: Implement Worker routing

**Files:**
- Create: `cloudflare/potato-link/test/worker.test.mjs`
- Create: `cloudflare/potato-link/src/worker.js`

- [ ] **Step 1: Write failing Worker behavior tests**

Create a Node test file that imports the default Worker handler and checks:

```javascript
import assert from "node:assert/strict";
import test from "node:test";

import { DESTINATIONS } from "../dist/destinations.js";
import worker from "../src/worker.js";

async function request(path, method = "GET") {
  return worker.fetch(new Request(`https://potato-link.example${path}`, { method }));
}

test("root redirects to the default profile", async () => {
  const response = await request("/");
  assert.equal(response.status, 302);
  assert.equal(response.headers.get("location"), DESTINATIONS.default);
});

test("/ru redirects to the RU profile", async () => {
  const response = await request("/ru");
  assert.equal(response.status, 302);
  assert.equal(response.headers.get("location"), DESTINATIONS.ru);
  assert.notEqual(DESTINATIONS.ru, DESTINATIONS.default);
});

test("HEAD redirects without a body", async () => {
  const response = await request("/ru", "HEAD");
  assert.equal(response.status, 302);
  assert.equal(await response.text(), "");
});

test("redirects disable caching and referrers", async () => {
  const response = await request("/");
  assert.equal(response.headers.get("cache-control"), "no-store");
  assert.equal(response.headers.get("referrer-policy"), "no-referrer");
  assert.equal(response.headers.get("x-content-type-options"), "nosniff");
});

test("unknown paths return 404 without exposing a deeplink", async () => {
  const response = await request("/missing");
  assert.equal(response.status, 404);
  assert.doesNotMatch(await response.text(), /happ:/);
});

test("unsupported methods return 405 on a known path", async () => {
  const response = await request("/", "POST");
  assert.equal(response.status, 405);
  assert.equal(response.headers.get("allow"), "GET, HEAD");
});
```

- [ ] **Step 2: Run the tests and verify RED**

Run:

```bash
node --test cloudflare/potato-link/test/worker.test.mjs
```

Expected: module-not-found failure for `src/worker.js`.

- [ ] **Step 3: Implement the minimal Worker**

Create:

```javascript
import { DESTINATIONS } from "../dist/destinations.js";

const PATHS = new Map([
  ["/", DESTINATIONS.default],
  ["/ru", DESTINATIONS.ru],
]);

const TEXT_HEADERS = {
  "content-type": "text/plain; charset=utf-8",
  "x-content-type-options": "nosniff",
};

export default {
  fetch(request) {
    const destination = PATHS.get(new URL(request.url).pathname);
    if (destination === undefined) {
      return new Response("Not found\n", {
        status: 404,
        headers: TEXT_HEADERS,
      });
    }
    if (request.method !== "GET" && request.method !== "HEAD") {
      return new Response("Method not allowed\n", {
        status: 405,
        headers: {
          ...TEXT_HEADERS,
          allow: "GET, HEAD",
        },
      });
    }
    return new Response(null, {
      status: 302,
      headers: {
        location: destination,
        "cache-control": "no-store",
        "referrer-policy": "no-referrer",
        "x-content-type-options": "nosniff",
      },
    });
  },
};
```

- [ ] **Step 4: Run Worker and repository tests**

Run:

```bash
node --test cloudflare/potato-link/test/worker.test.mjs
python3 -m unittest discover -s tests -v
```

Expected: six Node tests and all Python tests pass.

- [ ] **Step 5: Commit Worker behavior**

```bash
git add cloudflare/potato-link/src/worker.js cloudflare/potato-link/test/worker.test.mjs
git commit -m "feat: redirect both HAPP profile links"
```

### Task 3: Add pinned Wrangler tooling and validate the bundle

**Files:**
- Create: `cloudflare/potato-link/package.json`
- Create: `cloudflare/potato-link/package-lock.json`
- Create: `cloudflare/potato-link/wrangler.jsonc`

- [ ] **Step 1: Quarantine Wrangler without executing it**

Confirm `wrangler@4.114.0` resolves to the official
`cloudflare/workers-sdk` repository, record its npm integrity/signature
metadata, download the tarball into a temporary directory, inspect its
`package.json` lifecycle scripts and file list, and do not execute package
scripts.

- [ ] **Step 2: Add exact package and Worker configuration**

Create a private ESM package with scripts:

```json
{
  "name": "potato-link-worker",
  "private": true,
  "type": "module",
  "scripts": {
    "test": "node --test test/*.test.mjs",
    "deploy": "wrangler deploy",
    "deploy:dry": "wrangler deploy --dry-run"
  },
  "devDependencies": {
    "wrangler": "4.114.0"
  }
}
```

Create `wrangler.jsonc`:

```jsonc
{
  "$schema": "./node_modules/wrangler/config-schema.json",
  "name": "potato-link",
  "main": "src/worker.js",
  "compatibility_date": "2026-07-26",
  "workers_dev": true
}
```

- [ ] **Step 3: Produce and inspect the lockfile**

Run:

```bash
npm install --package-lock-only --ignore-scripts --prefix cloudflare/potato-link
npm ci --ignore-scripts --prefix cloudflare/potato-link
npm audit --omit=dev --prefix cloudflare/potato-link
```

Expected: an exact lockfile is created, no lifecycle scripts run, and the
production audit has no vulnerabilities.

- [ ] **Step 4: Verify tests and Wrangler dry-run**

Run:

```bash
npm test --prefix cloudflare/potato-link
npm run deploy:dry --prefix cloudflare/potato-link
```

Expected: tests pass and Wrangler reports a successful dry-run for
`potato-link` without deploying.

- [ ] **Step 5: Commit pinned tooling**

```bash
git add cloudflare/potato-link/package.json cloudflare/potato-link/package-lock.json cloudflare/potato-link/wrangler.jsonc
git commit -m "build: pin potato-link Worker tooling"
```

### Task 4: Add hardened automatic deployment

**Files:**
- Modify: `tests/test_workflows.py`
- Create: `.github/workflows/deploy-potato-link.yml`
- Modify: `.github/workflows/build-happ-routing.yml`
- Modify: `.github/workflows/sync-lists.yml`
- Modify: `scripts/validate_publish_paths.py`

- [ ] **Step 1: Write failing workflow hardening tests**

Add `DEPLOY_WORKFLOW` and the setup-node pin:

```python
DEPLOY_WORKFLOW = REPO_ROOT / ".github/workflows/deploy-potato-link.yml"

ACTION_PINS = (
    "actions/checkout@34e114876b0b11c390a56381ad16ebd13914f8d5",
    "actions/setup-python@a26af69be951a213d495a4c3e4e4022e16d87065",
    "actions/setup-go@40f1582b2485089dde7abd97c1529aa768e1baff",
    "actions/upload-artifact@ea165f8d65b6e75b540449e92b4886f43607fa02",
    "actions/download-artifact@d3f86a106a0bac45b974a628896c90dbdf5c8093",
    "actions/setup-node@48b55a011bda9f5d6aeb4c2d9c7362e8dae4041e",
)
```

Add focused tests:

```python
def test_potato_link_workflow_is_pinned_and_read_only(self) -> None:
    content = DEPLOY_WORKFLOW.read_text(encoding="utf-8")
    self.assertIn(
        "actions/checkout@34e114876b0b11c390a56381ad16ebd13914f8d5",
        content,
    )
    self.assertIn(
        "actions/setup-python@a26af69be951a213d495a4c3e4e4022e16d87065",
        content,
    )
    self.assertIn(
        "actions/setup-node@48b55a011bda9f5d6aeb4c2d9c7362e8dae4041e",
        content,
    )
    self.assertIn('node-version: "22.17.1"', content)
    self.assertIn("permissions:\n  contents: read", content)
    self.assertIn("persist-credentials: false", content)
    self.assertNotRegex(content, r"uses: actions/[^@]+@v\\d")

def test_potato_link_workflow_verifies_before_trusted_deploy(self) -> None:
    content = DEPLOY_WORKFLOW.read_text(encoding="utf-8")
    verify = content.split("  verify:", 1)[1].split("  deploy:", 1)[0]
    deploy = content.split("  deploy:", 1)[1]
    for required in (
        "push:",
        "pull_request:",
        "workflow_dispatch:",
        "workflow_run:",
        'workflows: ["Sync rule lists"]',
        "npm ci --ignore-scripts",
        "python3 scripts/build_potato_link_worker.py",
        "git diff --exit-code",
        "npm run deploy:dry",
    ):
        self.assertIn(required, content)
    self.assertNotIn("CLOUDFLARE_API_TOKEN", verify)
    self.assertIn("needs: verify", deploy)
    self.assertIn("github.event.workflow_run.conclusion == 'success'", deploy)
    self.assertIn("github.ref == 'refs/heads/main'", deploy)
    self.assertIn("CLOUDFLARE_API_TOKEN: ${{ secrets.CLOUDFLARE_API_TOKEN }}", deploy)
    self.assertIn("CLOUDFLARE_ACCOUNT_ID: ${{ secrets.CLOUDFLARE_ACCOUNT_ID }}", deploy)

def test_release_workflows_regenerate_embedded_destinations(self) -> None:
    sync = SYNC_WORKFLOW.read_text(encoding="utf-8")
    verify = VERIFY_WORKFLOW.read_text(encoding="utf-8")
    generated = "cloudflare/potato-link/dist/destinations.js"
    self.assertIn("python3 scripts/build_potato_link_worker.py", sync)
    self.assertIn("python3 scripts/build_potato_link_worker.py", verify)
    self.assertIn(generated, sync)
    self.assertTrue(is_allowed_publish_path(generated))
```

These tests require:

- `actions/checkout@34e114876b0b11c390a56381ad16ebd13914f8d5`;
- `actions/setup-python@a26af69be951a213d495a4c3e4e4022e16d87065`;
- `actions/setup-node@48b55a011bda9f5d6aeb4c2d9c7362e8dae4041e`
  (`v6.4.0`);
- exact `node-version: "22.17.1"`;
- `npm ci --ignore-scripts`;
- `workflow_run` after successful `Sync rule lists`, plus `push`,
  `pull_request`, and `workflow_dispatch`;
- no Cloudflare secrets in the verification job;
- deployment only from trusted `main` events;
- regeneration plus `git diff --exit-code`;
- the embedded destination module in the publication allowlist and weekly
  release artifact.

- [ ] **Step 2: Run workflow tests and verify RED**

Run:

```bash
python3 -m unittest tests/test_workflows.py -v
```

Expected: failures because the deployment workflow and publication allowance
do not exist.

- [ ] **Step 3: Implement the deployment workflow**

Create:

```yaml
name: Deploy potato link

on:
  workflow_dispatch:
  push:
    branches: [main]
    paths:
      - "HAPP/DEFAULT.DEEPLINK"
      - "HAPP/RU-VPN.DEEPLINK"
      - "cloudflare/potato-link/**"
      - "scripts/build_potato_link_worker.py"
      - "tests/test_build_potato_link_worker.py"
      - "tests/test_workflows.py"
      - ".github/workflows/deploy-potato-link.yml"
  pull_request:
    paths:
      - "HAPP/DEFAULT.DEEPLINK"
      - "HAPP/RU-VPN.DEEPLINK"
      - "cloudflare/potato-link/**"
      - "scripts/build_potato_link_worker.py"
      - "tests/test_build_potato_link_worker.py"
      - "tests/test_workflows.py"
      - ".github/workflows/deploy-potato-link.yml"
  workflow_run:
    workflows: ["Sync rule lists"]
    types: [completed]
    branches: [main]

permissions:
  contents: read

concurrency:
  group: potato-link-production
  cancel-in-progress: false

jobs:
  verify:
    if: >-
      github.event_name != 'workflow_run' ||
      github.event.workflow_run.conclusion == 'success'
    runs-on: ubuntu-latest
    steps:
      - name: Checkout repository without persisted credentials
        uses: actions/checkout@34e114876b0b11c390a56381ad16ebd13914f8d5 # v4
        with:
          persist-credentials: false

      - name: Set up Python
        uses: actions/setup-python@a26af69be951a213d495a4c3e4e4022e16d87065 # v5
        with:
          python-version: "3.11"

      - name: Set up Node
        uses: actions/setup-node@48b55a011bda9f5d6aeb4c2d9c7362e8dae4041e # v6.4.0
        with:
          node-version: "22.17.1"
          cache: npm
          cache-dependency-path: cloudflare/potato-link/package-lock.json

      - name: Install exact Worker dependencies
        run: npm ci --ignore-scripts --prefix cloudflare/potato-link

      - name: Rebuild embedded destinations
        run: python3 scripts/build_potato_link_worker.py

      - name: Verify generated destinations are current
        run: git diff --exit-code

      - name: Run generator tests
        run: python3 -m unittest tests/test_build_potato_link_worker.py -v

      - name: Run Worker tests
        run: npm test --prefix cloudflare/potato-link

      - name: Validate Worker bundle
        run: npm run deploy:dry --prefix cloudflare/potato-link

  deploy:
    needs: verify
    if: >-
      (github.event_name == 'push' && github.ref == 'refs/heads/main') ||
      (github.event_name == 'workflow_dispatch' && github.ref == 'refs/heads/main') ||
      (github.event_name == 'workflow_run' &&
       github.event.workflow_run.conclusion == 'success' &&
       github.event.workflow_run.head_branch == 'main')
    runs-on: ubuntu-latest
    steps:
      - name: Checkout trusted main
        uses: actions/checkout@34e114876b0b11c390a56381ad16ebd13914f8d5 # v4
        with:
          ref: main
          persist-credentials: false

      - name: Set up Node
        uses: actions/setup-node@48b55a011bda9f5d6aeb4c2d9c7362e8dae4041e # v6.4.0
        with:
          node-version: "22.17.1"
          cache: npm
          cache-dependency-path: cloudflare/potato-link/package-lock.json

      - name: Install exact Worker dependencies
        run: npm ci --ignore-scripts --prefix cloudflare/potato-link

      - name: Deploy Worker
        env:
          CLOUDFLARE_API_TOKEN: ${{ secrets.CLOUDFLARE_API_TOKEN }}
          CLOUDFLARE_ACCOUNT_ID: ${{ secrets.CLOUDFLARE_ACCOUNT_ID }}
        run: npm run deploy --prefix cloudflare/potato-link
```

- [ ] **Step 4: Integrate generation with existing release workflows**

Run `python3 scripts/build_potato_link_worker.py` after HAPP generation in the
verification and weekly sync builds. Carry
`cloudflare/potato-link/dist/destinations.js` in the release artifact, publish
it alongside the HAPP files, and allow that exact generated path in
`scripts/validate_publish_paths.py` by adding:

```python
GENERATED_FILES = {
    "clash_config.yaml",
    "distillate/summary.json",
    "HAPP/DEFAULT.JSON",
    "HAPP/DEFAULT.DEEPLINK",
    "HAPP/RU-VPN.JSON",
    "HAPP/RU-VPN.DEEPLINK",
    "cloudflare/potato-link/dist/destinations.js",
    *GENERATED_RULES,
    *GENERATED_MODULES,
}
```

Add this exact path to the artifact `path:` list, the publication copy tuple,
and `git add -A` arguments in `sync-lists.yml`. Add:

```yaml
- name: Build embedded Worker destinations
  run: python3 scripts/build_potato_link_worker.py
```

immediately after each `Build HAPP artifacts` step.

- [ ] **Step 5: Verify workflow hardening and all tests**

Run:

```bash
python3 -m unittest tests/test_workflows.py -v
python3 -m unittest discover -s tests -v
npm test --prefix cloudflare/potato-link
git diff --check
```

Expected: all tests pass, actions are pinned, and no secret is exposed to pull
request verification.

- [ ] **Step 6: Commit automation**

```bash
git add .github/workflows/deploy-potato-link.yml .github/workflows/build-happ-routing.yml .github/workflows/sync-lists.yml scripts/validate_publish_paths.py tests/test_workflows.py
git commit -m "ci: deploy embedded HAPP redirects"
```

### Task 5: Verify, deploy, and document the real links

**Files:**
- Modify: `HAPP/README.md`

- [ ] **Step 1: Run the complete local verification**

Run:

```bash
python3 scripts/build_potato_link_worker.py
python3 -m unittest discover -s tests -v
PYTHONPYCACHEPREFIX=/tmp/potato-link-pycache python3 -m compileall -q scripts tests
npm test --prefix cloudflare/potato-link
npm run deploy:dry --prefix cloudflare/potato-link
git diff --exit-code
```

Expected: every command succeeds and the worktree remains clean.

- [ ] **Step 2: Verify Cloudflare authentication**

Run:

```bash
npm exec --prefix cloudflare/potato-link -- wrangler whoami
```

If unauthenticated, run the one-time OAuth flow:

```bash
npm exec --prefix cloudflare/potato-link -- wrangler login
```

Repeat `whoami` and confirm the intended Cloudflare account.

- [ ] **Step 3: Deploy and capture the assigned hostname**

Run:

```bash
npm run deploy --prefix cloudflare/potato-link
```

Record the exact `https://potato-link.<subdomain>.workers.dev` URL emitted by
Wrangler.

- [ ] **Step 4: Verify both production redirects**

Run `curl -I --max-redirs 0` against `/` and `/ru`. Confirm both return `302`,
the locations match `HAPP/DEFAULT.DEEPLINK` and `HAPP/RU-VPN.DEEPLINK`
respectively, and the cache/security headers are present.

- [ ] **Step 5: Document the two clickable URLs**

Add the exact production root and `/ru` links to `HAPP/README.md`, label which
profile each imports, and note that tapping should open HAPP while copying the
raw `.DEEPLINK` remains the fallback.

- [ ] **Step 6: Run final verification and commit documentation**

```bash
python3 -m unittest discover -s tests -v
npm test --prefix cloudflare/potato-link
git diff --check
git add HAPP/README.md
git commit -m "docs: publish clickable HAPP profile links"
```

- [ ] **Step 7: Push, merge, and clean up**

Push `feat/potato-link-worker`, merge it into `main` after checks pass, push
`main`, verify the deployment workflow, then remove the global worktree and
delete the merged feature branch as previously requested.
