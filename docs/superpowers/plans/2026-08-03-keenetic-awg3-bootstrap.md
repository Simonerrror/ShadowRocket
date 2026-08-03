# Keenetic AWG 3 Bootstrap Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a tested Mac-only toolkit that safely prepares an 8 GiB ext4 microSD partition, creates and restores verified images, installs pinned Entware packages through an offline Keenetic bundle, and deploys pinned AWG Manager 2.16.5 with AWG 3.0.

**Architecture:** Small Bash entry points share one strict common library and are tested from Python `unittest` through fake system commands. Destructive card actions require immutable device identity plus explicit confirmation; router mutations consume only locally cached artifacts matching a committed lock. The first execution stops at two human gates: approval of the quarantined Entware closure, then approval to run the custom bundle on the named router.

**Tech Stack:** macOS Bash 3.2, `diskutil`, `hdiutil`, Homebrew e2fsprogs 1.47.3, OpenSSH/SFTP, BusyBox shell on KeeneticOS, Entware `opkg`, Python 3 standard-library `unittest`.

---

## Scope and file map

Create a self-contained `custom-only` area:

- `tools/keenetic-awg3/README.md` — operator runbook and recovery sequence.
- `tools/keenetic-awg3/manifests/artifacts.lock` — reviewed URL, size, SHA-256, architecture, package and version records.
- `tools/keenetic-awg3/manifests/entware-install-order.txt` — explicit offline package order.
- `tools/keenetic-awg3/profiles/router.example.env` — non-secret device profile contract.
- `tools/keenetic-awg3/scripts/_common.sh` — strict mode, profile parsing, lock lookup, hashing, redaction and command wrappers.
- `tools/keenetic-awg3/scripts/inspect-card.sh` — read-only card identity and layout report.
- `tools/keenetic-awg3/scripts/prepare-card.sh` — guarded MBR/8 GiB/ext4 creation.
- `tools/keenetic-awg3/scripts/backup-card.sh` — offline metadata and compressed raw image creation.
- `tools/keenetic-awg3/scripts/restore-card.sh` — guarded raw restore and filesystem verification.
- `tools/keenetic-awg3/scripts/fetch-artifacts.sh` — download-only quarantine intake.
- `tools/keenetic-awg3/scripts/audit-artifacts.sh` — IPK metadata, maintainer-script and ELF architecture report.
- `tools/keenetic-awg3/scripts/build-entware-bundle.sh` — deterministic local Keenetic installer bundle assembly.
- `tools/keenetic-awg3/scripts/preflight-router.sh` — read-only router compatibility report.
- `tools/keenetic-awg3/scripts/bootstrap-entware.sh` — upload and explicitly arm the reviewed bundle.
- `tools/keenetic-awg3/scripts/sanitize-golden-source.sh` — remove device-private host state before the golden image.
- `tools/keenetic-awg3/scripts/install-awg-manager.sh` — backed-up pinned IPK install.
- `tools/keenetic-awg3/scripts/verify-router.sh` — SSH, service, module, port and WAN-exposure checks.
- `tools/keenetic-awg3/scripts/backup-router.sh` — versioned per-device configuration export without logging secret material.
- `tools/keenetic-awg3/payload/install-offline.sh` — BusyBox-compatible installer placed inside the custom bundle.
- `tools/keenetic-awg3/payload/S00firstboot-keys` — regenerate unique SSH host keys after golden-image restore.
- `tests/test_keenetic_awg3_card.py` — destructive boundary and image recovery tests.
- `tests/test_keenetic_awg3_artifacts.py` — lock, hash, package audit and bundle-content tests.
- `tests/test_keenetic_awg3_router.py` — SSH command sequencing, redaction and mutation-gate tests.
- `tests/keenetic_awg3_test_support.py` — reusable subprocess/fake-command harness.
- `.gitignore` — exclude `tools/keenetic-awg3/local/`.

No third-party Python or shell-test dependency is added.

The public CLI is fixed before implementation:

```text
inspect-card.sh /dev/diskN
prepare-card.sh /dev/diskN
backup-card.sh --kind device|golden /dev/diskN OUTPUT_DIR
restore-card.sh BACKUP_DIR /dev/diskN
fetch-artifacts.sh [CACHE_DIR]
audit-artifacts.sh [CACHE_DIR]
build-entware-bundle.sh --public-key FILE --output FILE
preflight-router.sh PROFILE
bootstrap-entware.sh PROFILE BUNDLE
sanitize-golden-source.sh PROFILE
backup-router.sh PROFILE OUTPUT_DIR
install-awg-manager.sh PROFILE [CACHE_DIR]
verify-router.sh PROFILE [--tunnel]
```

All tests inherit a standard-library helper in
`tests/keenetic_awg3_test_support.py`. It creates a temporary `bin/`, writes
executable fake commands, prepends that directory to `PATH`, records calls in a
JSON-lines file, and runs entry points with a clean environment:

```python
class ToolTestCase(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="keenetic-awg3-test."))
        self.bin = self.tmp / "bin"
        self.bin.mkdir()
        (self.tmp / "home").mkdir()
        self.calls = self.tmp / "calls.jsonl"
        self.env = {
            "PATH": f"{self.bin}:/usr/bin:/bin",
            "HOME": str(self.tmp / "home"),
            "KEENETIC_AWG3_TEST_MODE": "1",
            "KEENETIC_AWG3_CALLS": str(self.calls),
        }

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def temp_path(self, name, content=""):
        path = self.tmp / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)
        return path

    def fake_command(self, name, body):
        path = self.bin / name
        path.write_text("#!/bin/bash\nset -eu\n" + body)
        path.chmod(0o755)
        return path

    def run_script(self, relative, *args, stdin=""):
        return subprocess.run(
            [str(ROOT / relative), *map(str, args)], input=stdin,
            text=True, capture_output=True, env=self.env, check=False,
        )

    def recorded_calls(self):
        if not self.calls.exists():
            return []
        return [json.loads(line) for line in self.calls.read_text().splitlines()]
```

Task 1 creates this helper alongside the first two test modules. Domain helpers
such as `run_prepare`, `run_restore`, `run_bootstrap` and `run_awg_install` are
thin test-fixture builders around `fake_command` and `run_script`; each returns
`(CompletedProcess, recorded_calls())` as used below.

## Verification portfolio

| Category | Capability or risk | Primary proof | Why this level |
|---|---|---|---|
| Security | System/internal/wrong removable disk cannot be written | Integration test with fake `diskutil` and write-command recorder | Proves rejection occurs before any destructive subprocess |
| Integrity | Only locked artifacts enter bundle or router | Artifact integration test against corrupt and valid cache | Owns size/hash/version/architecture invariant at the intake boundary |
| Recovery | Full image restores exact bytes and ext4 check runs | Sparse-image integration test | Proves backup and restore are compatible, not merely creatable |
| Idempotency | Existing `/opt` and AWG config are preserved | Router workflow test with fake SSH state transitions | Proves rerun selects verify/stop instead of overwriting |
| Security | Passwords/private keys never enter arguments, output or Git | Router integration test and tracked-file scan | Covers the actual observable leak surfaces |
| Deployment | AWG package starts only after backup and explicit gate | Recorded fake SSH/SCP command sequence | Proves ordering around the package's active `postinst` |
| End-to-end | Fresh card reaches key-only Entware SSH and AWG 3 handshake | Manual acceptance on current router, then spare card restore | Hardware, firmware and kernel-module behavior cannot be faithfully emulated |

