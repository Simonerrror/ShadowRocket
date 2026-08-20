from __future__ import annotations

import unittest
from pathlib import Path

from scripts.validate_publish_paths import is_allowed_publish_path


REPO_ROOT = Path(__file__).resolve().parents[1]
SYNC_WORKFLOW = REPO_ROOT / ".github/workflows/sync-lists.yml"
VERIFY_WORKFLOW = REPO_ROOT / ".github/workflows/build-happ-routing.yml"
DEPLOY_WORKFLOW = REPO_ROOT / ".github/workflows/deploy-potato-link.yml"

ACTION_PINS = (
    "actions/checkout@34e114876b0b11c390a56381ad16ebd13914f8d5",
    "actions/setup-python@a26af69be951a213d495a4c3e4e4022e16d87065",
    "actions/setup-go@40f1582b2485089dde7abd97c1529aa768e1baff",
    "actions/upload-artifact@ea165f8d65b6e75b540449e92b4886f43607fa02",
    "actions/download-artifact@d3f86a106a0bac45b974a628896c90dbdf5c8093",
    "actions/setup-node@48b55a011bda9f5d6aeb4c2d9c7362e8dae4041e",
)


class WorkflowHardeningTests(unittest.TestCase):
    def test_sync_workflow_separates_read_build_from_write_publish(self) -> None:
        content = SYNC_WORKFLOW.read_text(encoding="utf-8")

        self.assertIn("allow_large_diff:", content)
        self.assertIn("concurrency:", content)
        self.assertIn("build:\n    permissions:\n      contents: read", content)
        self.assertIn("persist-credentials: false", content)
        self.assertIn("publish:\n    needs: build\n    permissions:\n      contents: write", content)
        self.assertIn("notify:\n    needs: [build, publish]", content)
        self.assertIn("issues: write", content)
        self.assertIn('go-version: "1.25.11"', content)
        self.assertIn("if git diff --quiet -- distillate rules modules Amnezia clash_config.yaml", content)
        self.assertIn("python3 scripts/build_amnezia_routing.py", content)
        self.assertIn("Amnezia/SR-DEFAULT-EXCLUDE.json", content)
        self.assertIn("Amnezia/SR-DEFAULT-EXCLUDE.summary.json", content)
        self.assertIn("python3 -m unittest discover -s tests -v", content)
        self.assertLess(content.index("python3 -m unittest discover"), content.index("actions/upload-artifact@"))
        self.assertNotIn("git push\n", content.split("  build:", 1)[1].split("  publish:", 1)[0])

    def test_workflows_pin_every_action_to_reviewed_sha(self) -> None:
        combined = (
            SYNC_WORKFLOW.read_text(encoding="utf-8")
            + VERIFY_WORKFLOW.read_text(encoding="utf-8")
            + DEPLOY_WORKFLOW.read_text(encoding="utf-8")
        )

        for pin in ACTION_PINS:
            with self.subTest(pin=pin):
                if pin.startswith(("actions/upload-artifact", "actions/download-artifact")):
                    self.assertIn(pin, SYNC_WORKFLOW.read_text(encoding="utf-8"))
                else:
                    self.assertIn(pin, combined)
        self.assertNotRegex(combined, r"uses: actions/[^@]+@v\d")

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
        self.assertNotRegex(content, r"uses: actions/[^@]+@v\d")

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
            with self.subTest(required=required):
                self.assertIn(required, content)
        self.assertNotIn("CLOUDFLARE_API_TOKEN", verify)
        self.assertIn("needs: verify", deploy)
        self.assertIn("github.event.workflow_run.conclusion == 'success'", deploy)
        self.assertIn("github.ref == 'refs/heads/main'", deploy)
        self.assertIn(
            "CLOUDFLARE_API_TOKEN: ${{ secrets.CLOUDFLARE_API_TOKEN }}",
            deploy,
        )
        self.assertIn(
            "CLOUDFLARE_ACCOUNT_ID: ${{ secrets.CLOUDFLARE_ACCOUNT_ID }}",
            deploy,
        )

    def test_release_workflows_regenerate_embedded_destinations(self) -> None:
        sync = SYNC_WORKFLOW.read_text(encoding="utf-8")
        verify = VERIFY_WORKFLOW.read_text(encoding="utf-8")
        generated = "cloudflare/potato-link/dist/destinations.js"

        self.assertIn("python3 scripts/build_potato_link_worker.py", sync)
        self.assertIn("python3 scripts/build_potato_link_worker.py", verify)
        self.assertIn("python3 scripts/build_amnezia_routing.py", sync)
        self.assertIn("python3 scripts/build_amnezia_routing.py", verify)
        self.assertIn(generated, sync)
        self.assertTrue(is_allowed_publish_path(generated))

    def test_release_workflows_build_and_publish_incy_artifacts(self) -> None:
        sync = SYNC_WORKFLOW.read_text(encoding="utf-8")
        verify = VERIFY_WORKFLOW.read_text(encoding="utf-8")
        deploy = DEPLOY_WORKFLOW.read_text(encoding="utf-8")

        for content in (sync, verify):
            with self.subTest(content="workflow build"):
                self.assertIn("python3 scripts/build_incy_routing.py", content)
        for path in ("INCY/DEFAULT.JSON", "INCY/RU-VPN.DEEPLINK"):
            with self.subTest(path=path):
                self.assertIn(path, sync)
        self.assertIn('"INCY/**"', verify)
        for path in (
            '"INCY/DEFAULT.DEEPLINK"',
            '"INCY/RU-VPN.DEEPLINK"',
        ):
            with self.subTest(path=path):
                self.assertIn(path, deploy)

    def test_sync_workflow_publishes_incy_geodata_release_assets(self) -> None:
        content = SYNC_WORKFLOW.read_text(encoding="utf-8")

        self.assertIn("gh release upload incy-geodata", content)
        for path in (
            "distillate/dat/geoip.dat",
            "distillate/dat/geoip.dat.sha256",
            "distillate/dat/geosite.dat",
            "distillate/dat/geosite.dat.sha256",
        ):
            with self.subTest(path=path):
                self.assertIn(path, content)
        self.assertIn("--clobber", content)

    def test_publish_path_allowlist_accepts_incy_generated_outputs(self) -> None:
        for path in (
            "INCY/DEFAULT.JSON",
            "INCY/DEFAULT.DEEPLINK",
            "INCY/RU-VPN.JSON",
            "INCY/RU-VPN.DEEPLINK",
        ):
            with self.subTest(path=path):
                self.assertTrue(is_allowed_publish_path(path))

    def test_verification_workflow_is_read_only(self) -> None:
        content = VERIFY_WORKFLOW.read_text(encoding="utf-8")

        self.assertIn("permissions:\n  contents: read", content)
        self.assertIn("persist-credentials: false", content)
        self.assertIn("git diff --exit-code", content)
        self.assertNotIn("git push", content)
        self.assertNotIn("contents: write", content)

    def test_workflows_cover_ru_vpn_artifacts(self) -> None:
        sync_content = SYNC_WORKFLOW.read_text(encoding="utf-8")
        verify_content = VERIFY_WORKFLOW.read_text(encoding="utf-8")

        self.assertIn('- "HAPP/**"', verify_content)
        for path in ("HAPP/RU-VPN.JSON", "HAPP/RU-VPN.DEEPLINK"):
            with self.subTest(path=path):
                self.assertIn(path, sync_content)

    def test_publish_path_allowlist_accepts_only_generated_outputs(self) -> None:
        allowed = (
            "distillate/upstream/bm7/Google.list",
            "distillate/text/domain/google.txt",
            "distillate/dat/geosite.dat",
            "distillate/summary.json",
            "rules/google-all.list",
            "rules/anti_advertising.04.list",
            "modules/anti_advertising.module",
            "clash_config.yaml",
            "HAPP/DEFAULT.JSON",
            "HAPP/RU-VPN.JSON",
            "HAPP/RU-VPN.DEEPLINK",
            "INCY/DEFAULT.JSON",
            "INCY/DEFAULT.DEEPLINK",
            "INCY/RU-VPN.JSON",
            "INCY/RU-VPN.DEEPLINK",
            "distillate/upstream/v2fly/ru_ipv4.txt",
            "Amnezia/SR-DEFAULT-EXCLUDE.json",
            "Amnezia/SR-DEFAULT-EXCLUDE.summary.json",
        )
        denied = (
            "scripts/build_distillate.py",
            "distillate/manifest.json",
            "distillate/overlays/ru_direct.add.list",
            "rules/adobe_telemetry_custom.list",
            ".github/workflows/sync-lists.yml",
            "../distillate/text/domain/google.txt",
            "/tmp/distillate/text/domain/google.txt",
            "Amnezia/other.json",
        )

        for path in allowed:
            with self.subTest(path=path):
                self.assertTrue(is_allowed_publish_path(path))
        for path in denied:
            with self.subTest(path=path):
                self.assertFalse(is_allowed_publish_path(path))


if __name__ == "__main__":
    unittest.main()
