from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from scripts.update_gemini_allowlist import build_filter, load_names, update_profile


class UpdateGeminiAllowlistTests(unittest.TestCase):
    def test_build_filter_is_anchored_and_escapes_names(self) -> None:
        result = build_filter(["France(LK) Vless", "Singapore PS SS"])
        self.assertEqual(r"(?i)^(?:France\(LK\)\ Vless|Singapore\ PS\ SS)$", result)

    def test_empty_allowlist_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "allowlist.txt"
            path.write_text("\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "must not be empty"):
                load_names(path)

    def test_update_profile_replaces_only_google_filter(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "profile.conf"
            path.write_text(
                "GOOGLE = url-test,policy-regex-filter=old,interval=180,tolerance=100,"
                "url=https://abs.twimg.com/favicon.ico,timeout=7\n",
                encoding="utf-8",
            )
            update_profile(path, r"(?i)^(?:France\(LK\))$")
            self.assertIn(r"policy-regex-filter=(?i)^(?:France\(LK\))$", path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