## Locked baseline

The first implementation uses the already reviewed discovery snapshot from 3
August 2026:

- Entware base archive `aarch64-installer.tar.gz`, SHA-256
  `64451a3a70ca85aaab3b0677814f6b58f7994793ed6b120eddc36a16639c15d1`.
- Entware main `Packages`, SHA-256
  `b1f04218d93d967d79fdf8d58badd759c3fd44dda4edeb2d68670f9fbbff1283`.
- Entware Keenetic `Packages`, SHA-256
  `9054004f134e6de1a19eda70e3433f1e4611b1739fc9a55fabad95b5ec87d3cf`.
- AWG Manager `2.16.5`, SHA-256
  `1b841747a85dda101e5d9be0b647c84275f354fc51b41d71b26e684f44f19b12`.
- AWG embedded module bundle `3.0.20260731-04`.
- Entware closure: 32 exact IPKs, including Keenetic-priority
  `iptables_1.4.21-6_aarch64-3.10_kn.ipk`, `opt-ndmsv2_1.0-17`,
  `poorbox_1.37.0-2`, Dropbear `2025.89-1`, and AWG dependencies
  `ip-full_4.4.0-11`, `wireguard-tools_1.0.20250521-1`, `conntrack_1.4.8-1`.

The lock contains all 32 feed-provided SHA-256 values, not just this summary.
Execution must stop for human review if any source has changed; discovering a
newer release never mutates the lock automatically.

### Task 1: Strict local contract and secret boundary

**Files:**
- Create: `tools/keenetic-awg3/scripts/_common.sh`
- Create: `tools/keenetic-awg3/profiles/router.example.env`
- Create: `tools/keenetic-awg3/manifests/artifacts.lock`
- Create: `tools/keenetic-awg3/manifests/entware-install-order.txt`
- Modify: `.gitignore`
- Test: `tests/test_keenetic_awg3_artifacts.py`
- Test: `tests/test_keenetic_awg3_router.py`
- Test support: `tests/keenetic_awg3_test_support.py`

**Risk/capability:** Every later command receives validated non-secret configuration and can only resolve exact locked artifacts.

**Primary proof:** Execute `_common.sh` helpers in a subprocess with valid and malicious profiles; assert lock lookup succeeds only for an exact unique record and logs redact sensitive values.

- [ ] **Step 1: Write failing contract tests**

Create tests that invoke Bash rather than inspect source text:

```python
class CommonContractTests(unittest.TestCase):
    def run_common(self, body, env=None):
        script = ROOT / "tools/keenetic-awg3/scripts/_common.sh"
        return subprocess.run(
            ["bash", "-c", f"source {shlex.quote(str(script))}; {body}"],
            text=True, capture_output=True, env=env, check=False,
        )

    def test_profile_rejects_shell_syntax(self):
        profile = self.temp_path("router.env", "ROUTER_HOST=$(id)\n")
        result = self.run_common(f"load_profile {shlex.quote(str(profile))}")
        self.assertNotEqual(result.returncode, 0)
        self.assertNotIn("uid=", result.stdout + result.stderr)

    def test_lock_requires_exact_unique_record(self):
        result = self.run_common("lock_field awg-manager 2.16.5 sha256")
        self.assertEqual(result.returncode, 0)
        self.assertEqual(len(result.stdout.strip()), 64)

    def test_redaction_covers_password_and_private_key(self):
        result = self.run_common(
            "redact 'password=codex123 key=-----BEGIN OPENSSH PRIVATE KEY-----'"
        )
        self.assertNotIn("codex123", result.stdout)
        self.assertNotIn("BEGIN OPENSSH", result.stdout)
```

- [ ] **Step 2: Run tests and confirm the missing common library fails**

Run:

```bash
python3 -m unittest tests.test_keenetic_awg3_artifacts tests.test_keenetic_awg3_router -v
```

Expected: FAIL because `_common.sh` and the manifest do not exist.

- [ ] **Step 3: Implement the common contract**

Use `set -euo pipefail`, derive `TOOL_ROOT` from `BASH_SOURCE`, and expose these
stable functions:

```bash
SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
TOOL_ROOT=$(cd "$SCRIPT_DIR/.." && pwd)
ARTIFACT_LOCK="$TOOL_ROOT/manifests/artifacts.lock"

die() { printf 'ERROR: %s\n' "$*" >&2; exit 1; }
require_cmd() { command -v "$1" >/dev/null 2>&1 || die "missing command: $1"; }
sha256_file() { shasum -a 256 "$1" | awk '{print $1}'; }
redact() {
  if [ "$#" -gt 0 ]; then printf '%s\n' "$*"; else cat; fi | sed -E \
    -e 's/([Pp][Aa][Ss][Ss][Ww][Oo][Rr][Dd]|token|secret)=([^ ]+)/\1=<redacted>/g' \
    -e 's/-----BEGIN [A-Z ]*PRIVATE KEY-----/<private-key-redacted>/g'
}
lock_field() {
  local package="$1" version="$2" field="$3" column
  case "$field" in
    repo) column=1 ;; package) column=2 ;; version) column=3 ;;
    architecture) column=4 ;; size) column=5 ;; sha256) column=6 ;; url) column=7 ;;
    *) die "unknown lock field: $field" ;;
  esac
  awk -F'|' -v p="$package" -v v="$version" -v n="$column" '
    NR > 1 && $2 == p && $3 == v { print $n; found++ }
    END { if (found != 1) exit 1 }
  ' "$ARTIFACT_LOCK"
}
load_profile() {
  local file="$1" line key value
  [ -f "$file" ] || die "profile not found: $file"
  while IFS= read -r line || [ -n "$line" ]; do
    case "$line" in ''|'#'*) continue ;; esac
    case "$line" in
      [A-Z_]*=*) key=${line%%=*}; value=${line#*=} ;;
      *) die "invalid profile line" ;;
    esac
    case "$key" in
      ROUTER_NAME|ADMIN_USER) [[ "$value" =~ ^[A-Za-z0-9._-]+$ ]] || die "invalid $key" ;;
      ROUTER_HOST) [[ "$value" =~ ^[A-Za-z0-9.:-]+$ ]] || die "invalid $key" ;;
      ROOT_PORT)
        [[ "$value" =~ ^[0-9]{1,5}$ ]] && [ "$value" -ge 1 ] && [ "$value" -le 65535 ] || die "invalid $key"
        ;;
      EXPECTED_MODEL) [[ "$value" =~ ^[A-Za-z0-9+._\ -]+$ ]] || die "invalid $key" ;;
      *) die "unknown profile key: $key" ;;
    esac
    printf -v "$key" '%s' "$value"
    export "$key"
  done < "$file"
}
```

The example profile is:

```dotenv
ROUTER_NAME=hopper-main
ROUTER_HOST=192.168.1.1
ADMIN_USER=admin
ROOT_PORT=222
EXPECTED_MODEL=Netcraze Hopper 4G+ NC-2312
```

