from __future__ import annotations

import re
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
WHITELIST_CONF = REPO_ROOT / "shadowrocket_whitelist.conf"
EXPECTED_SUBSCRIPTION_FILTER = r"(?i)^(?!.*Russia)(?!.*\bSS\b)(?!.*\bTrojan\b).*$"


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


class ShadowrocketWhitelistConfigTests(unittest.TestCase):
    def test_single_proxy_group_accepts_only_non_excluded_nodes(self) -> None:
        content = WHITELIST_CONF.read_text(encoding="utf-8")
        groups = section_lines(content, "Proxy Group")

        self.assertEqual(1, len(groups))
        self.assertEqual(
            groups,
            [f"PROXY = select,policy-regex-filter={EXPECTED_SUBSCRIPTION_FILTER}"],
        )
        self.assertNotIn("DIRECT", groups[0])
        self.assertNotIn("policy-select-name=", content)

        subscription_filter = re.compile(EXPECTED_SUBSCRIPTION_FILTER)
        for name in (
            "🇺🇸 United States Vless",
            "🇫🇷 France Hysteria2",
            "Japan VMess",
            "BASS relay",
            "WL VLESS",
            "WL-lte VLESS",
            "USA VLESS SS2022",
        ):
            with self.subTest(name=name):
                self.assertTrue(subscription_filter.fullmatch(name))

        for name in (
            "🇷🇺 Russia Vless",
            "USA Trojan",
            "Germany SS",
        ):
            with self.subTest(name=name):
                self.assertFalse(subscription_filter.fullmatch(name))

    def test_direct_allowlist_precedes_final_proxy_without_service_routes(self) -> None:
        content = WHITELIST_CONF.read_text(encoding="utf-8")
        rules = section_lines(content, "Rule")

        self.assertIn(
            "RULE-SET,https://raw.githubusercontent.com/Simonerrror/ShadowRocket/main/rules/whitelist_direct.list,DIRECT",
            rules,
        )
        self.assertEqual("FINAL,PROXY", rules[-1])
        self.assertLess(rules.index("GEOIP,RU,DIRECT"), rules.index("FINAL,PROXY"))
        for forbidden in (
            "GOOGLE =",
            "OPENAI =",
            "AUTO-MAIN =",
            "AUTO-WL =",
            "greylist_proxy.list",
            "google-all.list",
            "openai.list",
            "microsoft.list",
            "domains_community.list",
        ):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, content)


if __name__ == "__main__":
    unittest.main()
