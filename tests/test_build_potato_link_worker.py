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
VALID_INCY_DEFAULT = "incy://routing/onadd/eyJOYW1lIjoiZGVmYXVsdCJ9"
VALID_INCY_RU = "incy://routing/onadd/eyJOYW1lIjoicnUifQ=="
VALID_INCY_ADD = "incy://routing/add/eyJOYW1lIjoiZGVmYXVsdCJ9"


class PotatoLinkBuildTests(unittest.TestCase):
    def test_build_module_embeds_all_four_scheme_specific_destinations(self) -> None:
        module = build_module(
            VALID_DEFAULT,
            VALID_RU,
            VALID_INCY_DEFAULT,
            VALID_INCY_RU,
        )

        self.assertIn(f'default: "{VALID_DEFAULT}"', module)
        self.assertIn(f'ru: "{VALID_RU}"', module)
        self.assertIn(f'incyDefault: "{VALID_INCY_DEFAULT}"', module)
        self.assertIn(f'incyRu: "{VALID_INCY_RU}"', module)

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

    def test_validate_deeplink_requires_matching_scheme_prefix(self) -> None:
        with self.assertRaisesRegex(ValueError, "prefix"):
            validate_deeplink(VALID_INCY_DEFAULT, Path("bad"), scheme="happ")

        with self.assertRaisesRegex(ValueError, "prefix"):
            validate_deeplink(VALID_DEFAULT, Path("bad"), scheme="incy")

    def test_validate_deeplink_accepts_supported_add_mode(self) -> None:
        self.assertEqual(
            validate_deeplink(VALID_INCY_ADD, Path("incy-add"), scheme="incy"),
            VALID_INCY_ADD,
        )

    def test_rejects_invalid_base64(self) -> None:
        with self.assertRaisesRegex(ValueError, "base64"):
            validate_deeplink("happ://routing/onadd/not-valid!", Path("bad"))

    def test_rejects_oversized_input(self) -> None:
        value = "happ://routing/onadd/" + ("A" * MAX_DEEPLINK_LENGTH)

        with self.assertRaisesRegex(ValueError, "16 KiB"):
            validate_deeplink(value, Path("bad"))


if __name__ == "__main__":
    unittest.main()