Use a pipe-delimited lock schema:

```text
repo|package|version|architecture|size|sha256|url
```

Reject comments inside records, duplicate `repo/package/version` keys, non-HTTPS
URLs, non-decimal sizes and non-64-character lowercase hashes. The full Entware
closure and exact install order are copied from the locked appendix at the end
of this plan. The local working directory is excluded with:

```gitignore
/tools/keenetic-awg3/local/
```

- [ ] **Step 4: Run focused tests**

Run the Step 2 command. Expected: PASS.

- [ ] **Step 5: Commit the contract slice**

```bash
git add .gitignore tools/keenetic-awg3/manifests tools/keenetic-awg3/profiles \
  tools/keenetic-awg3/scripts/_common.sh tests/test_keenetic_awg3_artifacts.py \
  tests/test_keenetic_awg3_router.py tests/keenetic_awg3_test_support.py
git commit -m "feat(keenetic): зафиксировать AWG3 artifact contract"
```

### Task 2: Safe MBR and ext4 card preparation

**Files:**
- Create: `tools/keenetic-awg3/scripts/inspect-card.sh`
- Create: `tools/keenetic-awg3/scripts/prepare-card.sh`
- Test: `tests/test_keenetic_awg3_card.py`

**Risk/capability:** A named external removable card becomes one 8 GiB Linux partition at sector 2048, while internal, virtual and changed devices are rejected before writing.

**Primary proof:** Drive scripts against fake `diskutil`/`sudo` recorders for rejection and against a temporary 32 GiB sparse disk image for the exact MBR layout.

- [ ] **Step 1: Write failing destructive-boundary tests**

Cover these observable cases in `tests/test_keenetic_awg3_card.py`:

```python
def test_internal_disk_is_rejected_before_sudo(self):
    result, calls = self.run_prepare(plist="internal.plist", answer="disk9\n")
    self.assertNotEqual(result.returncode, 0)
    self.assertEqual(calls, [])

def test_identity_change_after_confirmation_is_rejected(self):
    result, calls = self.run_prepare(
        plist_sequence=["safe-card.plist", "different-card.plist"],
        answer="disk9\n",
    )
    self.assertNotEqual(result.returncode, 0)
    self.assertFalse(any("partitionDisk" in call for call in calls))

def test_safe_card_uses_exact_partition_contract(self):
    result, calls = self.run_prepare(plist="safe-card.plist", answer="disk9\n")
    self.assertEqual(result.returncode, 0)
    self.assertIn(
        "diskutil partitionDisk /dev/disk9 2 MBRFormat %Linux% ENT 8GiB Free Space UNUSED R",
        calls,
    )
```

Fixtures use plist keys observed on macOS: `Internal`, `WholeDisk`,
`RemovableMedia`, `RemovableMediaOrExternalDevice`, `WritableMedia`, `Size`,
`DeviceIdentifier`, `MediaName`, `BusProtocol`, and `Content`.

- [ ] **Step 2: Run the card test and confirm failure**

```bash
python3 -m unittest tests.test_keenetic_awg3_card -v
```

Expected: FAIL because the card scripts do not exist.

- [ ] **Step 3: Implement read-only inspection and two-pass identity validation**

`inspect-card.sh /dev/diskN` must reject slice identifiers and print a canonical
fingerprint made from identifier, size, media name, bus protocol and IOKit path.
`prepare-card.sh` calls inspection twice and compares the fingerprints around
the exact confirmation prompt:

```bash
printf 'Type %s to ERASE this card: ' "$disk_id" >&2
IFS= read -r confirmation
[ "$confirmation" = "$disk_id" ] || die "confirmation mismatch"
[ "$(card_fingerprint "$device")" = "$first_fingerprint" ] || \
  die "device identity changed"
```

After the second check, execute:

```bash
sudo /usr/sbin/diskutil unmountDisk "$device"
sudo /usr/sbin/diskutil partitionDisk "$device" 2 MBRFormat \
  '%Linux%' ENT 8GiB 'Free Space' UNUSED R
sudo /usr/sbin/diskutil unmountDisk "$device"
sudo "$E2FSPROGS_PREFIX/sbin/mkfs.ext4" -F -L ENT -m 0 \
  -O '^metadata_csum_seed,^orphan_file' "/dev/r${disk_id}s1"
sudo "$E2FSPROGS_PREFIX/sbin/e2fsck" -fn "/dev/r${disk_id}s1"
```

Resolve `E2FSPROGS_PREFIX` with `brew --prefix e2fsprogs`, verify `mke2fs
1.47.3`, and refuse a different version until reviewed. Verify postconditions
with `fdisk`: signature `0xAA55`, partition id `83`, start `2048`, size
`16777216` sectors; verify ext4 label and features with `dumpe2fs -h`.

- [ ] **Step 4: Verify behavior and a safe sparse-image probe**

Run the unit test, then create a temporary sparse image and execute only the
partition-map portion:

```bash
probe_dir=$(mktemp -d /tmp/keenetic-card-probe.XXXXXX)
hdiutil create -size 32g -type SPARSE -layout NONE -ov "$probe_dir/card"
probe_disk=$(hdiutil attach -nomount "$probe_dir/card.sparseimage" | awk 'NR==1 {print $1}')
diskutil partitionDisk "$probe_disk" 2 MBRFormat '%Linux%' ENT 8GiB 'Free Space' UNUSED R
fdisk "$probe_disk"
hdiutil detach "$probe_disk"
```

Expected: partition 1 has id `83`, start `2048`, size `16777216`; the remainder
is free. The test image is deleted after detach.

- [ ] **Step 5: Commit safe preparation**

```bash
git add tools/keenetic-awg3/scripts/inspect-card.sh \
  tools/keenetic-awg3/scripts/prepare-card.sh tests/test_keenetic_awg3_card.py
git commit -m "feat(keenetic): безопасно готовить ext4-карту"
```

### Task 3: Verifiable full-image backup and restore

**Files:**
- Create: `tools/keenetic-awg3/scripts/backup-card.sh`
- Create: `tools/keenetic-awg3/scripts/restore-card.sh`
- Modify: `tests/test_keenetic_awg3_card.py`

**Risk/capability:** The toolkit produces a restorable full image, not only ext4 metadata, and cannot restore it to a smaller or different device.

**Primary proof:** Back up and restore deterministic bytes in a temporary file-backed fixture; compare raw SHA-256 and assert `e2fsck -fn` is the final successful operation.

- [ ] **Step 1: Add failing backup/restore tests**

```python
def test_backup_manifest_describes_raw_payload(self):
    result = self.run_backup(self.raw_fixture, self.output_dir)
    manifest = json.loads((self.output_dir / "manifest.json").read_text())
    self.assertEqual(manifest["raw_bytes"], 8589934592)
    self.assertRegex(manifest["raw_sha256"], r"^[0-9a-f]{64}$")
    self.assertEqual(result.returncode, 0)

def test_restore_refuses_smaller_partition_before_dd(self):
    result, calls = self.run_restore(target_bytes=8589934080)
    self.assertNotEqual(result.returncode, 0)
    self.assertFalse(any(call.startswith("dd ") for call in calls))

def test_restore_verifies_raw_hash_and_runs_fsck(self):
    result, calls = self.run_restore(target_bytes=8589934592)
    self.assertEqual(result.returncode, 0)
    self.assertEqual(calls[-1].split()[0], "e2fsck")

def test_golden_restore_randomizes_filesystem_uuid(self):
    result, calls = self.run_restore(target_bytes=8589934592, golden=True)
    self.assertEqual(result.returncode, 0)
    self.assertTrue(any("tune2fs -U random" in call for call in calls))
```

