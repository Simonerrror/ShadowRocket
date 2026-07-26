# HAPP RU-VPN Profile Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Generate an additional HAPP profile and deeplink that proxy Russian domains/IPs through a selected Russian node while sending all unmatched traffic directly.

**Architecture:** Extend the existing compact V2Ray geodata with `category-ru` from the already pinned domain-list-community checkout and `ru` from a checksum-verified, immutable V2Fly GeoIP artifact cached in the repository. Reuse the HAPP serializer with explicit routing tags to generate `DEFAULT.*` unchanged and new `RU-VPN.*` artifacts with `GlobalProxy: false`.

**Tech Stack:** Python 3 standard library, `unittest`, V2Fly domain-list-community compiler, V2Fly GeoIP compiler, HAPP routing JSON/deeplinks, GitHub Actions YAML.

---

## File map

- `scripts/build_distillate.py`: validate the pinned GeoIP input, compile `category-ru` and `ru` into the existing compact `.dat` outputs.
- `distillate/upstream/v2fly/geoip.dat`: reviewed immutable V2Fly GeoIP input at release commit `402b99afef60cf55058350b5d8c29322835636cd`.
- `scripts/build_happ_routing.py`: generate both profile pairs from explicit routing policies.
- `tests/test_build_distillate.py`: geodata pin, checksum, and compiler-input tests.
- `tests/test_build_happ_routing.py`: JSON/deeplink and DEFAULT-regression tests.
- `scripts/validate_publish_paths.py`, `tests/test_workflows.py`, `.github/workflows/*.yml`: publish and verify both profile pairs.
- `HAPP/README.md`, `README.md`: usage and Russian-exit requirement.
- `HAPP/RU-VPN.JSON`, `HAPP/RU-VPN.DEEPLINK`, `distillate/dat/*.dat`: generated outputs.

### Task 1: Quarantine and compile pinned RU geodata

**Files:**
- Modify: `tests/test_build_distillate.py`
- Modify: `scripts/build_distillate.py`
- Create: `distillate/upstream/v2fly/geoip.dat`

- [ ] **Step 1: Write failing pin and compiler-input tests**

Add imports for the new constants/helpers and these tests:

```python
def test_ru_geoip_source_is_pinned_and_checksum_verified(self) -> None:
    self.assertEqual(GEOIP_DATA_COMMIT, "402b99afef60cf55058350b5d8c29322835636cd")
    self.assertEqual(
        GEOIP_DATA_SHA256,
        "b71d1999439dde2de2d2b6844a2befa50c50211ff739785c005ca7c230a17d6a",
    )

def test_verify_ru_geoip_source_rejects_wrong_payload(self) -> None:
    with tempfile.TemporaryDirectory() as tmpdir:
        path = Path(tmpdir) / "geoip.dat"
        path.write_bytes(b"wrong")
        with self.assertRaisesRegex(DistillateError, "checksum"):
            verify_ru_geoip_source(path)

def test_compiled_geosite_tags_include_category_ru(self) -> None:
    self.assertIn("category-ru", compiled_geosite_tags({"sr-direct": CategoryResult("sr-direct")}))

def test_geoip_inputs_import_ru_from_cached_v2fly_dat(self) -> None:
    inputs, wanted = geoip_compiler_inputs(Path("/repo"), {})
    self.assertEqual(inputs[0]["type"], "v2rayGeoIPDat")
    self.assertEqual(inputs[0]["args"]["wantedList"], ["ru"])
    self.assertIn("ru", wanted)
```

- [ ] **Step 2: Run the focused tests and confirm failure**

Run:

```bash
python3 -m unittest tests.test_build_distillate -v
```

Expected: import failures for the new constants/helpers.

- [ ] **Step 3: Add immutable source metadata and verification**

Add to `scripts/build_distillate.py`:

```python
GEOIP_DATA_COMMIT = "402b99afef60cf55058350b5d8c29322835636cd"
GEOIP_DATA_SHA256 = "b71d1999439dde2de2d2b6844a2befa50c50211ff739785c005ca7c230a17d6a"
GEOIP_DATA_PATH = Path("distillate/upstream/v2fly/geoip.dat")

def verify_ru_geoip_source(path: Path) -> None:
    if not path.exists():
        raise DistillateError(f"Pinned V2Fly GeoIP source is missing: {path}")
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    if digest != GEOIP_DATA_SHA256:
        raise DistillateError(
            f"Pinned V2Fly GeoIP checksum mismatch for {path}: "
            f"expected {GEOIP_DATA_SHA256}, got {digest}"
        )
```

Import `hashlib`. Do not add a floating download path to the normal builder.

- [ ] **Step 4: Cache the reviewed exact artifact**

Download only this immutable URL into the repository cache:

