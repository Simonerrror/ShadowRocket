from __future__ import annotations

import unittest

from scripts.build_clash_config import DEFAULT_CONF, DEFAULT_SUBSCRIPTION_URL, build_config


class BuildClashConfigTests(unittest.TestCase):
    def test_openai_rule_provider_routes_to_openai_group(self) -> None:
        content, warnings = build_config(DEFAULT_CONF, DEFAULT_SUBSCRIPTION_URL)

        self.assertIn("  openai:", content)
        self.assertIn("rules/openai.list", content)
        self.assertIn("  - RULE-SET,openai,OPENAI", content)
        self.assertIn("  - name: OPENAI", content)
        self.assertNotIn("OPENAI: unsupported", "\n".join(warnings))

    def test_openai_group_includes_uae_nodes_without_protocol_filter(self) -> None:
        content, _warnings = build_config(DEFAULT_CONF, DEFAULT_SUBSCRIPTION_URL)
        openai_group = content.split("  - name: OPENAI", 1)[1].split("  - name:", 1)[0]

        self.assertIn("USA|United States|Finland|Poland|Germany|UAE", openai_group)
        self.assertNotIn("Vless", openai_group)

    def test_subscription_provider_has_no_protocol_filter(self) -> None:
        content, _warnings = build_config(DEFAULT_CONF, DEFAULT_SUBSCRIPTION_URL)
        provider = content.split("  Main-Sub:", 1)[1].split("# 4. RULE PROVIDERS", 1)[0]

        self.assertNotIn("    filter:", provider)
        self.assertIn('exclude-filter: "(?i)(Russia|Belarus|Ukraine)"', provider)

    def test_manual_proxy_uses_subscription_without_filter(self) -> None:
        content, _warnings = build_config(DEFAULT_CONF, DEFAULT_SUBSCRIPTION_URL)
        manual_group = content.split("  - name: MANUAL-PROXY", 1)[1].split("  - name:", 1)[0]

        self.assertIn("    use:\n      - Main-Sub", manual_group)
        self.assertNotIn("    filter:", manual_group)


if __name__ == "__main__":
    unittest.main()