- [ ] **Step 2: Run focused tests and confirm failure**

Run `python3 -m unittest tests.test_keenetic_awg3_card -v`. Expected: new image
tests FAIL because backup/restore entry points are missing.

- [ ] **Step 3: Implement distinct metadata and full-image artifacts**

`backup-card.sh` reuses the card identity checks, requires the whole disk to be
unmounted, and writes to a new timestamped directory:

```bash
sudo "$E2FSPROGS_PREFIX/sbin/e2fsck" -fn "$raw_partition"
sudo "$E2FSPROGS_PREFIX/sbin/e2image" -r "$raw_partition" "$output/fs-metadata.e2i"
sudo dd if="$raw_partition" bs=8m | gzip -1 > "$output/partition.raw.gz"
gzip -dc "$output/partition.raw.gz" | shasum -a 256 > "$output/partition.raw.sha256"
```

Write `manifest.json` atomically only after all commands pass. Record raw bytes,
raw hash, compressed hash, ext4 UUID/label/features, device fingerprint,
partition start/size, tool versions and UTC timestamp. Never overwrite an
existing backup directory.

`restore-card.sh` verifies both hashes, checks `raw_bytes == target partition
bytes`, repeats the explicit disk confirmation and identity check, then writes:

```bash
gzip -dc "$image" | sudo dd of="$raw_partition" bs=8m
sudo sync
sudo "$E2FSPROGS_PREFIX/sbin/e2fsck" -fn "$raw_partition"
```

It rejects a whole-disk target: restore always addresses `diskNs1` after
verifying the parent whole disk. For a manifest with `kind=golden`, it runs
`tune2fs -U random` and another `e2fsck -fn` so cloned cards do not share an
ext4 UUID. For `kind=device`, it preserves the UUID for exact disaster recovery.

- [ ] **Step 4: Run recovery tests**

Run `python3 -m unittest tests.test_keenetic_awg3_card -v`. Expected: PASS and
the fixture's before/after SHA-256 values match.

- [ ] **Step 5: Commit recovery tooling**

```bash
git add tools/keenetic-awg3/scripts/backup-card.sh \
  tools/keenetic-awg3/scripts/restore-card.sh tests/test_keenetic_awg3_card.py
git commit -m "feat(keenetic): добавить проверяемый backup карт"
```

### Task 4: Quarantined artifacts and offline Entware bundle

**Files:**
- Create: `tools/keenetic-awg3/scripts/fetch-artifacts.sh`
- Create: `tools/keenetic-awg3/scripts/audit-artifacts.sh`
- Create: `tools/keenetic-awg3/scripts/build-entware-bundle.sh`
- Create: `tools/keenetic-awg3/payload/install-offline.sh`
- Create: `tools/keenetic-awg3/payload/S00firstboot-keys`
- Modify: `tests/test_keenetic_awg3_artifacts.py`

**Risk/capability:** No floating feed or remote installer script executes on the router; every package and maintainer script is locally reviewable before bundle creation.

**Primary proof:** Build a bundle from fixture IPKs, reject one-byte corruption, and inspect the resulting tar to prove it contains only locked packages, a supplied public key and the offline installer.

- [ ] **Step 1: Add failing artifact pipeline tests**

```python
def test_fetch_rejects_hash_mismatch_and_removes_partial(self):
    result = self.run_fetch(self.lock_with_wrong_hash)
    self.assertNotEqual(result.returncode, 0)
    self.assertEqual(list(self.cache.glob("*.partial")), [])

def test_audit_extracts_maintainer_scripts_without_running_them(self):
    result = self.run_audit(self.fixture_ipk_with_postinst)
    self.assertEqual(result.returncode, 0)
    self.assertIn("postinst", result.stdout)
    self.assertFalse(self.side_effect_marker.exists())

def test_bundle_contains_only_locked_ipks_and_public_key(self):
    bundle = self.build_bundle(self.valid_cache, self.public_key)
    names = self.tar_names(bundle)
    self.assertIn("./bootstrap-packages/dropbear_2025.89-1_aarch64-3.10.ipk", names)
    self.assertIn("./root/.ssh/authorized_keys", names)
    self.assertNotIn("./etc/dropbear/dropbear_rsa_host_key", names)
    self.assertIn("./etc/init.d/S00firstboot-keys", names)
```

- [ ] **Step 2: Run artifact tests and confirm failure**

```bash
python3 -m unittest tests.test_keenetic_awg3_artifacts -v
```

Expected: FAIL because intake, audit and bundle scripts are missing.

- [ ] **Step 3: Implement download-only intake and readable audit reports**

`fetch-artifacts.sh` uses `curl --fail --location --proto '=https'
--tlsv1.2`, writes `.partial`, verifies exact byte count and SHA-256, then
renames atomically. It never invokes `opkg`, package binaries or maintainer
scripts.

`audit-artifacts.sh` supports both outer gzip-tar and `ar` IPK variants. For
each IPK it extracts into `mktemp -d`, prints `control`, `preinst`, `postinst`,
`prerm`, `postrm`, file list, and `file` results for ELF/`.ko` files. The AWG
report must show `Version: 2.16.5`, AArch64 binaries, dependencies
`iptables, ip-full, wireguard-tools, conntrack`, and bundle version
`3.0.20260731-04`.

- [ ] **Step 4: Implement the offline Keenetic payload**

Start from the exact Entware base archive, verify its hash, extract it, remove
the bundled Dropbear host keys and original online `/bin/install`, then copy all
32 locked IPKs plus the supplied OpenSSH public key. `install-offline.sh` must
be BusyBox `sh`, fail before mutation if any package is missing, and never call
`opkg update`:

```sh
#!/bin/sh
set -eu
PATH=/opt/bin:/opt/sbin:/sbin:/bin:/usr/sbin:/usr/bin
PKG_DIR=/opt/bootstrap-packages
ORDER=/opt/bootstrap-packages/install-order.txt

mount | grep -q 'on /opt .*ext' || exit 20
[ -s /opt/root/.ssh/authorized_keys ] || exit 21
while IFS= read -r package; do
    [ -f "$PKG_DIR/$package" ] || exit 22
done < "$ORDER"

while IFS= read -r package; do
    /opt/bin/opkg install "$PKG_DIR/$package"
done < "$ORDER"

chmod 700 /opt/root /opt/root/.ssh
chmod 600 /opt/root/.ssh/authorized_keys
rm -f /opt/etc/dropbear/dropbear_*_host_key
/opt/bin/dropbearkey -t rsa -f /opt/etc/dropbear/dropbear_rsa_host_key
/opt/bin/dropbearkey -t ed25519 -f /opt/etc/dropbear/dropbear_ed25519_host_key
sed -i 's|$DROPBEAR -p $PORT -P $PIDFILE|$DROPBEAR -s -p $PORT -P $PIDFILE -D /opt/root/.ssh|' \
  /opt/etc/init.d/S51dropbear
sed -i 's/^PORT=.*/PORT=222/' /opt/etc/config/dropbear.conf
/opt/etc/init.d/S51dropbear start
wget -qO - --post-data='[{"opkg":{"initrc":{"path":"/opt/etc/init.d/rc.unslung"}}},{"system":{"configuration":{"save":true}}}]' \
  localhost:79/rci/ >/dev/null
rm -rf "$PKG_DIR"
rm -f /opt/etc/init.d/doinstall /opt/bin/install
```

