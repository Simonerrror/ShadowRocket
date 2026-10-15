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


VALID_DEFAULT = "incy://routing/onadd/eyJOYW1lIjoiZGVmYXVsdCJ9"
VALID_RU = "incy://routing/onadd/eyJOYW1lIjoicnUifQ=="
VALID_INCY_DEFAULT = "incy://routing/onadd/eyJOYW1lIjoiZGVmYXVsdCJ9"
VALID_INCY_RU = "incy://routing/onadd/eyJOYW1lIjoicnUifQ=="
VALID_INCY_ADD = "incy://routing/add/eyJOYW1lIjoiZGVmYXVsdCJ9"


class PotatoLinkBuildTests(unittest.TestCase):
    def test_build_module_embeds_only_incy_destinations(self) -> None:
        module = build_module(
            VALID_INCY_DEFAULT,
            VALID_INCY_RU,
        )

        self.assertIn(f'incyDefault: "{VALID_INCY_DEFAULT}"', module)
        self.assertIn(f'incyRu: "{VALID_INCY_RU}"', module)

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
