from __future__ import annotations

import re
import unittest

from scripts.build_clash_config import (
    DEFAULT_CONF,
    DEFAULT_SUBSCRIPTION_URL,
    build_config,
    yaml_quote,
)


EXPECTED_MIHOMO_AUTO_EXCLUDE_FILTER = r"(?i)Russia|Belarus|Ukraine|\b(?:WL|SS)\b"


class BuildClashConfigTests(unittest.TestCase):
    def test_generated_service_routes_leave_google_and_openai_to_optional_overlays(self) -> None:
        content, warnings = build_config(DEFAULT_CONF, DEFAULT_SUBSCRIPTION_URL)

        self.assertNotIn("  openai:", content)
        self.assertNotIn("rules/openai.list", content)
        self.assertNotIn("RULE-SET,openai", content)
        self.assertNotIn("  - name: OPENAI", content)
        self.assertNotIn("OPENAI: unsupported", "\n".join(warnings))
        self.assertNotIn("  google_all:", content)
        self.assertNotIn("rules/google-all.list", content)
        self.assertNotIn("RULE-SET,google_all", content)
        self.assertNotIn("  - name: GOOGLE", content)

    def test_rule_providers_declare_text_format_for_shadowrocket_lists(self) -> None:
        content, _ = build_config(DEFAULT_CONF, DEFAULT_SUBSCRIPTION_URL)
        providers = content.split("rule-providers:\n", 1)[1].split("# 5. PROXY GROUPS", 1)[0]
        for provider in re.split(r"(?m)^  [A-Za-z0-9_]+:\n", providers)[1:]:
            self.assertIn("    format: text", provider)

    def test_torrent_block_precedes_all_other_generated_rules(self) -> None:
        content, _warnings = build_config(DEFAULT_CONF, DEFAULT_SUBSCRIPTION_URL)
        rules = content.split("\nrules:\n", 1)[1]
        first = next(line.strip() for line in rules.splitlines() if line.strip().startswith("- "))
        self.assertEqual("- RULE-SET,torrent_block,REJECT", first)
        self.assertIn("rules/torrent_block.list", content)

    def test_latest_template_uses_one_visible_automatic_pool(self) -> None:
        content, warnings = build_config(DEFAULT_CONF, DEFAULT_SUBSCRIPTION_URL)
        self.assertEqual(re.findall(r"^  - name: (.+)$", content, re.MULTILINE), ["Режим"])
        group = content.split("  - name: Режим\n", 1)[1].split("# 6. RULES", 1)[0]
        self.assertIn("    type: url-test", group)
        self.assertIn("    use:\n      - Main-Sub", group)
        self.assertIn('    url: "https://www.youtube.com/favicon.ico"', group)
        self.assertIn("    interval: 180", group)
        self.assertIn("    tolerance: 100", group)
        self.assertNotIn("    proxies:", group)
        self.assertNotIn("    filter:", group)
        self.assertNotIn("hidden: true", group)
        self.assertIn(f"    exclude-filter: {yaml_quote(EXPECTED_MIHOMO_AUTO_EXCLUDE_FILTER)}", group)
        self.assertIn("MATCH,Режим", content)
        self.assertNotIn("unsupported proxy-group option use=true", "\n".join(warnings))
        pattern = re.compile(EXPECTED_MIHOMO_AUTO_EXCLUDE_FILTER)
        for name in ("Germany", "Poland", "Japan Hysteria2", "USA Trojan", "MASS relay", "SSS relay"):
            with self.subTest(name=name, expected="accept"):
                self.assertIsNone(pattern.search(name))
        for name in ("Russia", "Belarus", "Ukraine", "Germany SS", "Japan SS-lte", "Germany Hysteria2 SS", "WL-lte"):
            with self.subTest(name=name, expected="reject"):
                self.assertIsNotNone(pattern.search(name))

    def test_latest_dns_uses_loopback_hosts_and_separate_node_resolvers(self) -> None:
        content, _ = build_config(DEFAULT_CONF, DEFAULT_SUBSCRIPTION_URL)
        self.assertIn("  listen: 127.0.0.1:1053", content)
        self.assertIn("  use-hosts: true", content)
        self.assertIn("  proxy-server-nameserver:\n    - https://1.1.1.1/dns-query\n    - https://8.8.8.8/dns-query", content)
        self.assertIn("  default-nameserver:\n    - 1.1.1.1\n    - 8.8.8.8", content)
        self.assertNotIn("  fallback-filter:", content)



if __name__ == "__main__":
    unittest.main()
