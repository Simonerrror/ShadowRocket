from __future__ import annotations

import base64
import json
import tempfile
import unittest
from pathlib import Path

from scripts.build_happ_routing import (
    DEFAULT_REMOTE_DNS_DOMAIN,
    DEFAULT_REMOTE_DNS_IP,
    DEFAULT_RU_REMOTE_DNS_DOMAIN,
    DEFAULT_RU_REMOTE_DNS_IP,
    RU_PROFILE_NAME,
    BuildData,
    Bucket,
    build_profile,
    existing_build_stamp,
    profile_to_deeplink,
    resolve_build_stamp,
)


class HappDnsDefaultsTests(unittest.TestCase):
    def test_remote_dns_defaults_to_adguard_non_filtering(self) -> None:
        self.assertEqual(DEFAULT_REMOTE_DNS_IP, "94.140.14.140")
        self.assertEqual(
            DEFAULT_REMOTE_DNS_DOMAIN,
            "https://unfiltered.adguard-dns.com/dns-query",
        )
        self.assertEqual(DEFAULT_RU_REMOTE_DNS_IP, "8.8.8.8")
        self.assertEqual(DEFAULT_RU_REMOTE_DNS_DOMAIN, "https://8.8.8.8/dns-query")


class HappBuildStampTests(unittest.TestCase):
    def test_preserves_existing_stamp_when_explicit_value_is_absent(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            out_dir = root / "HAPP"
            out_dir.mkdir()
            (out_dir / "DEFAULT.JSON").write_text(
                json.dumps({"LastUpdated": "1234567890"}),
                encoding="utf-8",
            )

            self.assertEqual(resolve_build_stamp(root, "", out_dir), "1234567890")

    def test_explicit_stamp_overrides_existing_value(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            out_dir = root / "HAPP"
            out_dir.mkdir()
            (out_dir / "DEFAULT.JSON").write_text(
                json.dumps({"LastUpdated": "1234567890"}),
                encoding="utf-8",
            )

            self.assertEqual(resolve_build_stamp(root, "9876543210", out_dir), "9876543210")

    def test_invalid_existing_json_has_no_preserved_stamp(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            out_dir = Path(tmpdir)
            (out_dir / "DEFAULT.JSON").write_text("not json", encoding="utf-8")

            self.assertIsNone(existing_build_stamp(out_dir))


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
