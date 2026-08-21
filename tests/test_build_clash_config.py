from __future__ import annotations

import unittest

from scripts.build_clash_config import (
    DEFAULT_CONF,
    DEFAULT_SUBSCRIPTION_URL,
    SHADOWROCKET_GOOGLE_SUBSCRIPTION_FILTER,
    build_config,
    yaml_quote,
)


EXPECTED_GOOGLE_FILTER = SHADOWROCKET_GOOGLE_SUBSCRIPTION_FILTER
EXPECTED_MIHOMO_MANUAL_EXCLUDE_FILTER = r"(?i)\bWL\b"
EXPECTED_MIHOMO_AUTO_FILTER = r"(?i)\bVLESS\b"
EXPECTED_MIHOMO_AUTO_EXCLUDE_FILTER = r"(?i)Russia|Belarus|Ukraine|\bWL\b"
EXPECTED_MIHOMO_WL_FILTER = r"(?i)\bWL\b"


class BuildClashConfigTests(unittest.TestCase):
    def test_generated_service_routes_keep_google_and_remove_openai(self) -> None:
        content, warnings = build_config(DEFAULT_CONF, DEFAULT_SUBSCRIPTION_URL)

        self.assertNotIn("  openai:", content)
        self.assertNotIn("rules/openai.list", content)
        self.assertNotIn("RULE-SET,openai", content)
        self.assertNotIn("  - name: OPENAI", content)
        self.assertNotIn("OPENAI: unsupported", "\n".join(warnings))
        self.assertIn("  google_all:", content)
        self.assertIn("rules/google-all.list", content)
        self.assertIn("  - RULE-SET,google_all,GOOGLE", content)
        self.assertIn("  - name: GOOGLE", content)
        google_group = content.split("  - name: GOOGLE", 1)[1].split("  - name:", 1)[0]
        self.assertIn("    type: url-test", google_group)
        self.assertIn("    use:\n      - Main-Sub", google_group)
        self.assertIn(f"    filter: {yaml_quote(EXPECTED_GOOGLE_FILTER)}", google_group)
        self.assertNotIn("    exclude-filter:", google_group)
        self.assertIn('    url: "https://abs.twimg.com/favicon.ico"', google_group)
        self.assertIn("    interval: 180", google_group)
        self.assertIn("    tolerance: 100", google_group)

    def test_manual_proxy_uses_the_unfiltered_subscription_with_wl_excluded(self) -> None:
        content, warnings = build_config(DEFAULT_CONF, DEFAULT_SUBSCRIPTION_URL)
        provider = content.split("  Main-Sub:", 1)[1].split("# 4. RULE PROVIDERS", 1)[0]
        self.assertNotIn("    filter:", provider)
        self.assertNotIn("    exclude-filter:", provider)
        manual_group = content.split("  - name: MANUAL-PROXY", 1)[1].split("  - name:", 1)[0]

        self.assertIn("    use:\n      - Main-Sub", manual_group)
        self.assertIn(f"    exclude-filter: {yaml_quote(EXPECTED_MIHOMO_MANUAL_EXCLUDE_FILTER)}", manual_group)
        self.assertNotIn("    filter:", manual_group)
        self.assertNotIn("unsupported proxy-group option use=true", "\n".join(warnings))

    def test_auto_speed_uses_url_test_and_auto_stability_uses_fallback(self) -> None:
        content, _warnings = build_config(DEFAULT_CONF, DEFAULT_SUBSCRIPTION_URL)
        self.assertIn("  - name: AUTO-SPEED", content)
        self.assertIn("  - name: AUTO-STABILITY", content)
        speed_group = content.split("  - name: AUTO-SPEED", 1)[1].split("  - name:", 1)[0]
        stability_group = content.split("  - name: AUTO-STABILITY", 1)[1].split("  - name:", 1)[0]
        proxy_group = content.split("  - name: PROXY", 1)[1].split("# 6. RULES", 1)[0]

        self.assertIn("    type: url-test", speed_group)
        self.assertIn("    type: fallback", stability_group)
        self.assertIn('    url: "https://abs.twimg.com/favicon.ico"', speed_group)
        self.assertIn("    interval: 180", speed_group)
        self.assertIn("    tolerance: 100", speed_group)
        for group in (speed_group, stability_group):
            self.assertIn(f"    filter: {yaml_quote(EXPECTED_MIHOMO_AUTO_FILTER)}", group)
            self.assertIn(f"    exclude-filter: {yaml_quote(EXPECTED_MIHOMO_AUTO_EXCLUDE_FILTER)}", group)
        self.assertIn("      - MANUAL-PROXY", proxy_group)
        self.assertIn("      - AUTO-SPEED", proxy_group)
        self.assertIn("      - AUTO-STABILITY", proxy_group)
        self.assertIn("      - WL", proxy_group)
        self.assertNotIn("      - GOOGLE", proxy_group)
        self.assertNotIn("      - DIRECT", proxy_group)

        wl_group = content.split("  - name: WL", 1)[1].split("  - name:", 1)[0]
        self.assertIn("    type: select", wl_group)
        self.assertIn(f"    filter: {yaml_quote(EXPECTED_MIHOMO_WL_FILTER)}", wl_group)


if __name__ == "__main__":
    unittest.main()
