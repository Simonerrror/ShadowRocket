from __future__ import annotations

import ipaddress
import json
import tempfile
import unittest
from pathlib import Path

from scripts.build_amnezia_routing import (
    FIXED_EXCLUSIONS,
    AmneziaRoutingError,
    build_artifacts,
)


class BuildAmneziaRoutingTests(unittest.TestCase):
    def _write(self, root: Path, relative: str, content: str) -> Path:
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        return path

    def test_builds_ipv4_exclusion_profile_with_canonical_numeric_order(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            ru_path = self._write(
                root,
                "ru_ipv4.txt",
                "203.0.113.128/25\n203.0.113.0/25\n203.0.113.128/25\n",
            )
            direct_ip_path = self._write(
                root,
                "sr-direct.txt",
                "198.51.100.1/32\n198.51.100.0/31\n192.0.2.0/31\n",
            )
            direct_domain_path = self._write(
                root,
                "sr-direct-domain.txt",
                "full:example.org\n# ignored comments are not domain rules\n",
            )
            output_path = root / "Amnezia/SR-DEFAULT-EXCLUDE.json"
            summary_path = root / "Amnezia/SR-DEFAULT-EXCLUDE.summary.json"

            result = build_artifacts(
                ru_path,
                direct_ip_path,
                direct_domain_path,
                output_path,
                summary_path,
            )

            expected = [
                "10.0.0.0/8",
                "100.64.0.0/10",
                "169.254.0.0/16",
                "172.16.0.0/12",
                "192.0.2.0/31",
                "192.168.0.0/16",
                "198.51.100.0/31",
                "203.0.113.0/24",
                "224.0.0.0/4",
            ]
            self.assertEqual(result["cidrs"], expected)
            profile = json.loads(output_path.read_text(encoding="utf-8"))
            self.assertEqual(
                profile,
                [
                    {
                        "hostname": (
                            f"cidr-{cidr.split('/')[0].replace('.', '-')}-"
                            f"{cidr.split('/')[1]}.invalid"
                        ),
                        "ip": cidr,
                    }
                    for cidr in expected
                ],
            )
            self.assertEqual(len(profile), len({entry["hostname"] for entry in profile}))
            for entry in profile:
                with self.subTest(cidr=entry["ip"]):
                    self.assertNotIn("/", entry["hostname"])
                    self.assertEqual(entry["ip"], str(ipaddress.ip_network(entry["ip"])))
            self.assertEqual(output_path.read_text(encoding="utf-8")[-1], "\n")

            summary = json.loads(summary_path.read_text(encoding="utf-8"))
            self.assertEqual(summary["mode"], "exclude-vpn")
            self.assertIn("all other IPv4", summary["intent"])
            self.assertEqual(
                summary["encoding"],
                {
                    "hostname": "cidr-<network-octets>-<prefix>.invalid",
                    "ip": "canonical IPv4 CIDR",
                    "note": "CIDR stays in ip because the Amnezia importer strips '/' from hostname",
                },
            )
            self.assertEqual(summary["sources"]["ru_ipv4"]["count"], 3)
            self.assertEqual(summary["sources"]["sr_direct_ipv4"]["count"], 3)
            self.assertEqual(summary["sources"]["fixed_exclusions"]["count"], len(FIXED_EXCLUSIONS))
            self.assertEqual(
                summary["unrepresented_domain_direct_rules"],
                {"count": 1, "entries": ["full:example.org"]},
            )

    def test_invalid_input_keeps_existing_outputs_untouched(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            ru_path = self._write(root, "ru_ipv4.txt", "203.0.113.0/24\n")
            direct_ip_path = self._write(root, "sr-direct.txt", "2001:db8::/32\n")
            direct_domain_path = self._write(root, "sr-direct-domain.txt", "domain:example.org\n")
            output_path = root / "Amnezia/SR-DEFAULT-EXCLUDE.json"
            summary_path = root / "Amnezia/SR-DEFAULT-EXCLUDE.summary.json"
            output_path.parent.mkdir(parents=True)
            output_path.write_text("old profile\n", encoding="utf-8")
            summary_path.write_text("old summary\n", encoding="utf-8")

            with self.assertRaisesRegex(AmneziaRoutingError, "IPv4 CIDR"):
                build_artifacts(
                    ru_path,
                    direct_ip_path,
                    direct_domain_path,
                    output_path,
                    summary_path,
                )

            self.assertEqual(output_path.read_text(encoding="utf-8"), "old profile\n")
            self.assertEqual(summary_path.read_text(encoding="utf-8"), "old summary\n")

    def test_missing_or_empty_ru_source_creates_no_outputs(self) -> None:
        for source, message in ((None, "missing"), ("# compiler output was empty\n", "empty")):
            with self.subTest(message=message), tempfile.TemporaryDirectory() as tmpdir:
                root = Path(tmpdir)
                ru_path = root / "ru_ipv4.txt"
                if source is not None:
                    self._write(root, "ru_ipv4.txt", source)
                direct_ip_path = self._write(root, "sr-direct.txt", "203.0.113.1/32\n")
                direct_domain_path = self._write(root, "sr-direct-domain.txt", "domain:example.org\n")
                output_path = root / "Amnezia/SR-DEFAULT-EXCLUDE.json"
                summary_path = root / "Amnezia/SR-DEFAULT-EXCLUDE.summary.json"

                with self.assertRaisesRegex(AmneziaRoutingError, message):
                    build_artifacts(ru_path, direct_ip_path, direct_domain_path, output_path, summary_path)

                self.assertFalse(output_path.exists())
                self.assertFalse(summary_path.exists())


if __name__ == "__main__":
    unittest.main()
