from __future__ import annotations

import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
BASE_CONF = REPO_ROOT / "shadowrocket.conf"
CUSTOM_CONF = REPO_ROOT / "shadowrocket_custom.conf"
PRIVATE_DNS_CONF = REPO_ROOT / "shadowrocket_custom_private_dns.conf"
TAILSCALE_MODULE = REPO_ROOT / "modules" / "tailscale_direct.module"


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
    def test_proxy_groups_match_across_main_profiles(self) -> None:
        base_groups = section_lines(BASE_CONF, "Proxy Group")

        self.assertEqual(base_groups, section_lines(CUSTOM_CONF, "Proxy Group"))
        self.assertEqual(base_groups, section_lines(PRIVATE_DNS_CONF, "Proxy Group"))

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

        self.assertNotIn("100.100.100.100", profile_contents)
        self.assertNotIn("ts.net", profile_contents)
        self.assertNotIn("tailscale.com", profile_contents)
        self.assertIn("100.100.100.100", module_content)
        self.assertIn("DOMAIN-SUFFIX,ts.net,DIRECT", module_content)
        self.assertIn("DOMAIN-SUFFIX,tailscale.com,DIRECT", module_content)

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
