#!/usr/bin/env python3
"""Build and publish source-branch artifacts into the release branch worktree."""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
COPY_IGNORE = shutil.ignore_patterns(".DS_Store", "__pycache__")
CUSTOM_RELEASE_PATHS = (
    Path("shadowrocket_custom.conf"),
    Path("modules/GFN-AM.module"),
    Path("modules/anti_advertising_custom.module"),
    Path("rules/adobe_telemetry_custom.list"),
)
SHARED_CACHE_PATH = Path("distillate/upstream")
EXCLUDED_ROOT_NAMES = {".git", ".DS_Store", "__pycache__"}
ANTI_AD_RULE_GLOB = "anti_advertising.[0-9][0-9].list"
ANTI_AD_RULE_PREFIX = "RULE-SET, https://raw.githubusercontent.com/Simonerrror/ShadowRocket/main/rules/"


def run(cmd: list[str], cwd: Path | None = None) -> None:
    subprocess.run(cmd, cwd=str(cwd) if cwd else None, check=True)


def remove_path(path: Path) -> None:
    if not path.exists():
        return
    if path.is_dir() and not path.is_symlink():
        shutil.rmtree(path)
        return
    path.unlink()


def copy_path(source: Path, target: Path) -> None:
    if not source.exists():
        remove_path(target)
        return
    remove_path(target)
    target.parent.mkdir(parents=True, exist_ok=True)
    if source.is_dir():
        shutil.copytree(source, target, ignore=COPY_IGNORE)
    else:
        shutil.copy2(source, target)


def replace_root_contents(source_root: Path, publish_root: Path) -> None:
    for child in publish_root.iterdir():
        if child.name in EXCLUDED_ROOT_NAMES:
            continue
        remove_path(child)

    for child in source_root.iterdir():
        if child.name in EXCLUDED_ROOT_NAMES:
            continue
        copy_path(child, publish_root / child.name)


def hydrate_cache_from_publish(source_root: Path, publish_root: Path) -> None:
    publish_cache = publish_root / SHARED_CACHE_PATH
    if not publish_cache.exists():
        return
    copy_path(publish_cache, source_root / SHARED_CACHE_PATH)


def build_shared_release(source_root: Path, build_stamp: str) -> None:
    run([sys.executable, str(source_root / "scripts" / "sync_lists.py"), "--no-pull"], cwd=source_root)
    run([sys.executable, str(source_root / "scripts" / "build_distillate.py")], cwd=source_root)
    run(
        [
            sys.executable,
            str(source_root / "scripts" / "build_xkeen_routing.py"),
            "--conf",
            str(source_root / "shadowrocket.conf"),
        ],
        cwd=source_root,
    )
    happ_cmd = [
        sys.executable,
        str(source_root / "scripts" / "build_happ_routing.py"),
    ]
    if build_stamp:
        happ_cmd.extend(["--build-stamp", build_stamp])
    run(happ_cmd, cwd=source_root)


def anti_ad_chunk_rule_lines(publish_root: Path) -> list[str]:
    chunk_paths = sorted((publish_root / "rules").glob(ANTI_AD_RULE_GLOB))
    return [f"{ANTI_AD_RULE_PREFIX}{path.name},REJECT" for path in chunk_paths]


def rewrite_module_chunks(module_path: Path, chunk_lines: list[str]) -> None:
    if not module_path.exists():
        return

    lines = module_path.read_text(encoding="utf-8").splitlines()
    kept_lines = [
        line
        for line in lines
        if "anti_advertising.list,REJECT" not in line and "anti_advertising." not in line
    ]
    if chunk_lines:
        if kept_lines and kept_lines[-1] != "":
            kept_lines.append("")
        kept_lines.extend(chunk_lines)
    module_path.write_text("\n".join(kept_lines) + "\n", encoding="utf-8")


def rewrite_anti_ad_modules(publish_root: Path) -> None:
    chunk_lines = anti_ad_chunk_rule_lines(publish_root)
    rewrite_module_chunks(publish_root / "modules" / "anti_advertising.module", chunk_lines)
    rewrite_module_chunks(publish_root / "modules" / "anti_advertising_custom.module", chunk_lines)


def publish_custom_release(source_root: Path, publish_root: Path) -> None:
    for rel_path in CUSTOM_RELEASE_PATHS:
        copy_path(source_root / rel_path, publish_root / rel_path)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Publish source-branch outputs into a release worktree.")
    parser.add_argument(
        "--channel",
        choices=["shared", "custom"],
        required=True,
        help="Release channel to publish.",
    )
    parser.add_argument(
        "--publish-dir",
        type=Path,
        required=True,
        help="Path to the checked-out release branch worktree.",
    )
    parser.add_argument(
        "--build-stamp",
        default="",
        help="Stable LastUpdated value passed to HAPP generation.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    source_root = REPO_ROOT
    publish_root = args.publish_dir.resolve()

    if args.channel == "shared":
        hydrate_cache_from_publish(source_root, publish_root)
        build_shared_release(source_root, args.build_stamp)
        replace_root_contents(source_root, publish_root)
        rewrite_anti_ad_modules(publish_root)
        return 0

    publish_custom_release(source_root, publish_root)
    rewrite_anti_ad_modules(publish_root)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
