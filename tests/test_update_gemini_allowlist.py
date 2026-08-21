from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from scripts.update_gemini_allowlist import build_filter, load_names, update_profile


class UpdateGeminiAllowlistTests(unittest.TestCase):
    def test_empty_allowlist_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "allowlist.txt"
            path.write_text("\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "must not be empty"):
                load_names(path)

    def test_allowlist_is_escaped_anchored_and_only_updates_google_filter(self) -> None:
        regex_filter = build_filter(["France(LK) Vless", "Singapore PS SS"])
        self.assertEqual(r"(?i)^(?:France\(LK\)\ Vless|Singapore\ PS\ SS)$", regex_filter)
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "profile.conf"
            path.write_text(
                "before = unchanged\n"
                "GOOGLE = url-test,policy-regex-filter=old,interval=180,tolerance=100,"
                "url=https://abs.twimg.com/favicon.ico,timeout=7\n"
                "after = unchanged\n",
                encoding="utf-8",
            )
            update_profile(path, regex_filter)
            self.assertEqual(
                path.read_text(encoding="utf-8"),
                "before = unchanged\n"
                f"GOOGLE = url-test,policy-regex-filter={regex_filter},interval=180,tolerance=100,"
                "url=https://abs.twimg.com/favicon.ico,timeout=7\n"
                "after = unchanged\n",
            )


if __name__ == "__main__":
    unittest.main()