Install `S00firstboot-keys` with mode 755. Its `start` action creates missing
RSA and Ed25519 host keys, starts no network service itself, and removes
`/opt/.golden-ready` after successful generation:

```sh
#!/bin/sh
case "${1:-start}" in
  start)
    for key in rsa ed25519; do
      file="/opt/etc/dropbear/dropbear_${key}_host_key"
      [ -s "$file" ] || /opt/bin/dropbearkey -t "$key" -f "$file" || exit 1
      chmod 600 "$file"
    done
    rm -f /opt/.golden-ready
    ;;
esac
```

Before adopting the `-D /opt/root/.ssh` invocation, inspect the locked
Dropbear binary's help in no-listen mode on the current AArch64 router and
compare it with the reviewed 2025.89 package documentation. This remains
Mac-plus-router only; no VM is introduced. If its meaning differs, stop for
review and do not guess another flag.

Repack deterministically with sorted names, numeric owner/group 0, fixed mtime,
and gzip without original filename/timestamp. Save bundle SHA-256 and a build
manifest in `local/bundles/`; never commit the personalized bundle.

- [ ] **Step 5: Run artifact tests and generate the review report**

```bash
python3 -m unittest tests.test_keenetic_awg3_artifacts -v
tools/keenetic-awg3/scripts/fetch-artifacts.sh
tools/keenetic-awg3/scripts/audit-artifacts.sh \
  > tools/keenetic-awg3/local/audit-2026-08-03.txt
```

Expected: tests PASS; exactly 33 IPKs are cached (32 Entware plus AWG Manager);
the audit report lists but does not execute every maintainer script.

This is the first human gate. Review the report and `artifacts.lock`; do not
build or upload a router bundle until the user explicitly approves them.

- [ ] **Step 6: Commit quarantine tooling**

```bash
git add tools/keenetic-awg3/scripts/fetch-artifacts.sh \
  tools/keenetic-awg3/scripts/audit-artifacts.sh \
  tools/keenetic-awg3/scripts/build-entware-bundle.sh \
  tools/keenetic-awg3/payload/install-offline.sh \
  tools/keenetic-awg3/payload/S00firstboot-keys \
  tests/test_keenetic_awg3_artifacts.py
git commit -m "feat(keenetic): собирать offline Entware bundle"
```

### Task 5: Router preflight and idempotent Entware bootstrap

**Files:**
- Create: `tools/keenetic-awg3/scripts/preflight-router.sh`
- Create: `tools/keenetic-awg3/scripts/bootstrap-entware.sh`
- Create: `tools/keenetic-awg3/scripts/sanitize-golden-source.sh`
- Modify: `tests/test_keenetic_awg3_router.py`

**Risk/capability:** The correct router and mounted `ENT` volume are verified before upload; existing Entware is preserved and a fresh install requires a separate arming confirmation.

**Primary proof:** Fake SSH responses model fresh, healthy and conflicted `/opt` states and record that only the fresh approved state receives an upload/mutation.

- [ ] **Step 1: Add failing router-state tests**

```python
def test_model_mismatch_is_read_only(self):
    result, calls = self.run_bootstrap(state="wrong-model")
    self.assertNotEqual(result.returncode, 0)
    self.assertFalse(any(call.startswith("scp ") for call in calls))

def test_healthy_entware_is_verified_not_overwritten(self):
    result, calls = self.run_bootstrap(state="healthy-entware")
    self.assertEqual(result.returncode, 0)
    self.assertFalse(any(call.startswith("scp ") for call in calls))

def test_fresh_ent_volume_requires_exact_router_and_bundle_confirmation(self):
    result, calls = self.run_bootstrap(state="fresh", answer="wrong\n")
    self.assertNotEqual(result.returncode, 0)
    self.assertFalse(any(call.startswith("scp ") for call in calls))

def test_golden_sanitize_refuses_after_awg_manager_install(self):
    result, calls = self.run_golden_sanitize(awg_installed=True)
    self.assertNotEqual(result.returncode, 0)
    self.assertFalse(any("rm -f /opt/etc/dropbear" in call for call in calls))
```

- [ ] **Step 2: Run router tests and confirm failure**

Run `python3 -m unittest tests.test_keenetic_awg3_router -v`. Expected: new
preflight/bootstrap cases FAIL.

- [ ] **Step 3: Implement read-only preflight**

Use OpenSSH options `BatchMode=yes`, `IdentitiesOnly=yes`,
`StrictHostKeyChecking=yes`, a dedicated known-hosts file under `local/`, and
no password command-line argument. Collect and redact:

```sh
uname -a
cat /proc/sys/kernel/osrelease
mount
df -k /opt /tmp/mnt/ENT
test -x /opt/bin/opkg && /opt/bin/opkg list-installed
dmesg | tail -n 200
```

The admin connection may prompt interactively in a terminal, but credentials
are never accepted as script arguments or environment values. Confirm model,
firmware family `aarch64-k3.10`, mounted ext4 label/path, at least 256 MiB free,
and absence of ext4 I/O/checksum errors. Classify state as `fresh`, `healthy`,
or `conflict`.

- [ ] **Step 4: Implement the explicit bootstrap gate**

For `healthy`, run verification and exit zero. For `conflict`, print paths and
exit without mutation. For `fresh`, verify personalized bundle hash, then
require:

```text
INSTALL hopper-main 192.168.1.1 <bundle-sha256>
```

Upload to the mounted `ENT` root using native SFTP and instruct Keenetic's
package-manager component to consume it using the already configured disk. Do
not install/change KeeneticOS components or reboot. Keep the native admin
session open until a new root connection on port 222 succeeds by key and
password authentication is rejected.

- [ ] **Step 5: Implement the golden-image handoff before AWG installation**

`sanitize-golden-source.sh` requires healthy Entware, no installed
`awg-manager`, no `/opt/etc/awg-manager/tunnels`, and an explicit
`SANITIZE GOLDEN hopper-main` confirmation. It stops Dropbear, clears logs and
shell history, removes only `/opt/etc/dropbear/dropbear_*_host_key`, writes
`/opt/.golden-ready`, runs `sync`, and requests safe volume ejection. It leaves
the public `authorized_keys` file in place and does not delete package state.

After moving the card to the Mac, create the image with:

```bash
tools/keenetic-awg3/scripts/backup-card.sh --kind golden /dev/diskN \
  tools/keenetic-awg3/local/images/entware-base-2026-08-03
```

