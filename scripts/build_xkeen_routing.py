#!/usr/bin/env python3
"""Build XKeen/Xray routing config from repository rule lists."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent


def dedupe(items: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for item in items:
        if item not in seen:
            seen.add(item)
            result.append(item)
    return result


def parse_rule_list(path: Path) -> tuple[list[str], list[str], list[str]]:
    domains: list[str] = []
    ips: list[str] = []
    unsupported: list[str] = []

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip().replace("\ufeff", "")
        if not line or line.startswith("#"):
            continue

        parts = [part.strip() for part in line.split(",")]
        rule_type = parts[0]

        if rule_type == "DOMAIN" and len(parts) >= 2:
            domains.append(f"full:{parts[1]}")
        elif rule_type == "DOMAIN-SUFFIX" and len(parts) >= 2:
            domains.append(f"domain:{parts[1]}")
        elif rule_type == "DOMAIN-KEYWORD" and len(parts) >= 2:
            domains.append(f"keyword:{parts[1]}")
        elif rule_type in {"IP-CIDR", "IP-CIDR6"} and len(parts) >= 2:
            ips.append(parts[1])
        else:
            unsupported.append(line)

    return dedupe(domains), dedupe(ips), unsupported


def make_rule(
    *,
    outbound_tag: str,
    domains: list[str] | None = None,
    ips: list[str] | None = None,
    network: str | None = None,
) -> dict[str, object]:
    rule: dict[str, object] = {"type": "field", "outboundTag": outbound_tag}
    if domains:
        rule["domain"] = domains
    if ips:
        rule["ip"] = ips
    if network:
        rule["network"] = network
    return rule


def build_config(proxy_tag: str) -> tuple[dict[str, object], dict[str, list[str]]]:
    whitelist_domains, whitelist_ips, whitelist_unsupported = parse_rule_list(
        REPO_ROOT / "rules/whitelist_direct.list"
    )
    google_domains, google_ips, google_unsupported = parse_rule_list(
        REPO_ROOT / "rules/google-all.list"
    )
    microsoft_domains, microsoft_ips, microsoft_unsupported = parse_rule_list(
        REPO_ROOT / "rules/microsoft.list"
    )
    community_domains, community_ips, community_unsupported = parse_rule_list(
        REPO_ROOT / "rules/domains_community.list"
    )

    config = {
        "domainStrategy": "IPIfNonMatch",
        "rules": [
            make_rule(
                outbound_tag="direct",
                domains=whitelist_domains,
                ips=whitelist_ips,
            ),
            make_rule(
                outbound_tag=proxy_tag,
                domains=google_domains,
                ips=google_ips,
            ),
            make_rule(
                outbound_tag=proxy_tag,
                domains=microsoft_domains,
                ips=microsoft_ips,
            ),
            make_rule(
                outbound_tag=proxy_tag,
                domains=community_domains,
                ips=community_ips,
            ),
            make_rule(
                outbound_tag="direct",
                domains=["domain:ru", "domain:xn--p1ai", "domain:su"],
            ),
            make_rule(
                outbound_tag="direct",
                ips=["geoip:ru"],
            ),
            make_rule(
                outbound_tag=proxy_tag,
                network="tcp,udp",
            ),
        ],
    }

    unsupported = {
        "whitelist_direct": whitelist_unsupported,
        "google_all": google_unsupported,
        "microsoft": microsoft_unsupported,
        "domains_community": community_unsupported,
    }

    return config, unsupported


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Build XKeen/Xray 05_routing.json from repo rule lists."
    )
    parser.add_argument(
        "--proxy-tag",
        default="vless-reality",
        help='Outbound tag used for proxied traffic (default: "vless-reality").',
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=REPO_ROOT / "XKeen/05_routing.json",
        help="Path to generated JSON file.",
    )
    args = parser.parse_args()

    config, unsupported = build_config(args.proxy_tag)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(config, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    unsupported_total = 0
    for name, items in unsupported.items():
        if not items:
            continue
        unsupported_total += len(items)
        print(f"{name}: skipped {len(items)} unsupported entries")
        for item in items[:10]:
            print(f"  - {item}")
        if len(items) > 10:
            print(f"  ... and {len(items) - 10} more")

    if unsupported_total == 0:
        print(f"Generated {args.output}")
    else:
        print(f"Generated {args.output} with {unsupported_total} skipped entries")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
