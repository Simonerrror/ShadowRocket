from __future__ import annotations

import datetime as dt
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
MODULE = REPO_ROOT / "modules" / "eis_transition_tls.module"
MODULE_URL = (
    "https://raw.githubusercontent.com/Simonerrror/ShadowRocket/main/"
    "modules/eis_transition_tls.module"
)


def section_values(content: str, section: str) -> dict[str, str]:
    values: dict[str, str] = {}
    in_section = False
    for raw_line in content.splitlines():
        line = raw_line.strip()
        if line == f"[{section}]":
            in_section = True
            continue
        if in_section and line.startswith("[") and line.endswith("]"):
            break
        if in_section and line and not line.startswith("#"):
            key, value = line.split("=", 1)
            values[key.strip()] = value.strip()
    return values


class EisTransitionTlsModuleTests(unittest.TestCase):
    def test_module_limits_insecure_upstream_tls_to_exact_eis_host(self) -> None:
        self.assertTrue(MODULE.is_file(), f"missing module: {MODULE}")
        content = MODULE.read_text(encoding="utf-8")
        lines = content.splitlines()
        mitm = section_values(content, "MITM")

        self.assertIn(f"#!url={MODULE_URL}", lines)
        self.assertEqual("true", mitm.get("skip-server-cert-verify"))
        self.assertEqual("zakupki.gov.ru", mitm.get("hostname"))
        self.assertNotIn("%APPEND%", mitm["hostname"])
        self.assertNotIn("*", mitm["hostname"])
        self.assertNotIn("ca-p12", mitm)
        self.assertNotIn("ca-passphrase", mitm)
        self.assertNotIn("[Rule]", content)
        self.assertNotIn("ignore-certificate-errors", content)
        self.assertNotIn("skip-cert-verify", content)

    def test_module_has_a_hard_repository_removal_deadline(self) -> None:
        self.assertTrue(MODULE.is_file(), f"missing module: {MODULE}")
        content = MODULE.read_text(encoding="utf-8")
        expires_line = next(
            line for line in content.splitlines() if line.startswith("#!expires=")
        )
        expires = dt.date.fromisoformat(expires_line.split("=", 1)[1])

        self.assertEqual(dt.date(2027, 3, 16), expires)
        self.assertLess(dt.date.today(), expires, "remove the expired EIS TLS exception")


if __name__ == "__main__":
    unittest.main()
