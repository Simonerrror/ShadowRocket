from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from scripts.build_happ_routing import existing_build_stamp, resolve_build_stamp


class HappBuildStampTests(unittest.TestCase):
    def test_preserves_existing_stamp_when_explicit_value_is_absent(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            out_dir = root / "HAPP"
            out_dir.mkdir()
            (out_dir / "DEFAULT.JSON").write_text(
                json.dumps({"LastUpdated": "1234567890"}),
                encoding="utf-8",
            )

            self.assertEqual(resolve_build_stamp(root, "", out_dir), "1234567890")

    def test_explicit_stamp_overrides_existing_value(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            out_dir = root / "HAPP"
            out_dir.mkdir()
            (out_dir / "DEFAULT.JSON").write_text(
                json.dumps({"LastUpdated": "1234567890"}),
                encoding="utf-8",
            )

            self.assertEqual(resolve_build_stamp(root, "9876543210", out_dir), "9876543210")

    def test_invalid_existing_json_has_no_preserved_stamp(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            out_dir = Path(tmpdir)
            (out_dir / "DEFAULT.JSON").write_text("not json", encoding="utf-8")

            self.assertIsNone(existing_build_stamp(out_dir))


if __name__ == "__main__":
    unittest.main()
