#!/usr/bin/env python3
"""Refresh vendored upstream lists plus canonical distillate text outputs."""

from __future__ import annotations

import argparse
import subprocess
from pathlib import Path

from build_distillate import (
    DistillateError,
    MANIFEST_PATH,
    build_distillate,
    fetch_text,
    iter_external_sources,
    load_manifest,
)


def pull_latest(repo_root: Path) -> None:
    if not (repo_root / ".git").exists():
        print("Skipping git pull: repository metadata not found")
        return
    subprocess.run(["git", "-C", str(repo_root), "pull", "--rebase"], check=True)


def refresh_vendored_sources(repo_root: Path) -> None:
    manifest = load_manifest(repo_root / MANIFEST_PATH)
    targets = iter_external_sources(repo_root, manifest)
    for target in targets:
        cache_path = Path(target["cache_path"])
        url = target["url"]
        label = target["label"]
        try:
            payload = fetch_text(url)
        except DistillateError as exc:
            if cache_path.exists():
                print(f"Warning: keeping cached copy for {label}: {cache_path} ({exc})")
                continue
            raise RuntimeError(f"Failed to fetch required source {label} and no cached copy exists: {exc}") from exc

        cache_path.parent.mkdir(parents=True, exist_ok=True)
        tmp_path = cache_path.with_suffix(cache_path.suffix + ".tmp")
        tmp_path.write_text(payload, encoding="utf-8")
        tmp_path.replace(cache_path)
        print(f"Updated vendored source {label} -> {cache_path.relative_to(repo_root)}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Sync distillate text outputs and legacy rule lists.")
    parser.add_argument(
        "--no-pull",
        action="store_true",
        help="Skip git pull --rebase before syncing.",
    )
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parents[1]
    if not args.no_pull:
        pull_latest(repo_root)
    refresh_vendored_sources(repo_root)
    build_distillate(repo_root, repo_root / MANIFEST_PATH, skip_compiled=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
