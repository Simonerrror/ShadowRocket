from __future__ import annotations

import re
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
BASE_CONF = REPO_ROOT / "shadowrocket.conf"
CUSTOM_CONF = REPO_ROOT / "shadowrocket_custom.conf"
WHITELIST_CONF = REPO_ROOT / "shadowrocket_whitelist.conf"
TORRENT_DOMAINS = REPO_ROOT / "distillate" / "text" / "domain" / "motivato_torrent.txt"
SR_DIRECT_DOMAINS = REPO_ROOT / "distillate" / "text" / "domain" / "sr-direct.txt"
SR_BLOCK_DOMAINS = REPO_ROOT / "distillate" / "text" / "domain" / "sr-block.txt"
TAILSCALE_MODULE = REPO_ROOT / "modules" / "tailscale_tailnet.module"
WECHAT_MODULE = REPO_ROOT / "modules" / "wechat_direct.module"
GEMINI_OUTBOUND_MODULE = REPO_ROOT / "modules" / "gemini_personal_outbound.module"
EXPECTED_MANUAL_FILTER = r"(?i)^(?!.*\bWL\b)(?!.*\bSS\b).*$"
EXPECTED_AUTO_FILTER = r"(?i)^(?!.*(?:Russia|Belarus|Ukraine))(?!.*\bWL\b).*\b(?:VLESS|TT|Naive|NV|MR|AWG2)\b.*$"
EXPECTED_WL_FILTER = r"(?i)\bWL\b"
EXPECTED_PROVENANCE = [
    "# Config-Version: 2026.08.26.1",
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
    def test_torrent_domains_are_direct_in_every_profile(self) -> None:
        torrent_domains = set(TORRENT_DOMAINS.read_text(encoding="utf-8").splitlines())
        direct_domains = set(SR_DIRECT_DOMAINS.read_text(encoding="utf-8").splitlines())
        block_domains = set(SR_BLOCK_DOMAINS.read_text(encoding="utf-8").splitlines())

        self.assertTrue(torrent_domains)
        self.assertLessEqual(torrent_domains, direct_domains)
        self.assertTrue(torrent_domains.isdisjoint(block_domains))
        for path in (BASE_CONF, CUSTOM_CONF, WHITELIST_CONF):
            with self.subTest(path=path.name):
                self.assertIn(
                    "RULE-SET,https://raw.githubusercontent.com/Simonerrror/ShadowRocket/main/rules/whitelist_direct.list,DIRECT",
                    section_lines(path, "Rule"),
                )

    def test_published_profiles_show_version_maintainer_and_readme(self) -> None:
        for path in (BASE_CONF, CUSTOM_CONF, WHITELIST_CONF):
            lines = path.read_text(encoding="utf-8").splitlines()
            general_index = lines.index("[General]")
            with self.subTest(path=path.name):
                self.assertEqual(EXPECTED_PROVENANCE, lines[general_index + 1 : general_index + 4])

    def test_proxy_groups_apply_each_subscription_scope(self) -> None:
        profiles = (BASE_CONF, CUSTOM_CONF)

        for path in profiles:
            groups = key_values(path, "Proxy Group")
            for key, expected_filter in (
                ("MANUAL-PROXY", EXPECTED_MANUAL_FILTER),
                ("AUTO-SPEED", EXPECTED_AUTO_FILTER),
                ("AUTO-STABILITY", EXPECTED_AUTO_FILTER),
                ("WL", EXPECTED_WL_FILTER),
            ):
                with self.subTest(path=path.name, key=key):
                    actual_filter = groups[key].partition("policy-regex-filter=")[2].split(",", 1)[0]
                    self.assertEqual(expected_filter, actual_filter)

            self.assertNotIn("GOOGLE", groups)
            self.assertTrue(groups["WL"].startswith("select,"))
            self.assertEqual(
                ["select", "MANUAL-PROXY", "AUTO-SPEED", "AUTO-STABILITY", "WL", "policy-select-name=AUTO-STABILITY"],
                groups["PROXY"].split(","),
            )

    def test_subscription_filters_accept_and_reject_expected_nodes(self) -> None:
        cases = (
            (
                "manual",
                EXPECTED_MANUAL_FILTER,
                ("🇺🇸 United States Vless", "🇷🇺 Russia Vless", "Japan VMess", "MASS relay", "SSS relay"),
                ("WL-lte VLESS", "VLESS WL", "🇧🇾 Belarus SS", "Japan SS-lte"),
            ),
            (
                "wl",
                EXPECTED_WL_FILTER,
                ("WL Vless", "WL-lte VLESS", "VLESS WL", "WL Trojan", "WL SS"),
                ("VLESS Germany", "WLAN VLESS", "BOWL relay Trojan"),
            ),
            (
                "auto",
                EXPECTED_AUTO_FILTER,
                (
                    "🇺🇸 United States Vless",
                    "BOWL relay VLESS",
                    "WLAN Germany VLESS",
                    "🇭🇰 Hong Kong TT",
                    "🇩🇪 Germany Naive",
                    "🇵🇱 Польша AWG2",
                    "🇬🇷 Греция AWG2",
                    "🇩🇪 Germany NV",
                    "🇨🇦 Canada MR",
                ),
                (
                    "🇷🇺 Russia Vless",
                    "🇧🇾 Belarus(M) TT",
                    "🇺🇦 Ukraine Naive",
                    "🇫🇷 France WL Mobile Vless",
                    "Germany SS",
                    "USA Trojan",
                    "🇸🇪 Sweden Mieru",
                    "🇯🇵 Japan Mierus",
                    "🇯🇵 Japan NVx",
                    "🇰🇷 Korea MRoad",
                ),
            ),
        )
        for group, pattern, accepted, rejected in cases:
            compiled = re.compile(pattern)
            for name in accepted:
                with self.subTest(group=group, name=name, expected="accept"):
                    self.assertIsNotNone(compiled.search(name) if group == "wl" else compiled.fullmatch(name))
            for name in rejected:
                with self.subTest(group=group, name=name, expected="reject"):
                    self.assertIsNone(compiled.search(name) if group == "wl" else compiled.fullmatch(name))

    def test_profiles_keep_shared_dns_contracts(self) -> None:
        base_general = key_values(BASE_CONF, "General")
        custom_general = key_values(CUSTOM_CONF, "General")
        whitelist_general = key_values(WHITELIST_CONF, "General")

        self.assertEqual("9.9.9.9, 149.112.112.112, 77.88.8.8", base_general["dns-server"])
        self.assertEqual(base_general["dns-server"], custom_general["dns-server"])
        self.assertEqual(base_general["fallback-dns-server"], custom_general["fallback-dns-server"])
        for key in (
            "dns-server",
            "fallback-dns-server",
            "dns-direct-system",
            "always-real-ip",
            "dns-direct-fallback-proxy",
            "hijack-dns",
        ):
            with self.subTest(profile="whitelist", key=key):
                self.assertEqual(custom_general[key], whitelist_general[key])

    def test_base_keeps_custom_only_gfn_exceptions_out(self) -> None:
        base_general = key_values(BASE_CONF, "General")
        base_content = BASE_CONF.read_text(encoding="utf-8")

        self.assertNotIn("always-real-ip", base_general)
        self.assertNotIn("geforcenow", base_content)
        self.assertNotIn("nvidiagrid", base_content)

    def test_shared_local_bypass_ranges_match(self) -> None:
        base_general = key_values(BASE_CONF, "General")
        custom_general = key_values(CUSTOM_CONF, "General")
        self.assertEqual(base_general["skip-proxy"], custom_general["skip-proxy"])
        self.assertEqual(base_general["bypass-tun"], custom_general["bypass-tun"])

    def test_tailscale_specific_rules_stay_in_module(self) -> None:
        profile_contents = "\n".join(
            path.read_text(encoding="utf-8")
            for path in (BASE_CONF, CUSTOM_CONF, WHITELIST_CONF)
        )
        module_content = TAILSCALE_MODULE.read_text(encoding="utf-8")
        module_rules = section_lines(TAILSCALE_MODULE, "Rule")

        self.assertNotIn("100.64.0.0/10", profile_contents)
        self.assertNotIn("100.100.100.100", profile_contents)
        self.assertNotIn("ts.net", profile_contents)
        self.assertNotIn("tailscale.com", profile_contents)
        self.assertNotIn("DIRECT", module_content)
        self.assertNotIn("tun-excluded-routes", module_content)
        self.assertNotIn("bypass-tun", module_content)
        self.assertNotIn("skip-proxy", module_content)
        for rule in (
            "IP-CIDR,100.64.0.0/10,TAILSCALE,no-resolve",
            "IP-CIDR6,fd7a:115c:a1e0::/48,TAILSCALE,no-resolve",
            "DOMAIN-SUFFIX,ts.net,TAILSCALE",
        ):
            with self.subTest(rule=rule):
                self.assertIn(rule, module_rules)

    def test_gemini_personal_outbound_keeps_google_session_on_one_outbound(self) -> None:
        profile_contents = "\n".join(
            path.read_text(encoding="utf-8")
            for path in (BASE_CONF, CUSTOM_CONF)
        )
        template = GEMINI_OUTBOUND_MODULE.read_text(encoding="utf-8")
        module_general = key_values(GEMINI_OUTBOUND_MODULE, "General")
        rule = (
            "RULE-SET,https://raw.githubusercontent.com/Simonerrror/ShadowRocket/main/"
            "rules/google-all.list,{{{Ваш персональный outbound}}}"
        )

        self.assertNotIn("GOOGLE =", profile_contents)
        self.assertNotIn("rules/google-all.list", profile_contents)
        self.assertIn("#!arguments=Ваш персональный outbound:", template)
        self.assertNotIn("#!arguments=Ваш персональный outbound:WARP-GEMINI", template)
        self.assertEqual([rule], section_lines(GEMINI_OUTBOUND_MODULE, "Rule"))
        self.assertNotIn("force-remote-dns", template)
        self.assertEqual("REJECT", module_general["udp-policy-not-supported-behaviour"])

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

        self.assertNotIn("DOMAIN-SUFFIX,qq.com,DIRECT", rules)
        self.assertNotIn("DOMAIN-SUFFIX,gtimg.com,DIRECT", rules)
        self.assertNotIn("DOMAIN-SUFFIX,gtimg.cn,DIRECT", rules)
        self.assertNotIn("DOMAIN-SUFFIX,tencent.com,DIRECT", rules)
        self.assertFalse(any(rule.startswith(("IP-CIDR,", "IP-CIDR6,")) for rule in rules))

if __name__ == "__main__":
    unittest.main()
