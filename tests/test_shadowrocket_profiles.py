from __future__ import annotations

import re
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
BASE_CONF = REPO_ROOT / "shadowrocket.conf"
CUSTOM_CONF = REPO_ROOT / "shadowrocket_custom.conf"
PRIVATE_DNS_CONF = REPO_ROOT / "shadowrocket_custom_private_dns.conf"
WHITELIST_CONF = REPO_ROOT / "shadowrocket_whitelist.conf"
TAILSCALE_MODULE = REPO_ROOT / "modules" / "tailscale_direct.module"
WECHAT_MODULE = REPO_ROOT / "modules" / "wechat_direct.module"
README = REPO_ROOT / "README.md"
EXPECTED_MANUAL_FILTER = r"(?i)^(?!.*\bWL\b).*$"
EXPECTED_AUTO_FILTER = r"(?i)^(?!.*(?:Russia|Belarus|Ukraine))(?!.*\bWL\b).*\bVLESS\b.*$"
EXPECTED_GOOGLE_FILTER = r"(?i)^(?!.*(?:Russia|Belarus|Ukraine))(?!.*\bSS\b)(?!.*\bTrojan\b)(?!.*\bWL\b).*$"
EXPECTED_WL_FILTER = r"(?i)\bWL\b"
EXPECTED_PROVENANCE = [
    "# Config-Version: 2026.08.21.1",
    "# Maintainer: Simonerrror; contact: https://t.me/AIDHDaily",
    "# README: https://github.com/Simonerrror/ShadowRocket#readme",
]


def section_lines(path: Path, section: str, *, keep_comments: bool = False) -> list[str]:
    lines: list[str] = []
    in_section = False
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if line == f"[{section}]":
            in_section = True
            continue
        if in_section and line.startswith("[") and line.endswith("]"):
            break
        if in_section and line and (keep_comments or not line.startswith("#")):
            lines.append(line)
    return lines


def key_values(path: Path, section: str) -> dict[str, str]:
    values: dict[str, str] = {}
    for line in section_lines(path, section):
        if " = " in line:
            key, value = line.split(" = ", 1)
            values[key] = value
    return values


