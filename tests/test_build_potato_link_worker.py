from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from scripts.build_potato_link_worker import (
    MAX_DEEPLINK_LENGTH,
    build_module,
    read_deeplink,
    validate_deeplink,
)


VALID_DEFAULT = "happ://routing/onadd/eyJOYW1lIjoiZGVmYXVsdCJ9"
VALID_RU = "happ://routing/onadd/eyJOYW1lIjoicnUifQ=="


class PotatoLinkBuildTests(unittest.TestCase):
    def test_build_module_embeds_both_destinations(self) -> None:
        module = build_module(VALID_DEFAULT, VALID_RU)

        self.assertIn(f'default: "{VALID_DEFAULT}"', module)
        self.assertIn(f'ru: "{VALID_RU}"', module)

    def test_read_deeplink_accepts_one_trailing_lf(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "profile.DEEPLINK"
            path.write_text(VALID_DEFAULT + "\n", encoding="utf-8")

            self.assertEqual(read_deeplink(path), VALID_DEFAULT)

    def test_rejects_multiline_input(self) -> None:
        with self.assertRaisesRegex(ValueError, "single line"):
            validate_deeplink(VALID_DEFAULT + "\n" + VALID_RU, Path("bad"))

    def test_rejects_unexpected_scheme(self) -> None:
        with self.assertRaisesRegex(ValueError, "prefix"):
            validate_deeplink("https://example.com/value", Path("bad"))

    def test_rejects_invalid_base64(self) -> None:
        with self.assertRaisesRegex(ValueError, "base64"):
            validate_deeplink("happ://routing/onadd/not-valid!", Path("bad"))

    def test_rejects_oversized_input(self) -> None:
        value = "happ://routing/onadd/" + ("A" * MAX_DEEPLINK_LENGTH)

        with self.assertRaisesRegex(ValueError, "16 KiB"):
            validate_deeplink(value, Path("bad"))


if __name__ == "__main__":
    unittest.main()
