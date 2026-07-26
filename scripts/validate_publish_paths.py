#!/usr/bin/env python3
"""Reject release changes outside the generated artifact allowlist."""

from __future__ import annotations

import re
import subprocess
from pathlib import Path


GENERATED_RULES = {
    "rules/anti_advertising.list",
    "rules/domains_community.list",
    "rules/google-all.list",
    "rules/greylist_proxy.list",
    "rules/microsoft.list",
    "rules/openai.list",
    "rules/telegram.list",
    "rules/whitelist_direct.list",
}
GENERATED_MODULES = {
    "modules/anti_advertising.module",
    "modules/anti_advertising_custom.module",
}
GENERATED_FILES = {
    "clash_config.yaml",
    "distillate/summary.json",
    "HAPP/DEFAULT.JSON",
    "HAPP/DEFAULT.DEEPLINK",
    "HAPP/RU-VPN.JSON",
    "HAPP/RU-VPN.DEEPLINK",
    *GENERATED_RULES,
    *GENERATED_MODULES,
}
GENERATED_PREFIXES = (
    "distillate/upstream/",
    "distillate/text/",
    "distillate/dat/",
)
ANTI_AD_CHUNK = re.compile(r"rules/anti_advertising\.\d{2}\.list\Z")


def is_allowed_publish_path(path: str) -> bool:
    candidate = Path(path)
    if candidate.is_absolute() or ".." in candidate.parts:
        return False
    normalized = candidate.as_posix()
    if normalized.startswith("./"):
        normalized = normalized[2:]
    return (
        normalized in GENERATED_FILES
        or normalized.startswith(GENERATED_PREFIXES)
        or ANTI_AD_CHUNK.fullmatch(normalized) is not None
    )


def git_paths(args: list[str]) -> list[str]:
    result = subprocess.run(
        ["git", *args],
        check=True,
        stdout=subprocess.PIPE,
        text=True,
    )
    return [line for line in result.stdout.splitlines() if line]


def changed_paths() -> list[str]:
    return sorted(
        set(
            git_paths(["diff", "--name-only", "--no-renames", "HEAD"])
            + git_paths(["ls-files", "--others", "--exclude-standard"])
        )
    )


def main() -> int:
    paths = changed_paths()
    rejected = [path for path in paths if not is_allowed_publish_path(path)]
    if rejected:
        print("Release contains paths outside the publish allowlist:")
        for path in rejected:
            print(f"  - {path}")
        return 1
    print(f"Publish path validation passed for {len(paths)} changed paths")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
