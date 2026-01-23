#!/usr/bin/env python3
"""Sync rule lists from upstream repositories."""

from __future__ import annotations

import argparse
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable
from urllib.request import Request, urlopen


@dataclass(frozen=True)
class RuleSource:
    path: Path
    url: str
    reason: str


RULE_SOURCES: tuple[RuleSource, ...] = (
    RuleSource(
        path=Path("rules/google.list"),
        url=(
            "https://raw.githubusercontent.com/blackmatrix7/ios_rule_script/"
            "master/rule/Shadowrocket/Google/Google.list"
        ),
        reason="Upstream list from blackmatrix7",
    ),
    RuleSource(
        path=Path("rules/microsoft.list"),
        url=(
            "https://raw.githubusercontent.com/blackmatrix7/ios_rule_script/"
            "master/rule/Shadowrocket/Microsoft/Microsoft.list"
        ),
        reason="Upstream list from blackmatrix7 for MS365/Teams/Office",
    ),
    RuleSource(
        path=Path("rules/telegram.list"),
        url=(
            "https://raw.githubusercontent.com/blackmatrix7/ios_rule_script/"
            "master/rule/Shadowrocket/Telegram/Telegram.list"
        ),
        reason="Upstream list from blackmatrix7",
    ),
    RuleSource(
        path=Path("rules/youtube.list"),
        url=(
            "https://raw.githubusercontent.com/blackmatrix7/ios_rule_script/"
            "master/rule/Shadowrocket/YouTube/YouTube.list"
        ),
        reason="Upstream list from blackmatrix7",
    ),
    RuleSource(
        path=Path("rules/youtubemusic.list"),
        url=(
            "https://raw.githubusercontent.com/blackmatrix7/ios_rule_script/"
            "master/rule/Shadowrocket/YouTubeMusic/YouTubeMusic.list"
        ),
        reason="Upstream list from blackmatrix7",
    ),
    RuleSource(
        path=Path("rules/domain_ips.list"),
        url=(
            "https://raw.githubusercontent.com/misha-tgshv/"
            "shadowrocket-configuration-file/main/rules/domain_ips.list"
        ),
        reason="Upstream list from misha-tgshv",
    ),
    RuleSource(
        path=Path("rules/voice_ports.list"),
        url=(
            "https://raw.githubusercontent.com/misha-tgshv/"
            "shadowrocket-configuration-file/main/rules/voice_ports.list"
        ),
        reason="Upstream list from misha-tgshv",
    ),
    # RuleSource(
    #     path=Path("rules/domains_community.list"),
    #     url=(
    #         "https://raw.githubusercontent.com/misha-tgshv/"
    #         "shadowrocket-configuration-file/main/rules/domains_community.list"
    #     ),
    #     reason="Manual list in this repo; keep manual control",
    # ),
    # RuleSource(
    #     path=Path("rules/gemini_ip.list"),
    #     url="",
    #     reason="Local list in this repo; keep manual control",
    # ),
    # RuleSource(
    #     path=Path("rules/google-gemini.list"),
    #     url="",
    #     reason="Local list in this repo; keep manual control",
    # ),
    # RuleSource(
    #     path=Path("rules/russia_extended.list"),
    #     url="",
    #     reason="Local list in this repo; keep manual control",
    # ),
)

LOCAL_RULES: tuple[Path, ...] = (
    Path("rules/whitelist_direct.list"),
    Path("rules/greylist_proxy.list"),
)


def fetch_text(url: str) -> str:
    request = Request(url, headers={"User-Agent": "ShadowRocketSync/1.0"})
    with urlopen(request, timeout=30) as response:
        content = response.read().decode("utf-8")
    return content


def update_file(source: RuleSource, repo_root: Path) -> bool:
    target_path = repo_root / source.path
    target_path.parent.mkdir(parents=True, exist_ok=True)
    new_content = fetch_text(source.url)
    if target_path.exists():
        current_content = target_path.read_text(encoding="utf-8")
        if current_content == new_content:
            print(f"No changes for {source.path}")
            return False
    target_path.write_text(new_content, encoding="utf-8")
    print(f"Updated {source.path} ({source.reason})")
    return True


def sync_sources(sources: Iterable[RuleSource]) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    for local_rule in LOCAL_RULES:
        print(f"Skipping {local_rule}: local manual list")
    for source in sources:
        if not source.url:
            print(f"Skipping {source.path}: missing URL")
            continue
        update_file(source, repo_root)


def pull_latest(repo_root: Path) -> None:
    if not (repo_root / ".git").exists():
        print("Skipping git pull: repository metadata not found")
        return
    subprocess.run(["git", "-C", str(repo_root), "pull", "--rebase"], check=True)


def main() -> int:
    parser = argparse.ArgumentParser(description="Sync rule lists from upstream repositories.")
    parser.add_argument(
        "--no-pull",
        action="store_true",
        help="Skip git pull --rebase before syncing.",
    )
    args = parser.parse_args()
    repo_root = Path(__file__).resolve().parents[1]
    if not args.no_pull:
        pull_latest(repo_root)
    sync_sources(RULE_SOURCES)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
