from __future__ import annotations

import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
CUSTOM_CONF = REPO_ROOT / "shadowrocket_custom.conf"
WHITELIST_CONF = REPO_ROOT / "shadowrocket_whitelist.conf"
TAILSCALE_MODULE = REPO_ROOT / "modules" / "tailscale_direct.module"
EXPECTED_SUBSCRIPTION_FILTER = r"(?i)^(?!.*Russia)(?!.*\bSS\b).*$"


def section_lines(content: str, section: str) -> list[str]:
    lines: list[str] = []
    in_section = False
    for raw_line in content.splitlines():
        line = raw_line.strip()
        if line == f"[{section}]":
            in_section = True
            continue
        if in_section and line.startswith("[") and line.endswith("]"):
            break
        if in_section and line and not line.startswith("#"):
            lines.append(line)
    return lines


def key_values(lines: list[str]) -> dict[str, str]:
    values: dict[str, str] = {}
    for line in lines:
        if " = " in line:
            key, value = line.split(" = ", 1)
            values[key] = value
    return values


class ShadowrocketWhitelistConfigTests(unittest.TestCase):
    def test_dns_settings_match_custom_profile(self) -> None:
        custom_general = key_values(section_lines(CUSTOM_CONF.read_text(encoding="utf-8"), "General"))
        whitelist_general = key_values(section_lines(WHITELIST_CONF.read_text(encoding="utf-8"), "General"))

        for key in (
            "dns-server",
            "fallback-dns-server",
            "dns-direct-system",
            "always-real-ip",
            "dns-direct-fallback-proxy",
            "hijack-dns",
        ):
            self.assertEqual(custom_general[key], whitelist_general[key])

    def test_profile_has_only_one_proxy_group(self) -> None:
        content = WHITELIST_CONF.read_text(encoding="utf-8")
        groups = section_lines(content, "Proxy Group")

        self.assertEqual(1, len(groups))
        self.assertTrue(groups[0].startswith("PROXY = select,"))
        self.assertNotIn("DIRECT", groups[0])

    def test_proxy_group_excludes_russia_and_standalone_ss_without_personal_default(self) -> None:
        content = WHITELIST_CONF.read_text(encoding="utf-8")
        groups = section_lines(content, "Proxy Group")

        self.assertEqual(
            groups,
            [f"PROXY = select,policy-regex-filter={EXPECTED_SUBSCRIPTION_FILTER}"],
        )
        self.assertNotIn("policy-select-name=", content)

    def test_service_specific_proxy_lists_are_not_used(self) -> None:
        content = WHITELIST_CONF.read_text(encoding="utf-8")

        self.assertNotIn("GOOGLE =", content)
        self.assertNotIn("OPENAI =", content)
        self.assertNotIn("AUTO-MAIN =", content)
        self.assertNotIn("AUTO-WL =", content)
        self.assertNotIn("greylist_proxy.list", content)
        self.assertNotIn("google-all.list", content)
        self.assertNotIn("openai.list", content)
        self.assertNotIn("microsoft.list", content)
        self.assertNotIn("domains_community.list", content)

    def test_direct_rules_precede_final_proxy(self) -> None:
        rules = section_lines(WHITELIST_CONF.read_text(encoding="utf-8"), "Rule")

        self.assertIn(
            "RULE-SET,https://raw.githubusercontent.com/Simonerrror/ShadowRocket/main/rules/whitelist_direct.list,DIRECT",
            rules,
        )
        self.assertEqual("FINAL,PROXY", rules[-1])
        self.assertLess(rules.index("GEOIP,RU,DIRECT"), rules.index("FINAL,PROXY"))

    def test_tailscale_is_not_transparent_in_whitelist_profile(self) -> None:
        content = WHITELIST_CONF.read_text(encoding="utf-8")

        self.assertNotIn("100.64.0.0/10", content)
        self.assertNotIn("100.100.100.100", content)
        self.assertNotIn("ts.net", content)
        self.assertNotIn("tailscale.com", content)

    def test_tailscale_overlay_is_a_separate_module(self) -> None:
        custom_content = CUSTOM_CONF.read_text(encoding="utf-8")
        module_content = TAILSCALE_MODULE.read_text(encoding="utf-8")
        custom_rules = section_lines(custom_content, "Rule")
        module_general = key_values(section_lines(module_content, "General"))
        module_rules = section_lines(module_content, "Rule")
        tailscale_rules = [
            "IP-CIDR,100.64.0.0/10,DIRECT,no-resolve",
            "IP-CIDR,100.100.100.100/32,DIRECT,no-resolve",
            "DOMAIN-SUFFIX,ts.net,DIRECT",
            "DOMAIN-SUFFIX,tailscale.com,DIRECT",
        ]

        self.assertEqual("100.100.100.100, *.ts.net, *.tailscale.com", module_general["skip-proxy"])
        self.assertNotIn("100.100.100.100", custom_content)
        self.assertNotIn("ts.net", custom_content)
        self.assertNotIn("tailscale.com", custom_content)
        for rule in tailscale_rules:
            with self.subTest(rule=rule):
                self.assertNotIn(rule, custom_rules)
                self.assertIn(rule, module_rules)


if __name__ == "__main__":
    unittest.main()
