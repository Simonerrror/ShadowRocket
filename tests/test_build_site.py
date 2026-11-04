from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from scripts.build_site import (
    MAX_DEEPLINK_LENGTH,
    build_page,
    read_deeplink,
    validate_deeplink,
)


VALID_DEFAULT = "incy://routing/onadd/eyJOYW1lIjoiZGVmYXVsdCJ9"
VALID_RU = "incy://routing/onadd/eyJOYW1lIjoicnUifQ=="
VALID_INCY_DEFAULT = "incy://routing/onadd/eyJOYW1lIjoiZGVmYXVsdCJ9"
VALID_INCY_RU = "incy://routing/onadd/eyJOYW1lIjoicnUifQ=="
VALID_INCY_ADD = "incy://routing/add/eyJOYW1lIjoiZGVmYXVsdCJ9"


class SiteBuildTests(unittest.TestCase):
    def test_template_requires_each_incy_button_once(self) -> None:
        for template in ('{{INCY_DEFAULT}}', '{{INCY_DEFAULT}}{{INCY_RU}}{{INCY_RU}}'):
            with self.subTest(template=template):
                with self.assertRaisesRegex(ValueError, "exactly one"):
                    build_page(template, VALID_DEFAULT, VALID_RU)

    def test_cli_renders_html_instead_of_a_worker_module(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            template = root / "template.html"
            default = root / "default.DEEPLINK"
            ru = root / "ru.DEEPLINK"
            output = root / "index.html"
            template.write_text('<a href="{{INCY_DEFAULT}}">Default</a><a href="{{INCY_RU}}">RU</a>')
            default.write_text(VALID_DEFAULT)
            ru.write_text(VALID_RU)
            result = subprocess.run([
                sys.executable, "scripts/build_site.py", "--template", str(template),
                "--incy-default-input", str(default), "--incy-ru-input", str(ru),
                "--output", str(output),
            ], cwd=Path(__file__).resolve().parents[1], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(output.read_text(),
                             f'<a href="{VALID_DEFAULT}">Default</a><a href="{VALID_RU}">RU</a>')

    def test_read_deeplink_accepts_one_trailing_lf(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "profile.DEEPLINK"
            path.write_text(VALID_DEFAULT + "\n", encoding="utf-8")

            self.assertEqual(read_deeplink(path), VALID_DEFAULT)

    def test_validation_accepts_supported_modes_and_rejects_unsafe_inputs(self) -> None:
        self.assertEqual(
            validate_deeplink(VALID_INCY_ADD, Path("incy-add"), scheme="incy"),
            VALID_INCY_ADD,
        )
        cases = (
            (VALID_DEFAULT + "\n" + VALID_RU, "incy", "single line"),
            ("https://example.com/value", "incy", "prefix"),
            ("happ://routing/onadd/e30=", "incy", "prefix"),

            ("incy://routing/onadd/not-valid!", "incy", "base64"),
            ("incy://routing/onadd/" + ("A" * MAX_DEEPLINK_LENGTH), "incy", "16 KiB"),
        )
        for value, scheme, message in cases:
            with self.subTest(message=message, scheme=scheme):
                with self.assertRaisesRegex(ValueError, message):
                    validate_deeplink(value, Path("bad"), scheme=scheme)


    def test_validation_rejects_malformed_base64_lengths_and_padding(self) -> None:
        for payload in ("A", "AB=", "AB==", "ABC==", "AAAA="):
            with self.subTest(payload=payload):
                with self.assertRaisesRegex(ValueError, "base64"):
                    validate_deeplink(
                        f"incy://routing/onadd/{payload}",
                        Path("bad"),
                    )


if __name__ == "__main__":
    unittest.main()
