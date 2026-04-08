#!/usr/bin/env python3
"""Build Clash Verge Rev (Mihomo) config from Shadowrocket routing truth."""

from __future__ import annotations

import argparse
import re
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import urlparse


REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_OUTPUT = REPO_ROOT / "clash_config.yaml"
DEFAULT_CONF = REPO_ROOT / "shadowrocket.conf"
DEFAULT_SUBSCRIPTION_URL = "<INSERT_SUBSCRIPTION_URL_HERE>"
DEFAULT_PROVIDER_FILTER = r"(?i)(Vless|Netherlands\s+WL\s+Mobile)"
DEFAULT_PROVIDER_EXCLUDE_FILTER = r"(?i)(Russia|Belarus|Ukraine)"
DEFAULT_HEALTHCHECK_URL = "https://abs.twimg.com/favicon.ico"
DEFAULT_HEALTHCHECK_INTERVAL = 780
RULE_PROVIDER_INTERVAL = 86400
FAKE_IP_FILTER = [
    "+.lan",
    "+.local",
    "+.localhost",
    "+.home.arpa",
    "*.localdomain",
    "time.*.com",
    "time.*.gov",
    "time.*.edu",
    "time.windows.com",
    "time.apple.com",
    "time.android.com",
    "*.ntp.org",
]
SUPPORTED_INLINE_RULES = {"DOMAIN", "DOMAIN-SUFFIX", "DOMAIN-KEYWORD", "IP-CIDR", "IP-CIDR6", "GEOIP", "FINAL"}


@dataclass
class GroupSpec:
    name: str
    group_type: str
    members: list[str] = field(default_factory=list)
    attrs: dict[str, str] = field(default_factory=dict)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build clash_config.yaml from shadowrocket.conf")
    parser.add_argument("--conf", type=Path, default=DEFAULT_CONF, help="Path to base shadowrocket.conf")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT, help="Path to generated clash_config.yaml")
    parser.add_argument(
        "--subscription-url",
        default=DEFAULT_SUBSCRIPTION_URL,
        help="Placeholder subscription URL written into proxy-providers.Main-Sub.url",
    )
    return parser.parse_args()


def write_text_if_changed(path: Path, content: str) -> None:
    if path.exists() and path.read_text(encoding="utf-8") == content:
        return
    path.write_text(content, encoding="utf-8")


def parse_section_lines(conf_path: Path, section_name: str) -> list[str]:
    header = f"[{section_name}]"
    lines: list[str] = []
    in_section = False
    for raw_line in conf_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip().replace("\ufeff", "")
        if line == header:
            in_section = True
            continue
        if in_section and line.startswith("["):
            break
        if not in_section or not line or line.startswith("#"):
            continue
        lines.append(line)
    return lines


