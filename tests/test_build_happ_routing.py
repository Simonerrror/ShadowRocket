from __future__ import annotations

import base64
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from scripts.build_happ_routing import (
    RU_PROFILE_NAME,
    BuildData,
    Bucket,
    build_profile,
    existing_build_stamp,
    profile_to_deeplink,
    resolve_build_stamp,
)


class HappBuildStampTests(unittest.TestCase):
    def test_build_stamp_precedence_and_invalid_fallback(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            out_dir = root / "HAPP"
            out_dir.mkdir()
            (out_dir / "DEFAULT.JSON").write_text(
                json.dumps({"LastUpdated": "1234567890"}),
                encoding="utf-8",
            )

            self.assertEqual(resolve_build_stamp(root, "", out_dir), "1234567890")
            self.assertEqual(resolve_build_stamp(root, "9876543210", out_dir), "9876543210")
            (out_dir / "DEFAULT.JSON").write_text("not json", encoding="utf-8")
            self.assertIsNone(existing_build_stamp(out_dir))


class HappInputValidationTests(unittest.TestCase):
    def test_missing_aggregate_preserves_existing_outputs(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "shadowrocket.conf").write_text("[General]\n", encoding="utf-8")
            dat_dir = root / "distillate" / "dat"
            dat_dir.mkdir(parents=True)
            (dat_dir / "geoip.dat").write_bytes(b"geoip")
            (dat_dir / "geosite.dat").write_bytes(b"geosite")
            for kind in ("domain", "ip"):
                directory = root / "distillate" / "text" / kind
                directory.mkdir(parents=True)
                for bucket in ("direct", "proxy", "block"):
                    path = directory / f"sr-{bucket}.txt"
                    if path != root / "distillate" / "text" / "domain" / "sr-direct.txt":
                        path.write_text("", encoding="utf-8")
            (root / "distillate" / "text" / "domain" / "motivato_block.txt").write_text(
                "domain:block.example\n",
                encoding="utf-8",
            )
            out_dir = root / "HAPP"
            out_dir.mkdir()
            output = out_dir / "DEFAULT.JSON"
            obsolete = out_dir / "REPORT.md"
            output.write_text("old profile\n", encoding="utf-8")
            obsolete.write_text("old report\n", encoding="utf-8")

            result = subprocess.run(
                [
                    sys.executable,
                    str(Path(__file__).parents[1] / "scripts" / "build_happ_routing.py"),
                ],
                cwd=root,
                capture_output=True,
                text=True,
            )

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("sr-direct.txt", result.stderr + result.stdout)
            self.assertEqual(output.read_text(encoding="utf-8"), "old profile\n")
            self.assertEqual(obsolete.read_text(encoding="utf-8"), "old report\n")


class HappRuVpnProfileTests(unittest.TestCase):
    def test_ru_vpn_proxies_only_ru_tags_and_defaults_to_direct(self) -> None:
        data = BuildData(
            direct=Bucket(site_rules=["domain:ru"], cidrs=["192.0.2.0/24"]),
            proxy=Bucket(site_rules=["domain:openai.com"], cidrs=["198.51.100.0/24"]),
            block=Bucket(site_rules=["domain:ads.example"], cidrs=["203.0.113.0/24"]),
        )

        profile = build_profile(
            data=data,
            geodata_base="https://example.test/dat",
            last_updated="123",
            route_order="block-proxy-direct",
            remote_dns_ip="8.8.8.8",
            remote_dns_domain="https://8.8.8.8/dns-query",
            domestic_dns_ip="77.88.8.8",
            remote_dns_type="DoH",
            domestic_dns_type="DoH",
            general_direct_ips=["127.0.0.1"],
            profile_name=RU_PROFILE_NAME,
            block_geosite_tag="motivato-block",
            global_proxy="false",
            direct_geosite_tag=None,
            direct_geoip_tag=None,
            proxy_geosite_tag="category-ru",
            proxy_geoip_tag="ru",
        )

        self.assertEqual(profile["Name"], "RU-VPN")
        self.assertEqual(profile["GlobalProxy"], "false")
        self.assertEqual(profile["DirectSites"], [])
        self.assertEqual(profile["DirectIp"], ["127.0.0.1"])
        self.assertEqual(profile["ProxySites"], ["geosite:category-ru"])
        self.assertEqual(profile["ProxyIp"], ["geoip:ru"])
        self.assertNotIn("geosite:sr-proxy", profile["ProxySites"])
        self.assertNotIn("geoip:sr-proxy", profile["ProxyIp"])
        self.assertEqual(profile["BlockSites"], ["geosite:motivato-block"])
        self.assertEqual(profile["BlockIp"], ["geoip:sr-block"])

    def test_deeplink_decodes_to_exact_ru_vpn_json(self) -> None:
        profile = {"Name": "RU-VPN", "GlobalProxy": "false"}

        pretty, compact, deeplink = profile_to_deeplink(profile, "onadd")
        decoded = base64.b64decode(deeplink.rsplit("/", 1)[1]).decode("utf-8")

        self.assertEqual(json.loads(pretty), profile)
        self.assertEqual(decoded, compact)
        self.assertEqual(json.loads(decoded), profile)


if __name__ == "__main__":
    unittest.main()