```bash
curl --fail --location \
  https://raw.githubusercontent.com/v2fly/geoip/402b99afef60cf55058350b5d8c29322835636cd/geoip.dat \
  --output distillate/upstream/v2fly/geoip.dat
shasum -a 256 distillate/upstream/v2fly/geoip.dat
```

Expected SHA-256:

```text
b71d1999439dde2de2d2b6844a2befa50c50211ff739785c005ca7c230a17d6a
```

- [ ] **Step 5: Compile `category-ru` and `ru`**

Refactor compiler setup into testable helpers. For geosite, use the pinned checkout's full `data/` tree for include resolution, add the flattened custom categories to that tree, and generate an allowlisted dat containing existing compiled tags plus `category-ru`. For GeoIP, prepend this input and include `ru` in `wantedList`:

```python
{
    "type": "v2rayGeoIPDat",
    "action": "add",
    "args": {
        "uri": str(repo_root / GEOIP_DATA_PATH),
        "wantedList": ["ru"],
    },
}
```

Call `verify_ru_geoip_source()` before invoking the GeoIP compiler. Keep all existing custom text inputs after the pinned V2Fly input.

- [ ] **Step 6: Run focused tests**

Run:

```bash
python3 -m unittest tests.test_build_distillate -v
```

Expected: PASS.

- [ ] **Step 7: Commit the geodata intake**

```bash
git add scripts/build_distillate.py tests/test_build_distillate.py distillate/upstream/v2fly/geoip.dat
git commit -m "build(geodata): add pinned Russian routing data"
```

### Task 2: Generate the additional HAPP profile and deeplink

**Files:**
- Modify: `tests/test_build_happ_routing.py`
- Modify: `scripts/build_happ_routing.py`

- [ ] **Step 1: Write failing RU-VPN profile tests**

Add tests which construct minimal `BuildData`, call the profile builders, and assert:

```python
self.assertEqual(profile["Name"], "RU-VPN")
self.assertEqual(profile["GlobalProxy"], "false")
self.assertEqual(profile["ProxySites"], ["geosite:category-ru"])
self.assertEqual(profile["ProxyIp"], ["geoip:ru"])
self.assertNotIn("geosite:sr-proxy", profile["ProxySites"])
self.assertIn("127.0.0.1", profile["DirectIp"])
```

Add an integration test in a temporary repository that stubs `repo_slug`, creates minimal `.dat` inputs, runs `main()`, and verifies both deeplinks decode to the exact JSON payloads:

```python
encoded = deeplink.strip().rsplit("/", 1)[1]
self.assertEqual(
    json.loads(base64.b64decode(encoded).decode("utf-8")),
    json.loads(json_path.read_text(encoding="utf-8")),
)
```

The test must snapshot `DEFAULT.JSON` before/after generation and assert its routing fields are unchanged.

- [ ] **Step 2: Run focused tests and confirm failure**

Run:

```bash
python3 -m unittest tests.test_build_happ_routing -v
```

Expected: FAIL because `RU_PROFILE_NAME`/RU builder and output files do not exist.

- [ ] **Step 3: Generalize profile construction minimally**

Add:

```python
RU_PROFILE_NAME = "RU-VPN"
RU_PROFILE_FILES = ("RU-VPN.JSON", "RU-VPN.DEEPLINK")
```

Extend `build_profile()` with explicit parameters for:

```python
global_proxy: str = "true"
direct_geosite_tag: str | None = "sr-direct"
direct_geoip_tag: str | None = "sr-direct"
proxy_geosite_tag: str | None = "sr-proxy"
proxy_geoip_tag: str | None = "sr-proxy"
```

Build list entries only when a tag is non-null and its corresponding data is available. Preserve the current defaults so the existing `DEFAULT` call remains behaviorally identical.

- [ ] **Step 4: Build and write RU-VPN artifacts**

In `main()`, reuse the resolved geodata URL, DNS settings, local direct IPs, block tags, build stamp, and deeplink mode. Construct:

```python
ru_profile = build_profile(
    data=data,
    geodata_base=geodata_base,
    last_updated=build_stamp,
    route_order=args.route_order,
    remote_dns_ip=remote_dns_ip,
    remote_dns_domain=args.remote_dns_domain,
    domestic_dns_ip=args.domestic_dns_ip,
    remote_dns_type=args.remote_dns_type,
    domestic_dns_type=args.domestic_dns_type,
    general_direct_ips=general_direct_ips,
    profile_name=RU_PROFILE_NAME,
    block_geosite_tag=block_site_tag,
    global_proxy="false",
    direct_geosite_tag=None,
    direct_geoip_tag=None,
    proxy_geosite_tag="category-ru",
    proxy_geoip_tag="ru",
)
```

Serialize and write `HAPP/RU-VPN.JSON` and `HAPP/RU-VPN.DEEPLINK`. Do not add either filename to `OBSOLETE_HAPP_FILES`.

- [ ] **Step 5: Run focused tests**

Run:

```bash
python3 -m unittest tests.test_build_happ_routing -v
```

Expected: PASS.

- [ ] **Step 6: Commit generator behavior**

```bash
git add scripts/build_happ_routing.py tests/test_build_happ_routing.py
git commit -m "feat(happ): generate RU-VPN routing profile"
```

### Task 3: Publish and verify both profile pairs

**Files:**
- Modify: `tests/test_workflows.py`
- Modify: `scripts/validate_publish_paths.py`
- Modify: `.github/workflows/build-happ-routing.yml`
- Modify: `.github/workflows/sync-lists.yml`

- [ ] **Step 1: Write failing publication tests**

Extend the allowlist test with:

```python
"HAPP/RU-VPN.JSON",
"HAPP/RU-VPN.DEEPLINK",
```

Add assertions that both workflows mention both new files and that the sync workflow copies them into the publication candidate.

- [ ] **Step 2: Run workflow tests and confirm failure**

Run:

```bash
python3 -m unittest tests.test_workflows -v
```

Expected: FAIL because the new artifacts are not allowlisted or packaged.

- [ ] **Step 3: Update allowlists and workflows**

Add both files to `GENERATED_FILES`, verification workflow path filters/diff checks, sync artifact upload paths, publication-copy tuple, and any explicit HAPP file lists. Preserve pinned GitHub Action SHAs and the read-build/write-publish split.

- [ ] **Step 4: Run workflow tests**

Run:

```bash
python3 -m unittest tests.test_workflows -v
```

Expected: PASS.

- [ ] **Step 5: Commit publication integration**

```bash
git add scripts/validate_publish_paths.py tests/test_workflows.py .github/workflows/build-happ-routing.yml .github/workflows/sync-lists.yml
git commit -m "ci(happ): publish RU-VPN artifacts"
```

### Task 4: Generate artifacts and document usage

**Files:**
- Modify: `HAPP/README.md`
- Modify: `README.md`
- Modify: `HAPP/DEFAULT.JSON`
- Modify: `HAPP/DEFAULT.DEEPLINK`
- Create: `HAPP/RU-VPN.JSON`
- Create: `HAPP/RU-VPN.DEEPLINK`
- Modify: `distillate/dat/geosite.dat`
- Modify: `distillate/dat/geoip.dat`

- [ ] **Step 1: Rebuild deterministic geodata and profiles**

Run:

```bash
python3 scripts/build_distillate.py
python3 scripts/build_happ_routing.py
```

Expected: generated `.dat` files contain the new RU tags; `RU-VPN.*` is created; `DEFAULT.*` has no routing-field drift.

- [ ] **Step 2: Add documentation**

In `HAPP/README.md`, add raw GitHub links and behavior:

```markdown
- RU-VPN, deeplink:
  [RU-VPN.DEEPLINK](https://raw.githubusercontent.com/Simonerrror/ShadowRocket/main/HAPP/RU-VPN.DEEPLINK)
- RU-VPN, JSON:
  [RU-VPN.JSON](https://raw.githubusercontent.com/Simonerrror/ShadowRocket/main/HAPP/RU-VPN.JSON)
```

State that `.ru/.рф/.su`, `geosite:category-ru`, and `geoip:ru` go through the selected proxy while unmatched traffic is direct.

In `README.md`, state explicitly:

```markdown
RU-VPN выбирает российский трафик, но не выбирает страну сервера.
Перед активацией профиля выберите узел с проверенным российским выходным IP.
```

- [ ] **Step 3: Validate generated JSON/deeplinks**

Run a Python check that loads both JSON files, decodes both deeplinks, and asserts payload equality plus:

```python
assert ru["GlobalProxy"] == "false"
assert ru["ProxySites"] == ["geosite:category-ru"]
assert ru["ProxyIp"] == ["geoip:ru"]
```

Expected: `OK`.

- [ ] **Step 4: Commit generated artifacts and docs**

```bash
git add HAPP README.md distillate/dat/geosite.dat distillate/dat/geoip.dat
git commit -m "docs(happ): publish RU-VPN import links"
```

### Task 5: Full verification and deterministic rebuild

**Files:**
- Verify only.

- [ ] **Step 1: Run the full required suite**

```bash
python3 -m unittest discover -s tests -v
python3 -m compileall -q scripts tests
```

Expected: all tests PASS and compileall exits 0.

- [ ] **Step 2: Verify deterministic rebuild**

Record `git status --short`, rerun:

```bash
python3 scripts/build_distillate.py
python3 scripts/build_happ_routing.py
```

Then run:

```bash
git diff --check
git status --short
```

Expected: no new diff after the second rebuild.

- [ ] **Step 3: Inspect the final diff and history**

```bash
git log --oneline -6
git diff HEAD~4 --stat
git status --short --branch
```

Expected: only the approved RU-VPN implementation, generated outputs, tests, workflows, and documentation are present; worktree is clean.
