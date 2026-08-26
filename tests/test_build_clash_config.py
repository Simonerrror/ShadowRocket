from __future__ import annotations

import unittest

from scripts.build_clash_config import (
    DEFAULT_CONF,
    DEFAULT_SUBSCRIPTION_URL,
    build_config,
    yaml_quote,
)


EXPECTED_MIHOMO_MANUAL_EXCLUDE_FILTER = r"(?i)\b(?:WL|SS)\b"
EXPECTED_MIHOMO_AUTO_FILTER = r"(?i)\b(?:VLESS|TT|Naive|NV|MR|AWG2)\b"
EXPECTED_MIHOMO_AUTO_EXCLUDE_FILTER = r"(?i)Russia|Belarus|Ukraine|\bWL\b"
EXPECTED_MIHOMO_WL_FILTER = r"(?i)\bWL\b"


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

    def test_manual_proxy_excludes_wl_and_ss_from_the_subscription(self) -> None:
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
