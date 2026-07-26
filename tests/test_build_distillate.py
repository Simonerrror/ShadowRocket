from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts.build_distillate import (
    GEOIP_DATA_COMMIT,
    GEOIP_DATA_SHA256,
    GEOIP_COMMIT,
    GEOSITE_COMMIT,
    CategoryResult,
    DistillateError,
    build_distillate,
    checkout_pinned_repo,
    compiled_geosite_tags,
    geoip_compiler_inputs,
    publish_staged_outputs,
    verify_ru_geoip_source,
)


class BuildDistillateSafetyTests(unittest.TestCase):
    def test_failed_staged_build_keeps_existing_outputs(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "distillate/text/domain").mkdir(parents=True)
            (root / "distillate/dat").mkdir(parents=True)
            (root / "rules").mkdir()
            (root / "modules").mkdir()
            (root / "distillate/manifest.json").write_text(
                json.dumps({"categories": [{"name": "sample", "publish": True}]}),
                encoding="utf-8",
            )
            sentinels = {
                root / "distillate/text/domain/old.txt": "old text\n",
                root / "distillate/dat/geosite.dat": "old dat\n",
                root / "rules/old.list": "old rule\n",
                root / "modules/anti_advertising.module": "old module\n",
            }
            for path, content in sentinels.items():
                path.write_text(content, encoding="utf-8")

            with patch(
                "scripts.build_distillate._build_distillate_in_place",
                side_effect=DistillateError("injected failure"),
            ):
                with self.assertRaisesRegex(DistillateError, "injected failure"):
                    build_distillate(root, root / "distillate/manifest.json", skip_compiled=False)

            for path, content in sentinels.items():
                self.assertEqual(path.read_text(encoding="utf-8"), content)

    def test_compiler_commits_are_reviewed_immutable_shas(self) -> None:
        self.assertEqual(GEOSITE_COMMIT, "bb622a2b75b3dfbec83719c1eb6e748720ea698e")
        self.assertEqual(GEOIP_COMMIT, "fbeec6d51a544ba4c19d75cf04260f74c965fbd7")

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

            with self.assertRaisesRegex(DistillateError, "checksum mismatch"):
                verify_ru_geoip_source(path)

    def test_compiled_geosite_tags_include_category_ru(self) -> None:
        tags = compiled_geosite_tags({"sr-direct": CategoryResult("sr-direct")})

        self.assertEqual(tags, ["category-ru", "sr-direct"])

    def test_geoip_inputs_import_ru_from_cached_v2fly_dat(self) -> None:
        inputs, wanted = geoip_compiler_inputs(Path("/repo"), {})

        self.assertEqual(inputs[0]["type"], "v2rayGeoIPDat")
        self.assertEqual(inputs[0]["args"]["wantedList"], ["ru"])
        self.assertEqual(inputs[0]["args"]["uri"], "/repo/distillate/upstream/v2fly/geoip.dat")
        self.assertIn("ru", wanted)

    def test_publish_failure_restores_every_replaced_output(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            base = Path(tmpdir)
            root = base / "root"
            staging = base / "staging"
            for target in (root, staging):
                (target / "distillate/text/domain").mkdir(parents=True)
            (root / "distillate/summary.json").write_text("old summary\n", encoding="utf-8")
            (root / "distillate/text/domain/sample.txt").write_text("old text\n", encoding="utf-8")
            (staging / "distillate/summary.json").write_text("new summary\n", encoding="utf-8")
            (staging / "distillate/text/domain/sample.txt").write_text("new text\n", encoding="utf-8")

            original_replace = Path.replace
            injected = False

            def flaky_replace(path: Path, target: Path) -> Path:
                nonlocal injected
                if path == staging / "distillate/text" and not injected:
                    injected = True
                    raise OSError("injected publish failure")
                return original_replace(path, target)

            with patch("pathlib.Path.replace", new=flaky_replace):
                with self.assertRaisesRegex(OSError, "injected publish failure"):
                    publish_staged_outputs(
                        root,
                        staging,
                        {"categories": []},
                        skip_compiled=True,
                    )

            self.assertEqual((root / "distillate/summary.json").read_text(), "old summary\n")
            self.assertEqual((root / "distillate/text/domain/sample.txt").read_text(), "old text\n")

    @patch("scripts.build_distillate.run")
    @patch("scripts.build_distillate.run_with_retry")
    def test_checkout_fetches_and_detaches_exact_commit(self, mock_retry: object, mock_run: object) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            destination = Path(tmpdir) / "repo"
            checkout_pinned_repo("https://github.com/example/repo.git", "a" * 40, destination)

        commands = [call.args[0] for call in mock_retry.call_args_list]
        self.assertIn(
            ["git", "clone", "--no-checkout", "--filter=blob:none", "https://github.com/example/repo.git", str(destination)],
            commands,
        )
        self.assertIn(["git", "-C", str(destination), "fetch", "--depth", "1", "origin", "a" * 40], commands)
        mock_run.assert_called_once_with(["git", "-C", str(destination), "checkout", "--detach", "FETCH_HEAD"])


if __name__ == "__main__":
    unittest.main()