Golden mode uses `debugfs -R` to require `/.golden-ready`, absence of
`/etc/dropbear/dropbear_*_host_key`, and absence of `/etc/awg-manager` inside
the ext4 root. Reinsert the
source card and verify `S00firstboot-keys` creates new device-unique host keys;
accept the expected changed SSH host fingerprint only after comparing it over
the still-open native admin session.

- [ ] **Step 6: Run router workflow tests**

Run `python3 -m unittest tests.test_keenetic_awg3_router -v`. Expected: PASS;
only the fresh, exactly confirmed fixture records an upload.

- [ ] **Step 7: Commit Entware deployment**

```bash
git add tools/keenetic-awg3/scripts/preflight-router.sh \
  tools/keenetic-awg3/scripts/bootstrap-entware.sh \
  tools/keenetic-awg3/scripts/sanitize-golden-source.sh \
  tests/test_keenetic_awg3_router.py
git commit -m "feat(keenetic): безопасно разворачивать Entware"
```

### Task 6: Backed-up AWG Manager install and operational verification

**Files:**
- Create: `tools/keenetic-awg3/scripts/backup-router.sh`
- Create: `tools/keenetic-awg3/scripts/install-awg-manager.sh`
- Create: `tools/keenetic-awg3/scripts/verify-router.sh`
- Modify: `tests/test_keenetic_awg3_router.py`

**Risk/capability:** AWG Manager's active `postinst` runs only after a valid backup, dependencies and explicit confirmation; failure produces diagnostics without invoking destructive package removal.

**Primary proof:** Fake router workflow asserts strict backup-upload-install-verify order and failure behavior around `opkg install`.

- [ ] **Step 1: Add failing install-order and rollback tests**

```python
def test_awg_install_orders_backup_before_active_postinst(self):
    result, calls = self.run_awg_install(state="ready", confirmed=True)
    self.assertEqual(result.returncode, 0)
    self.assertLess(self.index(calls, "backup-router"), self.index(calls, "opkg install"))

def test_failed_postinst_collects_diagnostics_without_opkg_remove(self):
    result, calls = self.run_awg_install(state="postinst-fails", confirmed=True)
    self.assertNotEqual(result.returncode, 0)
    self.assertTrue(any("dmesg" in call for call in calls))
    self.assertFalse(any("opkg remove" in call for call in calls))

def test_verifier_requires_awg3_and_lan_only_port(self):
    result = self.run_verify(module_version="3.0.20260731-04", wan_open=False)
    self.assertEqual(result.returncode, 0)
```

- [ ] **Step 2: Run router tests and confirm failure**

Run `python3 -m unittest tests.test_keenetic_awg3_router -v`. Expected: new AWG
tests FAIL because the scripts do not exist.

- [ ] **Step 3: Implement per-device backup without secret output**

`backup-router.sh` creates a mode-700 local directory, remotely packages
`/opt/etc/awg-manager`, `/opt/etc/init.d/S99awg-manager`, NDMS hooks and
`opkg list-installed`, then downloads the archive. It never prints file
contents. It records archive SHA-256 and a redacted system report. If tunnel
private keys are present, mark the archive `sensitive=true`, chmod 600, and
require the output root to be outside Git.

- [ ] **Step 4: Implement pinned AWG install and failure collection**

Preflight requires exact installed versions of the four dependencies, at least
64 MiB free, successful backup, and locked IPK hash. Require:

```text
INSTALL AWG-MANAGER 2.16.5 hopper-main <ipk-sha256>
```

Upload to `/opt/tmp`, verify SHA-256 again on the router, run
`/opt/bin/opkg install /opt/tmp/awg-manager_2.16.5_aarch64-3.10-kn.ipk`, and
delete only the uploaded temporary IPK. If install/start fails, collect service
status, process list, `/opt/var/log`, module hashes, `lsmod` and `dmesg`; do not
call `opkg remove`, `--cleanup`, reboot or delete tunnels automatically.

- [ ] **Step 5: Implement verification**

`verify-router.sh` checks:

```sh
/opt/etc/init.d/S99awg-manager status
/opt/bin/opkg status awg-manager
cat /opt/etc/awg-manager/modules/bundled/version
lsmod
/opt/sbin/awg --version
/opt/bin/wg --version
```

From the Mac, verify TCP 2222 is reachable at the LAN address and explicitly
test the WAN address is not reachable when a WAN address is supplied in the
local profile. After the user creates/imports a tunnel in the UI, a second mode
checks AWG handshake, route state, DNS/internet access and a soft
`S99awg-manager restart`; it does not modify routing policy itself.

- [ ] **Step 6: Run router tests**

Run `python3 -m unittest tests.test_keenetic_awg3_router -v`. Expected: PASS,
including redaction and no-cleanup assertions.

- [ ] **Step 7: Commit AWG deployment**

```bash
git add tools/keenetic-awg3/scripts/backup-router.sh \
  tools/keenetic-awg3/scripts/install-awg-manager.sh \
  tools/keenetic-awg3/scripts/verify-router.sh \
  tests/test_keenetic_awg3_router.py
git commit -m "feat(keenetic): устанавливать и проверять AWG Manager"
```

### Task 7: Operator runbook and full acceptance gates

**Files:**
- Create: `tools/keenetic-awg3/README.md`
- Modify: `README.md`
- Modify: `tests/test_keenetic_awg3_artifacts.py`
- Modify: `tests/test_keenetic_awg3_card.py`
- Modify: `tests/test_keenetic_awg3_router.py`

**Risk/capability:** A future operator can repeat preparation, installation, backup, update and disaster recovery without prior chat history or Windows/Linux.

**Primary proof:** Full automated suite plus a documented two-device manual acceptance checklist whose evidence is stored outside Git.

- [ ] **Step 1: Write the runbook**

Document bounded flows in this order:

1. prerequisites and hardware;
2. `inspect-card` then `prepare-card`;
3. artifact fetch/audit and human approval;
4. personalized offline bundle build;
5. router preflight and Entware bootstrap;
6. root key-only SSH verification;
7. sanitized golden image creation and unique-host-key regeneration check;
8. config backup and AWG Manager install;
9. UI tunnel import and service-restart verification;
10. per-device backup;
11. update-by-new-lock flow;
12. fsck/restore incident flow;
13. disable native SFTP and rotate the temporary admin password.

Every destructive example uses a visibly fake `/dev/diskN`, never a copied
real identifier. State that `e2image` is diagnostic while `partition.raw.gz` is
the complete restore artifact. State that no script installs KeeneticOS
components or reboots the router.

- [ ] **Step 2: Add final contract assertions**

Add tracked-file secret scans using representative forbidden private-key
headers and known temporary-password labels, excluding fixtures that contain
only redacted tokens. Add an end-to-end dry-run test that assembles a bundle,
classifies a fake fresh router, records the approved upload/install sequence,
then verifies a fake AWG 3 service.

- [ ] **Step 3: Run all repository verification**

```bash
python3 -m unittest discover -s tests -v
python3 -m compileall -q scripts tests
git diff --check
```

Expected: all tests PASS, compileall exits 0, and `git diff --check` is silent.

- [ ] **Step 4: Run non-destructive live preflight**

