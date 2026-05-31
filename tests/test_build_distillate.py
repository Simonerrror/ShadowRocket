from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts import build_distillate as distillate


class BuildDistillateTests(unittest.TestCase):
    def test_repository_manifest_defines_supported_anti_advertising_tiers(self) -> None:
        repo_root = Path(__file__).resolve().parents[1]
        manifest = json.loads((repo_root / "distillate" / "manifest.json").read_text(encoding="utf-8"))
        categories = {category["name"]: category for category in manifest["categories"]}

        expected_tiers = {
            "anti_advertising_light": (
                "rules/anti_advertising_light.list",
                "distillate/upstream/external/hagezi_light_onlydomains.txt",
            ),
            "anti_advertising_medium": (
                "rules/anti_advertising_medium.list",
                "distillate/upstream/external/hagezi_multi_onlydomains.txt",
            ),
            "anti_advertising_pro": (
                "rules/anti_advertising_pro.list",
                "distillate/upstream/external/hagezi_pro_onlydomains.txt",
            ),
            "anti_advertising_pro_plus": (
                "rules/anti_advertising_pro_plus.list",
                "distillate/upstream/external/hagezi_pro_plus_onlydomains.txt",
            ),
        }

        for tier_name, (legacy_rule_path, hagezi_cache_path) in expected_tiers.items():
            tier = categories[tier_name]
            self.assertTrue(tier["publish"])
            self.assertFalse(tier["compiled"])
            self.assertEqual(tier["legacy_rule_path"], legacy_rule_path)
            self.assertEqual(
                [source["cache_path"] for source in tier["sources"]],
                [
                    "distillate/upstream/external/oisd_small_surge.list",
                    hagezi_cache_path,
                ],
            )
            self.assertTrue((repo_root / "modules" / f"{tier_name}.module").exists())
            self.assertTrue((repo_root / "modules" / f"{tier_name}_custom.module").exists())

    def test_rewrites_custom_anti_advertising_tier_modules_from_shared_header(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            repo_root = Path(tmp_dir)
            rules_dir = repo_root / "rules"
            modules_dir = repo_root / "modules"
            rules_dir.mkdir(parents=True)
            modules_dir.mkdir(parents=True)
            (rules_dir / "anti_advertising.01.list").write_text("DOMAIN-SUFFIX,ads.example\n", encoding="utf-8")
            (rules_dir / "anti_advertising_light.list").write_text(
                "DOMAIN-SUFFIX,light-ads.example\n",
                encoding="utf-8",
            )
            (rules_dir / "anti_advertising_pro.list").write_text(
                "DOMAIN-SUFFIX,pro-ads.example\n",
                encoding="utf-8",
            )
            (rules_dir / "anti_advertising_pro.01.list").write_text(
                "DOMAIN-SUFFIX,pro-ads.example\n",
                encoding="utf-8",
            )
            (modules_dir / "anti_advertising_custom.header").write_text(
                "DOMAIN-KEYWORD,nvidia,DIRECT\n"
                "RULE-SET, https://raw.githubusercontent.com/Simonerrror/ShadowRocket/main/rules/adobe_telemetry_custom.list,REJECT\n",
                encoding="utf-8",
            )

            distillate.rewrite_anti_ad_modules(repo_root)

            full_custom = (modules_dir / "anti_advertising_custom.module").read_text(encoding="utf-8")
            light_custom = (modules_dir / "anti_advertising_light_custom.module").read_text(encoding="utf-8")
            pro_module = (modules_dir / "anti_advertising_pro.module").read_text(encoding="utf-8")

            self.assertIn("DOMAIN-KEYWORD,nvidia,DIRECT", full_custom)
            self.assertIn("adobe_telemetry_custom.list,REJECT", full_custom)
            self.assertIn("anti_advertising.01.list,REJECT", full_custom)
            self.assertNotIn("anti_advertising.list,REJECT", full_custom)

            self.assertIn("DOMAIN-KEYWORD,nvidia,DIRECT", light_custom)
            self.assertIn("adobe_telemetry_custom.list,REJECT", light_custom)
            self.assertIn("anti_advertising_light.list,REJECT", light_custom)
            self.assertNotIn("anti_advertising.01.list,REJECT", light_custom)
            self.assertIn("anti_advertising_pro.01.list,REJECT", pro_module)
            self.assertNotIn("anti_advertising_pro.list,REJECT", pro_module)

    def test_prunes_domain_rules_already_covered_by_parent_suffix(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            repo_root = Path(tmp_dir)
            manifest_path = repo_root / "distillate" / "manifest.json"
            manifest_path.parent.mkdir(parents=True)
            manifest_path.write_text(
                json.dumps(
                    {
                        "categories": [
                            {
                                "name": "sample",
                                "publish": True,
                                "legacy_rule_path": "rules/sample.list",
                                "overlays": {"add": "distillate/overlays/sample.add.list"},
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )
            overlay_path = repo_root / "distillate" / "overlays" / "sample.add.list"
            overlay_path.parent.mkdir(parents=True)
            overlay_path.write_text(
                "\n".join(
                    [
                        "DOMAIN-SUFFIX,example.com",
                        "DOMAIN-SUFFIX,api.example.com",
                        "DOMAIN,www.example.com",
                        "DOMAIN-KEYWORD,example",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )

            distillate.build_distillate(repo_root, manifest_path, skip_compiled=True)

            self.assertEqual(
                (repo_root / "rules" / "sample.list").read_text(encoding="utf-8").splitlines(),
                [
                    "# Generated from distillate/manifest.json",
                    "DOMAIN-SUFFIX,example.com",
                    "DOMAIN-KEYWORD,example",
                ],
            )

    def test_frozen_anti_advertising_full_list_keeps_legacy_file_and_updates_chunks(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            repo_root = Path(tmp_dir)
            manifest_path = repo_root / "distillate" / "manifest.json"
            manifest_path.parent.mkdir(parents=True)
            manifest_path.write_text(
                json.dumps(
                    {
                        "categories": [
                            {
                                "name": "anti_advertising",
                                "publish": True,
                                "compiled": False,
                                "legacy_rule_path": "rules/anti_advertising.list",
                                "legacy_rule_mode": "frozen",
                                "overlays": {"add": "distillate/overlays/anti_advertising.add.list"},
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )
            overlay_path = repo_root / "distillate" / "overlays" / "anti_advertising.add.list"
            overlay_path.parent.mkdir(parents=True)
            overlay_path.write_text(
                "\n".join(
                    [
                        "DOMAIN-SUFFIX,ads-one.example",
                        "DOMAIN-SUFFIX,ads-two.example",
                        "DOMAIN-SUFFIX,ads-three.example",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )
            full_path = repo_root / "rules" / "anti_advertising.list"
            full_path.parent.mkdir(parents=True)
            full_path.write_text("legacy full list\n", encoding="utf-8")

            with patch.object(distillate, "ANTI_ADVERTISING_MAX_CHUNK_BYTES", 60):
                distillate.build_distillate(repo_root, manifest_path, skip_compiled=True)

            self.assertEqual(full_path.read_text(encoding="utf-8"), "legacy full list\n")
            chunk_paths = sorted((repo_root / "rules").glob("anti_advertising.[0-9][0-9].list"))
            self.assertGreaterEqual(len(chunk_paths), 2)
            chunk_payload = "\n".join(path.read_text(encoding="utf-8") for path in chunk_paths)
            self.assertIn("DOMAIN-SUFFIX,ads-one.example", chunk_payload)
            self.assertIn("DOMAIN-SUFFIX,ads-three.example", chunk_payload)

    def test_chunked_legacy_rules_can_keep_generated_full_file_and_write_tier_chunks(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            repo_root = Path(tmp_dir)
            manifest_path = repo_root / "distillate" / "manifest.json"
            manifest_path.parent.mkdir(parents=True)
            manifest_path.write_text(
                json.dumps(
                    {
                        "categories": [
                            {
                                "name": "anti_advertising_pro",
                                "publish": True,
                                "compiled": False,
                                "legacy_rule_path": "rules/anti_advertising_pro.list",
                                "legacy_rule_chunks": True,
                                "overlays": {"add": "distillate/overlays/anti_advertising_pro.add.list"},
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )
            overlay_path = repo_root / "distillate" / "overlays" / "anti_advertising_pro.add.list"
            overlay_path.parent.mkdir(parents=True)
            overlay_path.write_text(
                "\n".join(f"DOMAIN-SUFFIX,ads-{index}.example" for index in range(1, 6)) + "\n",
                encoding="utf-8",
            )

            with patch.object(distillate, "ANTI_ADVERTISING_MAX_CHUNK_BYTES", 70):
                distillate.build_distillate(repo_root, manifest_path, skip_compiled=True)

            full_path = repo_root / "rules" / "anti_advertising_pro.list"
            self.assertIn("DOMAIN-SUFFIX,ads-1.example", full_path.read_text(encoding="utf-8"))
            chunk_paths = sorted((repo_root / "rules").glob("anti_advertising_pro.[0-9][0-9].list"))
            self.assertGreaterEqual(len(chunk_paths), 2)
            chunk_payload = "\n".join(path.read_text(encoding="utf-8") for path in chunk_paths)
            self.assertIn("DOMAIN-SUFFIX,ads-5.example", chunk_payload)

    def test_instagram_meta_can_keep_bm7_instagram_and_filter_facebook_to_ip_only(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            repo_root = Path(tmp_dir)
            manifest_path = repo_root / "distillate" / "manifest.json"
            manifest_path.parent.mkdir(parents=True)
            manifest_path.write_text(
                json.dumps(
                    {
                        "bm7_base_url": "https://example.test/bm7",
                        "upstream_dir": "distillate/upstream",
                        "categories": [
                            {
                                "name": "instagram_meta",
                                "publish": True,
                                "compiled": False,
                                "retain_ip_asn": True,
                                "legacy_rule_path": "rules/instagram_meta.list",
                                "sources": [
                                    {"type": "bm7", "pack": "Instagram"},
                                    {
                                        "type": "bm7",
                                        "pack": "Facebook",
                                        "include_rule_types": ["IP-CIDR", "IP-CIDR6", "IP-ASN"],
                                    },
                                ],
                                "overlays": {"add": "distillate/overlays/instagram_meta.add.list"},
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )
            upstream_dir = repo_root / "distillate" / "upstream" / "bm7"
            upstream_dir.mkdir(parents=True)
            (upstream_dir / "Instagram.list").write_text(
                "DOMAIN-SUFFIX,instagram.com\nDOMAIN-KEYWORD,instagram\n",
                encoding="utf-8",
            )
            (upstream_dir / "Facebook.list").write_text(
                "\n".join(
                    [
                        "DOMAIN-SUFFIX,facebook.com",
                        "IP-CIDR,31.13.24.0/21,no-resolve",
                        "IP-CIDR6,2a03:2880::/32,no-resolve",
                        "IP-ASN,32934,no-resolve",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )
            overlay_path = repo_root / "distillate" / "overlays" / "instagram_meta.add.list"
            overlay_path.parent.mkdir(parents=True)
            overlay_path.write_text("DOMAIN-SUFFIX,fbcdn.net\nDOMAIN,graph.instagram.com\n", encoding="utf-8")

            distillate.build_distillate(repo_root, manifest_path, skip_compiled=True)

            generated = (repo_root / "rules" / "instagram_meta.list").read_text(encoding="utf-8")
            self.assertIn("DOMAIN-KEYWORD,instagram", generated)
            self.assertIn("DOMAIN-SUFFIX,fbcdn.net", generated)
            self.assertIn("IP-CIDR,31.13.24.0/21", generated)
            self.assertIn("IP-CIDR6,2a03:2880::/32", generated)
            self.assertIn("IP-ASN,32934", generated)
            self.assertNotIn("DOMAIN-SUFFIX,facebook.com", generated)

    def test_restores_existing_dat_artifacts_when_compiled_build_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            repo_root = Path(tmp_dir)
            manifest_path, dat_dir = self.write_minimal_repo(repo_root)

            with patch.object(
                distillate,
                "compile_geosite_dat",
                side_effect=distillate.DistillateError("compiler upstream unavailable"),
            ):
                with self.assertRaises(distillate.DistillateError):
                    distillate.build_distillate(repo_root, manifest_path, skip_compiled=False)

            self.assertEqual((dat_dir / "geosite.dat").read_bytes(), b"old geosite")
            self.assertEqual((dat_dir / "geoip.dat").read_bytes(), b"old geoip")

    def test_allow_stale_compiled_continues_after_restoring_existing_dat(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            repo_root = Path(tmp_dir)
            manifest_path, dat_dir = self.write_minimal_repo(repo_root)

            with patch.object(
                distillate,
                "compile_geosite_dat",
                side_effect=distillate.DistillateError("compiler upstream unavailable"),
            ):
                result = distillate.build_distillate(
                    repo_root,
                    manifest_path,
                    skip_compiled=False,
                    allow_stale_compiled=True,
                )

            self.assertEqual(result, 0)
            self.assertEqual((dat_dir / "geosite.dat").read_bytes(), b"old geosite")
            self.assertEqual((dat_dir / "geoip.dat").read_bytes(), b"old geoip")

    def write_minimal_repo(self, repo_root: Path) -> tuple[Path, Path]:
        manifest_path = repo_root / "distillate" / "manifest.json"
        manifest_path.parent.mkdir(parents=True)
        manifest_path.write_text(
            json.dumps({"categories": [{"name": "empty", "publish": True}]}),
            encoding="utf-8",
        )

        dat_dir = repo_root / "distillate" / "dat"
        dat_dir.mkdir(parents=True)
        (dat_dir / "geosite.dat").write_bytes(b"old geosite")
        (dat_dir / "geoip.dat").write_bytes(b"old geoip")
        return manifest_path, dat_dir


if __name__ == "__main__":
    unittest.main()
