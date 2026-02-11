#!/usr/bin/env python3
"""Sync rule lists from upstream repositories."""

from __future__ import annotations

import argparse
import subprocess
from datetime import datetime, timezone
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


GOOGLE_BUNDLE_URLS: tuple[str, ...] = (
    "https://raw.githubusercontent.com/blackmatrix7/ios_rule_script/master/rule/Shadowrocket/Gemini/Gemini.list",
    "https://raw.githubusercontent.com/blackmatrix7/ios_rule_script/master/rule/Shadowrocket/Google/Google.list",
    "https://raw.githubusercontent.com/blackmatrix7/ios_rule_script/master/rule/Shadowrocket/GoogleDrive/GoogleDrive.list",
    "https://raw.githubusercontent.com/blackmatrix7/ios_rule_script/master/rule/Shadowrocket/GoogleEarth/GoogleEarth.list",
    "https://raw.githubusercontent.com/blackmatrix7/ios_rule_script/master/rule/Shadowrocket/GoogleFCM/GoogleFCM.list",
    "https://raw.githubusercontent.com/blackmatrix7/ios_rule_script/master/rule/Shadowrocket/GoogleSearch/GoogleSearch.list",
    "https://raw.githubusercontent.com/blackmatrix7/ios_rule_script/master/rule/Shadowrocket/GoogleVoice/GoogleVoice.list",
    "https://raw.githubusercontent.com/blackmatrix7/ios_rule_script/master/rule/Shadowrocket/YouTube/YouTube.list",
    "https://raw.githubusercontent.com/blackmatrix7/ios_rule_script/master/rule/Shadowrocket/YouTube/YouTube_Resolve.list",
    "https://raw.githubusercontent.com/blackmatrix7/ios_rule_script/master/rule/Shadowrocket/YouTubeMusic/YouTubeMusic.list",
)


def filter_shadowrocket_rules(raw_text: str) -> list[str]:
    rules: list[str] = []
    for line in raw_text.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith(("#", "!", ";", "[")):
            continue
        rules.append(stripped)
    return rules


def compress_google_rules(rules: Iterable[str]) -> list[str]:
    keyword_values = {
        line.split(",", 1)[1]
        for line in rules
        if line.startswith("DOMAIN-KEYWORD,") and "," in line
    }
    has_google_keyword = "google" in keyword_values

    compressed: list[str] = []
    for line in rules:
        if (
            has_google_keyword
            and line.startswith("DOMAIN-KEYWORD,")
            and "," in line
        ):
            keyword = line.split(",", 1)[1]
            if keyword != "google" and "google" in keyword:
                continue

        if (
            has_google_keyword
            and line.startswith("DOMAIN,")
            and "," in line
        ):
            domain = line.split(",", 1)[1]
            if domain == "google.com" or domain.endswith(".google.com"):
                continue

        compressed.append(line)
    return compressed


def update_google_bundle(repo_root: Path) -> bool:
    output_path = repo_root / "rules/google-all.list"
    combined: list[str] = []
    for url in GOOGLE_BUNDLE_URLS:
        combined.extend(filter_shadowrocket_rules(fetch_text(url)))
    unique_rules = sorted(set(compress_google_rules(combined)))
    header = [
        "# Total Google & Gemini Bundle",
        f"# Updated: {datetime.now(timezone.utc).isoformat()}",
    ]
    new_content = "\n".join(header + unique_rules) + "\n"
    if output_path.exists():
        current_content = output_path.read_text(encoding="utf-8")
        if current_content == new_content:
            print("No changes for rules/google-all.list")
            return False
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(new_content, encoding="utf-8")
    print("Updated rules/google-all.list (Google/Gemini bundle)")
    return True


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
    update_google_bundle(repo_root)
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