With a local ignored profile and the current router reachable:

```bash
tools/keenetic-awg3/scripts/preflight-router.sh \
  tools/keenetic-awg3/local/hopper-main.env
```

Expected: correct model/architecture, no mutation commands, and a redacted
report. Stop here if the new endurance card and reviewed artifact cache are not
ready.

- [ ] **Step 5: Execute hardware acceptance only after both gates**

On the new endurance card and current router, preserve evidence for each
outcome: clean `e2fsck -fn`, stable `/opt`, root key-only reconnect, AWG Manager
2.16.5, bundle `3.0.20260731-04`, LAN-only port 2222, AWG handshake, service
restart recovery, spare-card restore, native SFTP disabled and admin password
rotated. Repeat restore/bootstrap verification with a separate local profile
and keys for the second device.

- [ ] **Step 6: Commit documentation and final test adjustments**

```bash
git add README.md tools/keenetic-awg3/README.md \
  tests/test_keenetic_awg3_artifacts.py tests/test_keenetic_awg3_card.py \
  tests/test_keenetic_awg3_router.py
git commit -m "docs(keenetic): описать повторную установку AWG3"
```

## Completion report

Report verification by category, not only test count:

- card safety: rejected targets and exact sparse-image layout;
- artifact integrity: package count, lock validation, audit review and bundle hash;
- recovery: raw-image round trip and clean ext4 check;
- router safety: model/state classification, explicit mutation gates and redaction;
- deployment: Entware key-only SSH, pinned AWG 3 service and LAN-only UI;
- manual hardware evidence: handshake, soft restart and spare-card restore.

Do not report completion until the spare-card restore has actually been tested.

## Appendix A: exact artifact lock content

Create `artifacts.lock` with this reviewed content. Long lines are intentional;
the file is machine-validated and not reformatted:

```text
repo|package|version|architecture|size|sha256|url
entware-installer|aarch64-installer|2026-04-06|aarch64-k3.10|3232671|64451a3a70ca85aaab3b0677814f6b58f7994793ed6b120eddc36a16639c15d1|https://bin.entware.net/aarch64-k3.10/installer/aarch64-installer.tar.gz
entware-main|busybox|1.37.0-6|aarch64-3.10|332233|881b06cecc1c8c6b4a0658d551c2230034ea0a21354fab89ddbce744f3d51e24|https://bin.entware.net/aarch64-k3.10/busybox_1.37.0-6_aarch64-3.10.ipk
entware-main|conntrack|1.4.8-1|aarch64-3.10|30003|64fb1b337a3517481c717f17f736437642c48ecfc5df02f2c1be473739eb7416|https://bin.entware.net/aarch64-k3.10/conntrack_1.4.8-1_aarch64-3.10.ipk
entware-main|dropbear|2025.89-1|aarch64-3.10|116840|00b2005611370cc20b432292dc06e0bce6b4d666b62e78ca96242d5bfa0bd6a4|https://bin.entware.net/aarch64-k3.10/dropbear_2025.89-1_aarch64-3.10.ipk
entware-main|entware-release|2025.05-1|all|1068|fe26b5b90f7293319240e2e79cef353d815a6d3f21a26c91c326ca32bf43d420|https://bin.entware.net/aarch64-k3.10/entware-release_2025.05-1_all.ipk
entware-main|findutils|4.10.0-1|aarch64-3.10|175446|6f1ad0782d550a855da202e44c147fa20c822787325a4e714774d088ad99f347|https://bin.entware.net/aarch64-k3.10/findutils_4.10.0-1_aarch64-3.10.ipk
entware-main|grep|3.12-1|aarch64-3.10|118174|9571ab23c52da17977522274e447d0d5eeca8ea9ded329cab6e9a46cef24f3a3|https://bin.entware.net/aarch64-k3.10/grep_3.12-1_aarch64-3.10.ipk
entware-main|ip-full|4.4.0-11|aarch64-3.10|158925|9a60053e170ca1395fea512bf57b978ebf21b39f734010d6e9f40fee745683b1|https://bin.entware.net/aarch64-k3.10/ip-full_4.4.0-11_aarch64-3.10.ipk
entware-keenetic|iptables|1.4.21-6|aarch64-3.10_kn|203022|87f9bf7c2edfc34f5f9d42632d399a29766503d644f1018cbba92526cce5a7ca|https://bin.entware.net/aarch64-k3.10/keenetic/iptables_1.4.21-6_aarch64-3.10_kn.ipk
entware-main|ldconfig|2.27-12|aarch64-3.10|277427|f65b320c7fa2700d0c04505aa117dc34caadb798859a2f57aef393aff9a76519|https://bin.entware.net/aarch64-k3.10/ldconfig_2.27-12_aarch64-3.10.ipk
entware-main|libc|2.27-12|aarch64-3.10|1367072|4d7825a9ddf7a382a985a44ec85c4ab458f8ebe12c3e3b5fb25da814f71167bb|https://bin.entware.net/aarch64-k3.10/libc_2.27-12_aarch64-3.10.ipk
entware-main|libgcc|8.4.0-12|aarch64-3.10|36583|123882cd0063342b8cd058ea97541601d793ef1f847920e1da6be4c3a0b8da8b|https://bin.entware.net/aarch64-k3.10/libgcc_8.4.0-12_aarch64-3.10.ipk
entware-main|libmnl|1.0.5-1|aarch64-3.10|9265|20875d83b957cd3fa1549f743b986da1939c778850087d61c479549b22d6a77c|https://bin.entware.net/aarch64-k3.10/libmnl_1.0.5-1_aarch64-3.10.ipk
entware-main|libnetfilter-conntrack|1.1.0-1|aarch64-3.10|45435|e6e1a51bb0b2deb72af959e2f6b850b8e470742dda135c08f807d2437b6d9978|https://bin.entware.net/aarch64-k3.10/libnetfilter-conntrack_1.1.0-1_aarch64-3.10.ipk
entware-main|libnetfilter-cthelper|1.0.0-2|aarch64-3.10|5737|0830126bfe62567190bc9750e4902e8be75d5993d08f6c17c09b104cb28cc2ff|https://bin.entware.net/aarch64-k3.10/libnetfilter-cthelper_1.0.0-2_aarch64-3.10.ipk
entware-main|libnetfilter-cttimeout|1.0.0-2|aarch64-3.10|5754|e3dc32db80cb455df589e543f5abd45d58e4da8c856c5e9881d7595d2482125d|https://bin.entware.net/aarch64-k3.10/libnetfilter-cttimeout_1.0.0-2_aarch64-3.10.ipk
entware-main|libnetfilter-queue|1.0.5-4|aarch64-3.10|11828|6f5f0abe335b47d606a6e4d9a8d93ba9127f00e2a87fbc3af0de14647a72ae94|https://bin.entware.net/aarch64-k3.10/libnetfilter-queue_1.0.5-4_aarch64-3.10.ipk
entware-main|libnfnetlink|1.0.2-1|aarch64-3.10|12864|18c1b6ec1baed5c03cfd8e29368accbf63f39ad0efdf3fb008e087a284a84038|https://bin.entware.net/aarch64-k3.10/libnfnetlink_1.0.2-1_aarch64-3.10.ipk
entware-main|libnl-tiny|2025.12.02~40493a65-1|aarch64-3.10|18876|3bf53563ccadcbee520177bf3b601f807748819a277559dd8b5bf48f394a8d13|https://bin.entware.net/aarch64-k3.10/libnl-tiny_2025.12.02~40493a65-1_aarch64-3.10.ipk
entware-main|libpcre2|10.47-1|aarch64-3.10|250186|177e0ac6a084c81a2731e99b0c386989752482a52068f16f3024eb67db3f6e92|https://bin.entware.net/aarch64-k3.10/libpcre2_10.47-1_aarch64-3.10.ipk
entware-main|libpthread|2.27-12|aarch64-3.10|44699|a2af364e6e139069f8b37dd9e7f2accaf529efd35738c6d381d2e43e78b876d4|https://bin.entware.net/aarch64-k3.10/libpthread_2.27-12_aarch64-3.10.ipk
entware-main|librt|2.27-12|aarch64-3.10|13307|86d4adc05b939793f4fb7d54ecc6c34b867a1fe9c449983393f708f245b72b43|https://bin.entware.net/aarch64-k3.10/librt_2.27-12_aarch64-3.10.ipk
entware-main|libssp|8.4.0-12|aarch64-3.10|4092|8d85e466962569005ec604a64b2ffa739454a9db017a9a5e8dbe23b3c4bf2c25|https://bin.entware.net/aarch64-k3.10/libssp_8.4.0-12_aarch64-3.10.ipk
entware-main|libstdcpp|8.4.0-12|aarch64-3.10|389225|7b945502a7e7eef3e172b0343a533f4cce71db1579a372a4cee6e4c209b1bdc1|https://bin.entware.net/aarch64-k3.10/libstdcpp_8.4.0-12_aarch64-3.10.ipk
entware-main|locales|2.27-9|aarch64-3.10|651064|ee71c45537ad26b3a2abdd09fe252fc50b31de49e2aa93f55e741dfc3e5a4413|https://bin.entware.net/aarch64-k3.10/locales_2.27-9_aarch64-3.10.ipk
entware-main|opkg|2025.11.05~80503d94-1|aarch64-3.10|421511|872821cc70fdd3b550b4458c056ad1a5c61edbfb9981b73b68c4b6644085cd73|https://bin.entware.net/aarch64-k3.10/opkg_2025.11.05~80503d94-1_aarch64-3.10.ipk
entware-keenetic|opt-ndmsv2|1.0-17|aarch64-3.10_kn|3776|d0268a72c54e4a7343e3462ed8503332f0a0130c6998cf3944f51de29f2dae9a|https://bin.entware.net/aarch64-k3.10/keenetic/opt-ndmsv2_1.0-17_aarch64-3.10_kn.ipk
entware-keenetic|poorbox|1.37.0-2|aarch64-3.10_kn|484820|d93aba9b525748da7867cff0242079715ded6eed36732746c9dea9a2c8497517|https://bin.entware.net/aarch64-k3.10/keenetic/poorbox_1.37.0-2_aarch64-3.10_kn.ipk
entware-main|terminfo|6.4-3|aarch64-3.10|9664|ec0fa04fcaa9485968eb3321e7820ff3f80874798fdb19d79718606dd759405a|https://bin.entware.net/aarch64-k3.10/terminfo_6.4-3_aarch64-3.10.ipk
entware-main|wireguard-tools|1.0.20250521-1|aarch64-3.10|45015|1f7116af5e480eb546e38fa334f5992931f00f352b3e39e6fa7fd76d71116f33|https://bin.entware.net/aarch64-k3.10/wireguard-tools_1.0.20250521-1_aarch64-3.10.ipk
entware-main|zoneinfo-asia|2025c-1|aarch64-3.10|31032|f55841a75671c7c8d93880f5d6de3936b02e945f83b7fce096c164a7e8db4ae1|https://bin.entware.net/aarch64-k3.10/zoneinfo-asia_2025c-1_aarch64-3.10.ipk
entware-main|zoneinfo-core|2025c-1|aarch64-3.10|24416|30708ce57de9354022d30aebfe5ede68387a26c5cc46869513d65b15bc27d004|https://bin.entware.net/aarch64-k3.10/zoneinfo-core_2025c-1_aarch64-3.10.ipk
entware-main|zoneinfo-europe|2025c-1|aarch64-3.10|22257|1640940aa4b063bcc015014e15471e3e4d8db14f49349cf05ad41951dd9b9d00|https://bin.entware.net/aarch64-k3.10/zoneinfo-europe_2025c-1_aarch64-3.10.ipk
hoaxisr|awg-manager|2.16.5|aarch64-3.10|10904643|1b841747a85dda101e5d9be0b647c84275f354fc51b41d71b26e684f44f19b12|https://repo.hoaxisr.ru/aarch64-k3.10/awg-manager_2.16.5_aarch64-3.10-kn.ipk
```

