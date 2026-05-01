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

    def test_openai_group_includes_uae_vless_nodes(self) -> None:
        content, _warnings = build_config(DEFAULT_CONF, DEFAULT_SUBSCRIPTION_URL)
        openai_group = content.split("  - name: OPENAI", 1)[1].split("  - name:", 1)[0]

        self.assertIn("UAE.*Vless", openai_group)
        self.assertIn("Vless.*UAE", openai_group)


if __name__ == "__main__":
    unittest.main()
