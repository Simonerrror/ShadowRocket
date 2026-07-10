from __future__ import annotations

import unittest
from pathlib import Path

from scripts.validate_publish_paths import is_allowed_publish_path


REPO_ROOT = Path(__file__).resolve().parents[1]
SYNC_WORKFLOW = REPO_ROOT / ".github/workflows/sync-lists.yml"
VERIFY_WORKFLOW = REPO_ROOT / ".github/workflows/build-happ-routing.yml"

ACTION_PINS = (
    "actions/checkout@34e114876b0b11c390a56381ad16ebd13914f8d5",
    "actions/setup-python@a26af69be951a213d495a4c3e4e4022e16d87065",
    "actions/setup-go@40f1582b2485089dde7abd97c1529aa768e1baff",
    "actions/upload-artifact@ea165f8d65b6e75b540449e92b4886f43607fa02",
    "actions/download-artifact@d3f86a106a0bac45b974a628896c90dbdf5c8093",
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
        self.assertIn("if git diff --quiet -- distillate rules modules clash_config.yaml", content)
        self.assertIn("python3 -m unittest discover -s tests -v", content)
        self.assertLess(content.index("python3 -m unittest discover"), content.index("actions/upload-artifact@"))
        self.assertNotIn("git push\n", content.split("  build:", 1)[1].split("  publish:", 1)[0])

    def test_workflows_pin_every_action_to_reviewed_sha(self) -> None:
        combined = SYNC_WORKFLOW.read_text(encoding="utf-8") + VERIFY_WORKFLOW.read_text(encoding="utf-8")

        for pin in ACTION_PINS:
            with self.subTest(pin=pin):
                if pin.startswith(("actions/upload-artifact", "actions/download-artifact")):
                    self.assertIn(pin, SYNC_WORKFLOW.read_text(encoding="utf-8"))
                else:
                    self.assertIn(pin, combined)
        self.assertNotRegex(combined, r"uses: actions/[^@]+@v\d")

    def test_verification_workflow_is_read_only(self) -> None:
        content = VERIFY_WORKFLOW.read_text(encoding="utf-8")

        self.assertIn("permissions:\n  contents: read", content)
        self.assertIn("persist-credentials: false", content)
        self.assertIn("git diff --exit-code", content)
        self.assertNotIn("git push", content)
        self.assertNotIn("contents: write", content)

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
        )
        denied = (
            "scripts/build_distillate.py",
            "distillate/manifest.json",
            "distillate/overlays/ru_direct.add.list",
            "rules/adobe_telemetry_custom.list",
            ".github/workflows/sync-lists.yml",
            "../distillate/text/domain/google.txt",
            "/tmp/distillate/text/domain/google.txt",
        )

        for path in allowed:
            with self.subTest(path=path):
                self.assertTrue(is_allowed_publish_path(path))
        for path in denied:
            with self.subTest(path=path):
                self.assertFalse(is_allowed_publish_path(path))


if __name__ == "__main__":
    unittest.main()
