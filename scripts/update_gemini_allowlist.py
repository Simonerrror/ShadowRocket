#!/usr/bin/env python3
"""Update published GOOGLE filters from a fail-closed node-name allowlist."""

from __future__ import annotations

import argparse
import re
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_ALLOWLIST = REPO_ROOT / "gemini_node_allowlist.txt"
PROFILE_PATHS = (
    REPO_ROOT / "shadowrocket.conf",
    REPO_ROOT / "shadowrocket_custom.conf",
)
GOOGLE_LINE_RE = re.compile(
    r"^(GOOGLE = url-test,policy-regex-filter=).*?(,interval=180,tolerance=100,url=https://abs\.twimg\.com/favicon\.ico,timeout=7)$",
    re.MULTILINE,
)


def load_names(path: Path) -> list[str]:
    names = [line.strip() for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    if not names:
        raise ValueError("Gemini allowlist must not be empty")
    if len(names) != len(set(names)):
        raise ValueError("Gemini allowlist contains duplicate names")
    return names


def build_filter(names: list[str]) -> str:
    return "(?i)^(?:" + "|".join(re.escape(name) for name in names) + ")$"


def update_profile(path: Path, regex_filter: str) -> None:
    original = path.read_text(encoding="utf-8")
    updated, count = GOOGLE_LINE_RE.subn(rf"\g<1>{regex_filter}\g<2>", original)
    if count != 1:
        raise ValueError(f"expected one GOOGLE group in {path}, found {count}")
    if updated != original:
        path.write_text(updated, encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--allowlist", type=Path, default=DEFAULT_ALLOWLIST)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    regex_filter = build_filter(load_names(args.allowlist))
    for path in PROFILE_PATHS:
        if "GOOGLE = url-test" in path.read_text(encoding="utf-8"):
            update_profile(path, regex_filter)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
