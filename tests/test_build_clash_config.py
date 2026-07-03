from __future__ import annotations

import unittest

from scripts.build_clash_config import DEFAULT_CONF, DEFAULT_SUBSCRIPTION_URL, build_config


class BuildClashConfigTests(unittest.TestCase):
    def test_openai_rule_provider_is_removed(self) -> None:
        content, warnings = build_config(DEFAULT_CONF, DEFAULT_SUBSCRIPTION_URL)

        self.assertNotIn("  openai:", content)
        self.assertNotIn("rules/openai.list", content)
        self.assertNotIn("RULE-SET,openai", content)
        self.assertNotIn("  - name: OPENAI", content)
        self.assertNotIn("OPENAI: unsupported", "\n".join(warnings))

    def test_google_rule_provider_routes_to_google_group(self) -> None:
        content, _warnings = build_config(DEFAULT_CONF, DEFAULT_SUBSCRIPTION_URL)

        self.assertIn("  google_all:", content)
        self.assertIn("rules/google-all.list", content)
        self.assertIn("  - RULE-SET,google_all,GOOGLE", content)
        self.assertIn("  - name: GOOGLE", content)
        google_group = content.split("  - name: GOOGLE", 1)[1].split("  - name:", 1)[0]
        self.assertIn("    type: select", google_group)
        self.assertIn("    use:\n      - Main-Sub", google_group)
        self.assertNotIn("    filter:", google_group)

    def test_subscription_provider_is_unfiltered_for_manual_selection(self) -> None:
        content, _warnings = build_config(DEFAULT_CONF, DEFAULT_SUBSCRIPTION_URL)
        provider = content.split("  Main-Sub:", 1)[1].split("# 4. RULE PROVIDERS", 1)[0]

        self.assertNotIn("    filter:", provider)
        self.assertNotIn("    exclude-filter:", provider)

    def test_manual_proxy_uses_subscription_without_filter(self) -> None:
        content, _warnings = build_config(DEFAULT_CONF, DEFAULT_SUBSCRIPTION_URL)
        manual_group = content.split("  - name: MANUAL-PROXY", 1)[1].split("  - name:", 1)[0]

        self.assertIn("    use:\n      - Main-Sub", manual_group)
        self.assertNotIn("    filter:", manual_group)

    def test_auto_speed_uses_url_test_and_auto_stability_uses_fallback(self) -> None:
        content, _warnings = build_config(DEFAULT_CONF, DEFAULT_SUBSCRIPTION_URL)
        self.assertIn("  - name: AUTO-SPEED", content)
        self.assertIn("  - name: AUTO-STABILITY", content)
        speed_group = content.split("  - name: AUTO-SPEED", 1)[1].split("  - name:", 1)[0]
        stability_group = content.split("  - name: AUTO-STABILITY", 1)[1].split("  - name:", 1)[0]
        proxy_group = content.split("  - name: PROXY", 1)[1].split("# 6. RULES", 1)[0]

        self.assertIn("    type: url-test", speed_group)
        self.assertIn("    type: fallback", stability_group)
        self.assertNotIn("    filter:", speed_group)
        self.assertNotIn("    filter:", stability_group)
        self.assertIn("      - MANUAL-PROXY", proxy_group)
        self.assertIn("      - AUTO-SPEED", proxy_group)
        self.assertIn("      - AUTO-STABILITY", proxy_group)
        self.assertNotIn("      - AUTO-WL", proxy_group)
        self.assertNotIn("      - WL", proxy_group)


if __name__ == "__main__":
    unittest.main()