def parse_general(conf_path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    for line in parse_section_lines(conf_path, "General"):
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip()
    return values


def parse_proxy_groups(conf_path: Path) -> list[GroupSpec]:
    groups: list[GroupSpec] = []
    for line in parse_section_lines(conf_path, "Proxy Group"):
        if "=" not in line:
            continue
        name, rhs = line.split("=", 1)
        parts = [part.strip() for part in rhs.split(",") if part.strip()]
        if not parts:
            continue

        group_type = parts[0]
        members: list[str] = []
        attrs: dict[str, str] = {}
        for item in parts[1:]:
            if "=" in item:
                key, value = item.split("=", 1)
                attrs[key.strip()] = value.strip()
            else:
                members.append(item)
        groups.append(GroupSpec(name=name.strip(), group_type=group_type.strip(), members=members, attrs=attrs))
    return groups


def parse_rule_lines(conf_path: Path) -> list[str]:
    return parse_section_lines(conf_path, "Rule")


def normalize_domain(value: str) -> str:
    labels = [label for label in value.strip().rstrip(".").split(".") if label]
    return ".".join(label.encode("idna").decode("ascii") for label in labels)


def provider_name_from_url(rule_set_url: str) -> str:
    parsed = urlparse(rule_set_url)
    name = Path(parsed.path).stem
    if not name:
        raise ValueError(f"Cannot derive provider name from {rule_set_url}")
    return re.sub(r"[^0-9A-Za-z_]+", "_", name.replace("-", "_"))


def yaml_quote(value: str) -> str:
    escaped = value.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


def parse_csv(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


def parse_bool(value: str, default: bool) -> bool:
    normalized = value.strip().lower()
    if normalized in {"true", "yes", "1"}:
        return True
    if normalized in {"false", "no", "0"}:
        return False
    return default


def derive_healthcheck_url(groups: list[GroupSpec]) -> str:
    for group in groups:
        if group.group_type == "url-test":
            url = group.attrs.get("url")
            if url:
                return url
    return DEFAULT_HEALTHCHECK_URL


def render_rule_providers(rule_lines: list[str]) -> tuple[list[str], list[str]]:
    warnings: list[str] = []
    rendered: list[str] = []
    seen: set[str] = set()

    for line in rule_lines:
        parts = [part.strip() for part in line.split(",")]
        if not parts or parts[0].upper() != "RULE-SET" or len(parts) < 3:
            continue
        url = parts[1]
        provider_name = provider_name_from_url(url)
        if provider_name in seen:
            continue
        seen.add(provider_name)
        rendered.extend(
            [
                f"  {provider_name}:",
                "    type: http",
                "    behavior: classical",
                f"    url: {yaml_quote(url)}",
                f"    path: ./rules/{provider_name}.yaml",
                f"    interval: {RULE_PROVIDER_INTERVAL}",
                "",
            ]
        )
        if len(parts) > 3:
            warnings.append(f"RULE-SET modifiers dropped for Clash provider {provider_name}: {', '.join(parts[3:])}")

    if rendered and rendered[-1] == "":
        rendered.pop()
    return rendered, warnings


def render_proxy_groups(groups: list[GroupSpec]) -> tuple[list[str], list[str]]:
    warnings: list[str] = []
    rendered: list[str] = ["proxy-groups:"]

    for group in groups:
        rendered.extend(
            [
                f"  - name: {group.name}",
                f"    type: {group.group_type}",
            ]
        )

        regex_filter = group.attrs.get("policy-regex-filter")
        if regex_filter:
            rendered.extend(["    use:", "      - Main-Sub", f"    filter: {yaml_quote(regex_filter)}"])

        if group.members:
            rendered.append("    proxies:")
            for member in group.members:
                rendered.append(f"      - {member}")

        if group.group_type == "url-test":
            url = group.attrs.get("url", DEFAULT_HEALTHCHECK_URL)
            rendered.append(f"    url: {yaml_quote(url)}")
            if "interval" in group.attrs:
                rendered.append(f"    interval: {group.attrs['interval']}")
            if "tolerance" in group.attrs:
                rendered.append(f"    tolerance: {group.attrs['tolerance']}")
            if "timeout" in group.attrs:
                warnings.append(f"{group.name}: Clash builder ignores Shadowrocket timeout={group.attrs['timeout']}")

        unsupported_keys = set(group.attrs) - {"policy-regex-filter", "url", "interval", "tolerance", "timeout"}
        if "policy-select-name" in unsupported_keys:
            warnings.append(f"{group.name}: Clash builder ignores policy-select-name={group.attrs['policy-select-name']}")
            unsupported_keys.remove("policy-select-name")
        for key in sorted(unsupported_keys):
            warnings.append(f"{group.name}: unsupported proxy-group option {key}={group.attrs[key]}")

        rendered.append("")

    if rendered and rendered[-1] == "":
        rendered.pop()
    return rendered, warnings


def normalize_rule_target(target: str) -> str:
    return target.strip()


def render_rules(rule_lines: list[str]) -> tuple[list[str], list[str]]:
    warnings: list[str] = []
    rendered = ["rules:"]
    appended_private_geoip = False

    for line in rule_lines:
        parts = [part.strip() for part in line.split(",")]
        if not parts:
            continue
        rule_type = parts[0].upper()

        if rule_type == "RULE-SET" and len(parts) >= 3:
            provider_name = provider_name_from_url(parts[1])
            target = normalize_rule_target(parts[2])
            rendered.append(f"  - RULE-SET,{provider_name},{target}")
            if len(parts) > 3:
                warnings.append(f"Clash rules drop unsupported RULE-SET modifiers for {provider_name}: {', '.join(parts[3:])}")
            continue

        if rule_type == "FINAL" and len(parts) >= 2:
            if not appended_private_geoip:
                rendered.append("  - GEOIP,private,DIRECT")
                appended_private_geoip = True
            rendered.append(f"  - MATCH,{normalize_rule_target(parts[1])}")
            continue

        if rule_type == "DOMAIN" and len(parts) >= 3:
            rendered.append(f"  - DOMAIN,{normalize_domain(parts[1])},{normalize_rule_target(parts[2])}")
            continue

        if rule_type == "DOMAIN-SUFFIX" and len(parts) >= 3:
            rendered.append(f"  - DOMAIN-SUFFIX,{normalize_domain(parts[1])},{normalize_rule_target(parts[2])}")
            continue

        if rule_type == "DOMAIN-KEYWORD" and len(parts) >= 3:
            rendered.append(f"  - DOMAIN-KEYWORD,{parts[1].strip().strip('.')},{normalize_rule_target(parts[2])}")
            continue

        if rule_type in {"IP-CIDR", "IP-CIDR6"} and len(parts) >= 3:
            tail = ",".join(parts[3:]) if len(parts) > 3 else ""
            suffix = f",{tail}" if tail else ""
            rendered.append(f"  - {rule_type},{parts[1]},{normalize_rule_target(parts[2])}{suffix}")
            continue

        if rule_type == "GEOIP" and len(parts) >= 3:
            rendered.append(f"  - GEOIP,{parts[1]},{normalize_rule_target(parts[2])}")
            continue

        if rule_type in SUPPORTED_INLINE_RULES:
            warnings.append(f"Incomplete inline rule skipped for Clash: {line}")
            continue

        warnings.append(f"Unsupported Shadowrocket rule skipped for Clash: {line}")

    if not appended_private_geoip:
        rendered.append("  - GEOIP,private,DIRECT")
    return rendered, warnings


def build_config(conf_path: Path, subscription_url: str) -> tuple[str, list[str]]:
    general = parse_general(conf_path)
    groups = parse_proxy_groups(conf_path)
    rule_lines = parse_rule_lines(conf_path)
    warnings: list[str] = []

    dns_servers = parse_csv(general.get("dns-server", "77.88.8.8,8.8.8.8"))
    fallback_dns = parse_csv(general.get("fallback-dns-server", "tls://77.88.8.8,tls://8.8.8.8"))
    ipv6_enabled = parse_bool(general.get("ipv6", "false"), default=False)
    healthcheck_url = derive_healthcheck_url(groups)
    rule_providers_block, provider_warnings = render_rule_providers(rule_lines)
    proxy_groups_block, group_warnings = render_proxy_groups(groups)
    rules_block, rule_warnings = render_rules(rule_lines)
    warnings.extend(provider_warnings)
    warnings.extend(group_warnings)
    warnings.extend(rule_warnings)

    lines = [
        "# CLASH VERGE REV (MIHOMO) CONFIG",
        "# AUTO-GENERATED FROM shadowrocket.conf",
        "# Derived routing truth: proxy groups, rule-providers, rules",
        "",
        "port: 7890",
        "socks-port: 7891",
        "allow-lan: false",
        "mode: rule",
        "log-level: info",
        f"ipv6: {'true' if ipv6_enabled else 'false'}",
        "geoip-code: RU",
        "",
        "# 1. TUN MODE",
        "tun:",
        "  enable: true",
        "  stack: system",
        "  dns-hijack:",
        "    - any:53",
        "  auto-route: true",
        "  auto-detect-interface: true",
        "",
        "# 2. DNS (Fake-IP)",
        "dns:",
        "  enable: true",
        "  listen: 0.0.0.0:1053",
        f"  ipv6: {'true' if ipv6_enabled else 'false'}",
        "  enhanced-mode: fake-ip",
        "  fake-ip-range: 198.18.0.1/16",
        "  fake-ip-filter:",
    ]
    lines.extend(f"    - {yaml_quote(item)}" for item in FAKE_IP_FILTER)
    lines.extend(
        [
            "  default-nameserver:",
            *(f"    - {server}" for server in dns_servers),
            "  nameserver:",
            *(f"    - {server}" for server in dns_servers),
            "  fallback:",
            *(f"    - {server}" for server in fallback_dns),
            "  fallback-filter:",
            "    geoip: false",
            "    ipcidr:",
            "      - 0.0.0.0/0",
            "",
            "# 3. PROVIDERS",
            "proxy-providers:",
            "  Main-Sub:",
            "    type: http",
            f"    url: {yaml_quote(subscription_url)}",
            "    interval: 3600",
            "    path: ./proxies/main.yaml",
            f"    filter: {yaml_quote(DEFAULT_PROVIDER_FILTER)}",
            f"    exclude-filter: {yaml_quote(DEFAULT_PROVIDER_EXCLUDE_FILTER)}",
            "    health-check:",
            "      enable: true",
            f"      interval: {DEFAULT_HEALTHCHECK_INTERVAL}",
            f"      url: {yaml_quote(healthcheck_url)}",
            "",
            "# 4. RULE PROVIDERS",
            "rule-providers:",
        ]
    )
    lines.extend(rule_providers_block)
    lines.extend(["", "# 5. PROXY GROUPS"])
    lines.extend(proxy_groups_block)
    lines.extend(["", "# 6. RULES"])
    lines.extend(rules_block)
    return "\n".join(lines) + "\n", warnings


def main() -> int:
    args = parse_args()
    conf_path = args.conf.resolve()
    output_path = args.output.resolve()
    if not conf_path.exists():
        raise FileNotFoundError(f"Config not found: {conf_path}")

    content, warnings = build_config(conf_path, args.subscription_url)
    write_text_if_changed(output_path, content)

    if warnings:
        print("Clash generation warnings:")
        for warning in warnings:
            print(f"  - {warning}")
    else:
        print("Generated clash_config.yaml without dropped mappings.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
