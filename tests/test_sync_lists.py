from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts.sync_lists import refresh_vendored_sources


class SyncListsTests(unittest.TestCase):
    def test_keeps_cached_source_when_fetch_returns_html(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            repo_root = Path(tmp_dir)
            manifest_path = repo_root / "distillate" / "manifest.json"
            manifest_path.parent.mkdir(parents=True)
            manifest_path.write_text(
                json.dumps(
                    {
                        "upstream_dir": "distillate/upstream",
                        "categories": [
                            {
                                "name": "external",
                                "sources": [
                                    {
                                        "type": "url",
                                        "url": "https://example.test/list",
                                        "cache_path": "distillate/upstream/external/list.txt",
                                    }
                                ],
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )
            cache_path = repo_root / "distillate" / "upstream" / "external" / "list.txt"
            cache_path.parent.mkdir(parents=True)
            cache_path.write_text("DOMAIN-SUFFIX,example.com\n", encoding="utf-8")

            with patch("scripts.sync_lists.fetch_text", return_value="<html>gone</html>"):
                refresh_vendored_sources(repo_root)

            self.assertEqual(cache_path.read_text(encoding="utf-8"), "DOMAIN-SUFFIX,example.com\n")


if __name__ == "__main__":
    unittest.main()
