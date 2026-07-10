from __future__ import annotations

import unittest
from unittest.mock import patch

from scripts.build_distillate import DistillateError, fetch_text


class FakeResponse:
    def __init__(self, payload: bytes) -> None:
        self.payload = payload
        self.offset = 0

    def __enter__(self) -> "FakeResponse":
        return self

    def __exit__(self, *_args: object) -> None:
        return None

    def read(self, size: int = -1) -> bytes:
        if size < 0:
            size = len(self.payload) - self.offset
        chunk = self.payload[self.offset : self.offset + size]
        self.offset += len(chunk)
        return chunk


class FetchTextTests(unittest.TestCase):
    def test_rejects_non_https_url(self) -> None:
        with self.assertRaisesRegex(DistillateError, "HTTPS"):
            fetch_text("http://example.com/list.txt")

    @patch("scripts.build_distillate.urlopen")
    def test_rejects_empty_payload(self, mock_urlopen: object) -> None:
        mock_urlopen.return_value = FakeResponse(b"")

        with self.assertRaisesRegex(DistillateError, "empty"):
            fetch_text("https://example.com/list.txt", attempts=1)

    @patch("scripts.build_distillate.urlopen")
    def test_rejects_payload_over_size_limit(self, mock_urlopen: object) -> None:
        mock_urlopen.return_value = FakeResponse(b"a" * 17)

        with self.assertRaisesRegex(DistillateError, "exceeds"):
            fetch_text("https://example.com/list.txt", attempts=1, max_bytes=16)

    @patch("scripts.build_distillate.urlopen")
    def test_rejects_invalid_utf8(self, mock_urlopen: object) -> None:
        mock_urlopen.return_value = FakeResponse(b"\xff")

        with self.assertRaisesRegex(DistillateError, "UTF-8"):
            fetch_text("https://example.com/list.txt", attempts=1)


if __name__ == "__main__":
    unittest.main()