Create `entware-install-order.txt` with these exact 32 filenames:

```text
libgcc_8.4.0-12_aarch64-3.10.ipk
libssp_8.4.0-12_aarch64-3.10.ipk
libc_2.27-12_aarch64-3.10.ipk
libpthread_2.27-12_aarch64-3.10.ipk
librt_2.27-12_aarch64-3.10.ipk
libstdcpp_8.4.0-12_aarch64-3.10.ipk
libpcre2_10.47-1_aarch64-3.10.ipk
libnl-tiny_2025.12.02~40493a65-1_aarch64-3.10.ipk
libmnl_1.0.5-1_aarch64-3.10.ipk
libnfnetlink_1.0.2-1_aarch64-3.10.ipk
libnetfilter-conntrack_1.1.0-1_aarch64-3.10.ipk
libnetfilter-cthelper_1.0.0-2_aarch64-3.10.ipk
libnetfilter-cttimeout_1.0.0-2_aarch64-3.10.ipk
libnetfilter-queue_1.0.5-4_aarch64-3.10.ipk
conntrack_1.4.8-1_aarch64-3.10.ipk
terminfo_6.4-3_aarch64-3.10.ipk
grep_3.12-1_aarch64-3.10.ipk
findutils_4.10.0-1_aarch64-3.10.ipk
locales_2.27-9_aarch64-3.10.ipk
zoneinfo-core_2025c-1_aarch64-3.10.ipk
zoneinfo-asia_2025c-1_aarch64-3.10.ipk
zoneinfo-europe_2025c-1_aarch64-3.10.ipk
entware-release_2025.05-1_all.ipk
ldconfig_2.27-12_aarch64-3.10.ipk
opkg_2025.11.05~80503d94-1_aarch64-3.10.ipk
busybox_1.37.0-6_aarch64-3.10.ipk
poorbox_1.37.0-2_aarch64-3.10_kn.ipk
dropbear_2025.89-1_aarch64-3.10.ipk
ip-full_4.4.0-11_aarch64-3.10.ipk
wireguard-tools_1.0.20250521-1_aarch64-3.10.ipk
iptables_1.4.21-6_aarch64-3.10_kn.ipk
opt-ndmsv2_1.0-17_aarch64-3.10_kn.ipk
```
