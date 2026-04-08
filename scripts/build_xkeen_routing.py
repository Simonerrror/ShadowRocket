#!/usr/bin/env python3
"""Build XKeen/Xray routing config from Shadowrocket routing rules."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from urllib.parse import urlparse


REPO_ROOT = Path(__file__).resolve().parent.parent
SUPPORTED_DOMAIN_RULES = {"DOMAIN", "DOMAIN-SUFFIX", "DOMAIN-KEYWORD"}
SUPPORTED_IP_RULES = {"IP-CIDR", "IP-CIDR6"}
SKIPPED_POLICY_NAMES = {"REJECT", "REJECT-DROP", "REJECT-TINYGIF"}


def dedupe(items: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for item in items:
        if item in seen:
            continue
        seen.add(item)
        result.append(item)
    return result


def write_text_if_changed(path: Path, content: str) -> None:
    if path.exists() and path.read_text(encoding="utf-8") == content:
        return
    path.write_text(content, encoding="utf-8")


def normalize_domain(value: str) -> str:
    labels = [label for label in value.strip().rstrip(".").split(".") if label]
    return ".".join(label.encode("idna").decode("ascii") for label in labels)


def normalize_keyword(value: str) -> str:
    return value.strip().strip(".")


def parse_rule_list(path: Path) -> tuple[list[str], list[str], list[str]]:
    domains: list[str] = []
    ips: list[str] = []
    unsupported: list[str] = []

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip().replace("\ufeff", "")
        if not line or line.startswith("#"):
            continue

        parts = [part.strip() for part in line.split(",")]
        rule_type = parts[0].upper()

        if rule_type == "DOMAIN" and len(parts) >= 2:
            domains.append(f"full:{normalize_domain(parts[1])}")
        elif rule_type == "DOMAIN-SUFFIX" and len(parts) >= 2:
            domains.append(f"domain:{normalize_domain(parts[1])}")
        elif rule_type == "DOMAIN-KEYWORD" and len(parts) >= 2:
            domains.append(f"keyword:{normalize_keyword(parts[1])}")
        elif rule_type in SUPPORTED_IP_RULES and len(parts) >= 2:
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


def parse_shadowrocket_rule_lines(conf_path: Path) -> list[str]:
    lines: list[str] = []
    in_rule_section = False

    for raw_line in conf_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip().replace("\ufeff", "")
        if line == "[Rule]":
            in_rule_section = True
            continue
        if in_rule_section and line.startswith("["):
            break
        if not in_rule_section or not line or line.startswith("#"):
            continue
        lines.append(line)

    return lines


def local_rule_list_path(value: str) -> Path:
    if "://" in value:
        parsed = urlparse(value)
        name = Path(parsed.path).name
        if not name:
            raise ValueError(f"Unsupported rule-set URL: {value}")
        return REPO_ROOT / "rules" / name
    raw_path = Path(value)
    if raw_path.is_absolute():
        return raw_path
    return REPO_ROOT / raw_path


def outbound_for_policy(policy_name: str, proxy_tag: str) -> str | None:
    upper = policy_name.strip().upper()
    if upper == "DIRECT":
        return "direct"
    if upper in SKIPPED_POLICY_NAMES:
        return None
    return proxy_tag


def inline_domain_token(rule_type: str, value: str) -> str:
    if rule_type == "DOMAIN":
        return f"full:{normalize_domain(value)}"
    if rule_type == "DOMAIN-SUFFIX":
        return f"domain:{normalize_domain(value)}"
    if rule_type == "DOMAIN-KEYWORD":
        return f"keyword:{normalize_keyword(value)}"
    raise ValueError(f"Unsupported inline domain rule: {rule_type}")


def build_config(conf_path: Path, proxy_tag: str) -> tuple[dict[str, object], dict[str, list[str]]]:
    config = {"domainStrategy": "IPIfNonMatch", "rules": []}
    unsupported: dict[str, list[str]] = {}

    for line in parse_shadowrocket_rule_lines(conf_path):
        parts = [part.strip() for part in line.split(",")]
        rule_type = parts[0].upper()

        if rule_type == "RULE-SET" and len(parts) >= 3:
            outbound_tag = outbound_for_policy(parts[2], proxy_tag)
            if outbound_tag is None:
                unsupported.setdefault("shadowrocket.inline", []).append(line)
                continue

            rule_path = local_rule_list_path(parts[1])
            domains, ips, list_unsupported = parse_rule_list(rule_path)
            if domains or ips:
                config["rules"].append(make_rule(outbound_tag=outbound_tag, domains=domains, ips=ips))
            if list_unsupported:
                unsupported[rule_path.name] = list_unsupported
            continue

        if rule_type in SUPPORTED_DOMAIN_RULES and len(parts) >= 3:
            outbound_tag = outbound_for_policy(parts[2], proxy_tag)
            if outbound_tag is None:
                unsupported.setdefault("shadowrocket.inline", []).append(line)
                continue
            config["rules"].append(
                make_rule(outbound_tag=outbound_tag, domains=[inline_domain_token(rule_type, parts[1])])
            )
            continue

        if rule_type in SUPPORTED_IP_RULES and len(parts) >= 3:
            outbound_tag = outbound_for_policy(parts[2], proxy_tag)
            if outbound_tag is None:
                unsupported.setdefault("shadowrocket.inline", []).append(line)
                continue
            config["rules"].append(make_rule(outbound_tag=outbound_tag, ips=[parts[1]]))
            continue

        if rule_type == "GEOIP" and len(parts) >= 3:
            outbound_tag = outbound_for_policy(parts[2], proxy_tag)
            if outbound_tag is None:
                unsupported.setdefault("shadowrocket.inline", []).append(line)
                continue
            config["rules"].append(make_rule(outbound_tag=outbound_tag, ips=[f"geoip:{parts[1].lower()}"]))
            continue

        if rule_type == "FINAL" and len(parts) >= 2:
            outbound_tag = outbound_for_policy(parts[1], proxy_tag)
            if outbound_tag is None:
                unsupported.setdefault("shadowrocket.inline", []).append(line)
                continue
            config["rules"].append(make_rule(outbound_tag=outbound_tag, network="tcp,udp"))
            continue

        unsupported.setdefault("shadowrocket.inline", []).append(line)

    return config, unsupported


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Build XKeen/Xray 05_routing.json from Shadowrocket [Rule] order."
    )
    parser.add_argument(
        "--conf",
        type=Path,
        default=REPO_ROOT / "shadowrocket.conf",
        help="Path to the base Shadowrocket config used as routing truth.",
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

    config, unsupported = build_config(args.conf.resolve(), args.proxy_tag)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    write_text_if_changed(
        args.output,
        json.dumps(config, ensure_ascii=False, indent=2) + "\n",
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