class ShadowrocketProfilesTests(unittest.TestCase):
    def test_published_profiles_show_version_maintainer_and_readme(self) -> None:
        for path in (BASE_CONF, CUSTOM_CONF, PRIVATE_DNS_CONF, WHITELIST_CONF):
            lines = path.read_text(encoding="utf-8").splitlines()
            general_index = lines.index("[General]")
            with self.subTest(path=path.name):
                self.assertEqual(EXPECTED_PROVENANCE, lines[general_index + 1 : general_index + 4])

    def test_custom_proxy_groups_match_each_other(self) -> None:
        self.assertEqual(section_lines(CUSTOM_CONF, "Proxy Group"), section_lines(PRIVATE_DNS_CONF, "Proxy Group"))

    def test_proxy_groups_apply_each_subscription_scope(self) -> None:
        profiles = (BASE_CONF, CUSTOM_CONF, PRIVATE_DNS_CONF)

        for path in profiles:
            groups = key_values(path, "Proxy Group")
            for key, expected_filter in (
                ("MANUAL-PROXY", EXPECTED_MANUAL_FILTER),
                ("AUTO-SPEED", EXPECTED_AUTO_FILTER),
                ("AUTO-STABILITY", EXPECTED_AUTO_FILTER),
                ("GOOGLE", EXPECTED_GOOGLE_FILTER),
                ("WL", EXPECTED_WL_FILTER),
            ):
                with self.subTest(path=path.name, key=key):
                    actual_filter = groups[key].partition("policy-regex-filter=")[2].split(",", 1)[0]
                    self.assertEqual(expected_filter, actual_filter)

            self.assertTrue(groups["GOOGLE"].startswith("url-test,"))
            self.assertIn(",interval=180,tolerance=100,url=https://abs.twimg.com/favicon.ico,timeout=7", groups["GOOGLE"])
            self.assertTrue(groups["WL"].startswith("select,"))
            self.assertEqual(
                ["select", "MANUAL-PROXY", "AUTO-SPEED", "AUTO-STABILITY", "WL", "policy-select-name=AUTO-STABILITY"],
                groups["PROXY"].split(","),
            )

    def test_manual_filter_accepts_everything_except_standalone_wl(self) -> None:
        subscription_filter = re.compile(EXPECTED_MANUAL_FILTER)

        for name in (
            "🇺🇸 United States Vless",
            "🇷🇺 Russia Vless",
            "🇧🇾 Belarus SS",
            "🇺🇦 Ukraine Trojan",
            "🇫🇷 France Hysteria",
            "Japan VMess",
        ):
            with self.subTest(name=name):
                self.assertTrue(subscription_filter.fullmatch(name))

        for name in (
            "WL-lte VLESS",
            "VLESS WL",
        ):
            with self.subTest(name=name):
                self.assertFalse(subscription_filter.fullmatch(name))

    def test_wl_filter_accepts_any_protocol_with_standalone_wl_token(self) -> None:
        wl_filter = re.compile(EXPECTED_WL_FILTER)

        for name in ("WL Vless", "WL-lte VLESS", "VLESS WL", "WL Trojan", "WL SS", "WL Hysteria2"):
            with self.subTest(name=name):
                self.assertIsNotNone(wl_filter.search(name))

        for name in (
            "VLESS Germany",
            "WLAN VLESS",
            "BOWL relay Trojan",
            "Germany SS",
        ):
            with self.subTest(name=name):
                self.assertIsNone(wl_filter.search(name))

    def test_google_filter_excludes_cis_legacy_protocols_and_wl(self) -> None:
        google_filter = re.compile(EXPECTED_GOOGLE_FILTER)

        for name in ("France VLESS", "Germany Hysteria2", "Japan VMess", "USA SS2022"):
            with self.subTest(name=name):
                self.assertTrue(google_filter.fullmatch(name))

        for name in (
            "Russia VLESS",
            "Belarus Hysteria2",
            "Ukraine VMess",
            "Germany SS",
            "USA Trojan",
            "France WL Mobile VLESS",
        ):
            with self.subTest(name=name):
                self.assertFalse(google_filter.fullmatch(name))

    def test_auto_filter_keeps_only_vless_outside_ru_by_ua(self) -> None:
        auto_filter = re.compile(EXPECTED_AUTO_FILTER)

        for name in (
            "🇺🇸 United States Vless",
            "BOWL relay VLESS",
            "WLAN Germany VLESS",
        ):
            with self.subTest(name=name):
                self.assertTrue(auto_filter.fullmatch(name))

        for name in (
            "🇷🇺 Russia Vless",
            "🇧🇾 Belarus(M) Vless",
            "🇺🇦 Ukraine VLESS",
            "🇫🇷 France WL Mobile Vless",
            "Germany SS",
            "USA Trojan",
            "TROJAN Hysteria2",
            "Germany VLESS2",
        ):
            with self.subTest(name=name):
                self.assertFalse(auto_filter.fullmatch(name))

    def test_base_and_custom_use_same_dns(self) -> None:
        base_general = key_values(BASE_CONF, "General")
        custom_general = key_values(CUSTOM_CONF, "General")

        self.assertEqual("9.9.9.9, 149.112.112.112, 77.88.8.8", base_general["dns-server"])
        self.assertEqual(base_general["dns-server"], custom_general["dns-server"])
        self.assertEqual(base_general["fallback-dns-server"], custom_general["fallback-dns-server"])

    def test_private_dns_profile_keeps_doh_dot(self) -> None:
        general = key_values(PRIVATE_DNS_CONF, "General")

        self.assertEqual(
            "https://dns.mullvad.net/dns-query, https://dns.quad9.net/dns-query",
            general["dns-server"],
        )
        self.assertEqual("tls://dns.mullvad.net, tls://dns.quad9.net", general["fallback-dns-server"])

    def test_base_keeps_custom_only_gfn_exceptions_out(self) -> None:
        base_general = key_values(BASE_CONF, "General")
        base_content = BASE_CONF.read_text(encoding="utf-8")

        self.assertNotIn("always-real-ip", base_general)
        self.assertNotIn("geforcenow", base_content)
        self.assertNotIn("nvidiagrid", base_content)

    def test_shared_local_bypass_ranges_match(self) -> None:
        base_general = key_values(BASE_CONF, "General")
        custom_general = key_values(CUSTOM_CONF, "General")
        private_dns_general = key_values(PRIVATE_DNS_CONF, "General")

        self.assertEqual(base_general["skip-proxy"], custom_general["skip-proxy"])
        self.assertEqual(base_general["skip-proxy"], private_dns_general["skip-proxy"])
        self.assertEqual(base_general["bypass-tun"], custom_general["bypass-tun"])
        self.assertEqual(base_general["bypass-tun"], private_dns_general["bypass-tun"])

    def test_tailscale_specific_rules_stay_in_module(self) -> None:
        profile_contents = "\n".join(
            path.read_text(encoding="utf-8") for path in (BASE_CONF, CUSTOM_CONF, PRIVATE_DNS_CONF)
        )
        module_content = TAILSCALE_MODULE.read_text(encoding="utf-8")

        self.assertNotIn("100.64.0.0/10", profile_contents)
        self.assertNotIn("100.100.100.100", profile_contents)
        self.assertNotIn("ts.net", profile_contents)
        self.assertNotIn("tailscale.com", profile_contents)
        self.assertIn("100.100.100.100", module_content)
        self.assertIn("DOMAIN-SUFFIX,ts.net,DIRECT", module_content)
        self.assertIn("DOMAIN-SUFFIX,tailscale.com,DIRECT", module_content)

    def test_wechat_direct_module_has_approved_rules(self) -> None:
        content = WECHAT_MODULE.read_text(encoding="utf-8")
        rules = section_lines(WECHAT_MODULE, "Rule")
        expected_rules = [
            "DOMAIN-SUFFIX,wechat.com,DIRECT",
            "DOMAIN-SUFFIX,wechatapp.com,DIRECT",
            "DOMAIN-SUFFIX,wechatlegal.net,DIRECT",
            "DOMAIN-SUFFIX,wechatpay.com,DIRECT",
            "DOMAIN-SUFFIX,weixin.com,DIRECT",
            "DOMAIN-SUFFIX,weixin.qq.com,DIRECT",
            "DOMAIN-SUFFIX,weixinbridge.com,DIRECT",
            "DOMAIN-SUFFIX,servicewechat.com,DIRECT",
            "DOMAIN-SUFFIX,qpic.cn,DIRECT",
            "DOMAIN-SUFFIX,qlogo.cn,DIRECT",
            "DOMAIN-SUFFIX,wx.gtimg.com,DIRECT",
            "DOMAIN,miniapp.gtimg.cn,DIRECT",
            "DOMAIN,res.wx.qq.com,DIRECT",
        ]

        self.assertIn("#!name=WeChat Direct", content)
        self.assertIn("[Rule]", content)
        self.assertEqual(expected_rules, rules)

    def test_wechat_direct_module_excludes_broad_tencent_and_ip_rules(self) -> None:
        rules = section_lines(WECHAT_MODULE, "Rule")

        self.assertNotIn("DOMAIN-SUFFIX,qq.com,DIRECT", rules)
        self.assertNotIn("DOMAIN-SUFFIX,gtimg.com,DIRECT", rules)
        self.assertNotIn("DOMAIN-SUFFIX,gtimg.cn,DIRECT", rules)
        self.assertNotIn("DOMAIN-SUFFIX,tencent.com,DIRECT", rules)
        self.assertFalse(any(rule.startswith(("IP-CIDR,", "IP-CIDR6,")) for rule in rules))

    def test_readme_documents_wechat_direct_module(self) -> None:
        content = README.read_text(encoding="utf-8")

        self.assertIn("modules/wechat_direct.module", content)
        self.assertIn(
            "https://raw.githubusercontent.com/Simonerrror/ShadowRocket/main/modules/wechat_direct.module",
            content,
        )
        self.assertIn("выше anti-advertising", content)

    def test_rule_comments_have_visual_spacing(self) -> None:
        for path in (BASE_CONF, CUSTOM_CONF, PRIVATE_DNS_CONF):
            lines = path.read_text(encoding="utf-8").splitlines()
            rule_start = lines.index("[Rule]")
            for index in range(rule_start + 2, len(lines)):
                if lines[index].startswith("#"):
                    with self.subTest(path=path.name, comment=lines[index]):
                        self.assertEqual("", lines[index - 1])


if __name__ == "__main__":
    unittest.main()
