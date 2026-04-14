#!/usr/bin/env python3
"""Build private local XKeen 03/04/05 configs from a plain subscription bundle."""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse

REPO_ROOT = Path(__file__).resolve().parent.parent
BLOCKED_TOKENS = ("russia", "belarus", "ukraine")
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.build_clash_config import write_text_if_changed


@dataclass(frozen=True)
class SubscriptionEntry:
    scheme: str
    raw_uri: str
    name: str


def first(query: dict[str, list[str]], key: str, default: str | None = None) -> str | None:
    values = query.get(key)
    if not values:
        return default
    return values[0]


def load_subscription_entries(path: Path) -> list[SubscriptionEntry]:
    entries: list[SubscriptionEntry] = []
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or "://" not in line:
            continue
        parsed = urlparse(line)
        if not parsed.scheme:
            continue
        entries.append(
            SubscriptionEntry(
                scheme=parsed.scheme.lower(),
                raw_uri=line,
                name=unquote(parsed.fragment).strip(),
            )
        )
    return entries


def filter_auto_wl_nodes(entries: list[SubscriptionEntry]) -> list[SubscriptionEntry]:
    selected: list[SubscriptionEntry] = []
    for entry in entries:
        name = entry.name.lower()
        if entry.scheme != "vless":
            continue
        if "wl" not in name:
            continue
        if any(token in name for token in BLOCKED_TOKENS):
            continue
        selected.append(entry)
    return selected


def node_transport(entry: SubscriptionEntry) -> str:
    parsed = urlparse(entry.raw_uri)
    query = parse_qs(parsed.query)
    return first(query, "type", "tcp") or "tcp"


def build_inbounds(*, dest_override: list[str] | None = None) -> dict[str, object]:
    sniff_targets = dest_override or ["http", "tls"]
    return {
        "inbounds": [
            {
                "tag": "redirect",
                "port": 61219,
                "protocol": "dokodemo-door",
                "settings": {"network": "tcp", "followRedirect": True},
                "sniffing": {"enabled": True, "routeOnly": True, "destOverride": sniff_targets},
            },
            {
                "tag": "tproxy",
                "port": 61219,
                "protocol": "dokodemo-door",
                "settings": {"network": "udp", "followRedirect": True},
                "streamSettings": {"sockopt": {"tproxy": "tproxy"}},
                "sniffing": {"enabled": True, "routeOnly": True, "destOverride": sniff_targets},
            },
        ]
    }


def make_outbound_tag(selector_prefix: str, index: int) -> str:
    suffix = selector_prefix[:-1] if selector_prefix.endswith("-") else selector_prefix
    return f"{suffix}-{index:02d}"


def build_stream_settings(query: dict[str, list[str]]) -> dict[str, object]:
    network = first(query, "type", "tcp")
    stream_settings: dict[str, object] = {"network": network}

    security = first(query, "security")
    if security:
        stream_settings["security"] = security

    if network == "xhttp":
        xhttp_settings: dict[str, object] = {}
        path = first(query, "path")
        host = first(query, "host")
        mode = first(query, "mode")
        if path:
            xhttp_settings["path"] = path
        if host:
            xhttp_settings["host"] = host
        if mode:
            xhttp_settings["mode"] = mode
        if xhttp_settings:
            stream_settings["xhttpSettings"] = xhttp_settings

    if security == "reality":
        reality_settings: dict[str, object] = {}
        public_key = first(query, "pbk")
        fingerprint = first(query, "fp")
        server_name = first(query, "sni")
        short_id = first(query, "sid")
        spider_x = first(query, "spx", "/")
        if public_key:
            reality_settings["publicKey"] = public_key
        if fingerprint:
            reality_settings["fingerprint"] = fingerprint
        if server_name:
            reality_settings["serverName"] = server_name
        if short_id:
            reality_settings["shortId"] = short_id
        if spider_x:
            reality_settings["spiderX"] = spider_x
        stream_settings["realitySettings"] = reality_settings
    elif security == "tls":
        tls_settings: dict[str, object] = {}
        server_name = first(query, "sni")
        fingerprint = first(query, "fp")
        if server_name:
            tls_settings["serverName"] = server_name
        if fingerprint:
            tls_settings["fingerprint"] = fingerprint
        if tls_settings:
            stream_settings["tlsSettings"] = tls_settings

    return stream_settings


def parse_vless_outbound(entry: SubscriptionEntry, tag: str) -> dict[str, object]:
    parsed = urlparse(entry.raw_uri)
    query = parse_qs(parsed.query)
    user: dict[str, object] = {
        "id": parsed.username or "",
        "encryption": first(query, "encryption", "none"),
        "level": 0,
    }
    flow = first(query, "flow")
    if flow:
        user["flow"] = flow

    return {
        "tag": tag,
        "protocol": "vless",
        "settings": {
            "vnext": [
                {
                    "address": parsed.hostname,
                    "port": parsed.port or 443,
                    "users": [user],
                }
            ]
        },
        "streamSettings": build_stream_settings(query),
    }


def build_outbounds(entries: list[SubscriptionEntry], selector_prefix: str) -> dict[str, object]:
    proxies = [
        parse_vless_outbound(entry, make_outbound_tag(selector_prefix, index))
        for index, entry in enumerate(entries, start=1)
    ]
    return {
        "outbounds": [
            *proxies,
            {"protocol": "freedom", "tag": "direct"},
            {
                "tag": "block",
                "protocol": "blackhole",
                "settings": {"response": {"type": "http"}},
            },
        ]
    }


def build_single_outbounds(entry: SubscriptionEntry, proxy_tag: str) -> dict[str, object]:
    return {
        "outbounds": [
            parse_vless_outbound(entry, proxy_tag),
            {"protocol": "freedom", "tag": "direct"},
            {
                "tag": "block",
                "protocol": "blackhole",
                "settings": {"response": {"type": "http"}},
            },
        ]
    }


def build_diagnostic_outbounds(entry: SubscriptionEntry, proxy_tag: str) -> dict[str, object]:
    return build_single_outbounds(entry, proxy_tag)


def build_flat_ru_direct_rules() -> list[dict[str, object]]:
    return [
        {"type": "field", "domain": ["domain:ru"], "outboundTag": "direct"},
        {"type": "field", "domain": ["domain:xn--p1ai"], "outboundTag": "direct"},
        {"type": "field", "domain": ["domain:su"], "outboundTag": "direct"},
        {"type": "field", "ip": ["geoip:ru"], "outboundTag": "direct"},
    ]


def proxy_route_target(*, proxy_tag: str | None = None, balancer_tag: str | None = None) -> dict[str, object]:
    if balancer_tag is not None:
        return {"balancerTag": balancer_tag}
    if proxy_tag is not None:
        return {"outboundTag": proxy_tag}
    raise ValueError("proxy_tag or balancer_tag must be provided")


def build_community_routing(
    *,
    proxy_tag: str | None = None,
    balancer_tag: str | None = None,
    selector_prefix: str | None = None,
) -> dict[str, object]:
    proxy_target = proxy_route_target(proxy_tag=proxy_tag, balancer_tag=balancer_tag)
    routing: dict[str, object] = {
        "domainStrategy": "IPIfNonMatch",
        "rules": [
            {
                "type": "field",
                "inboundTag": ["redirect", "tproxy"],
                "outboundTag": "block",
                "network": "udp",
                "port": "135,137,138,139",
            },
            {
                "type": "field",
                "inboundTag": ["redirect", "tproxy"],
                "outboundTag": "block",
                "domain": [
                    "ext:geosite_v2fly.dat:category-ads-all",
                    "google-analytics",
                    "analytics.yandex",
                    "appcenter.ms",
                    "app-measurement.com",
                    "firebase.io",
                    "crashlytics.com",
                ],
            },
            {
                "type": "field",
                "inboundTag": ["redirect", "tproxy"],
                "outboundTag": "direct",
                "protocol": ["bittorrent"],
            },
            {
                "type": "field",
                "inboundTag": ["redirect", "tproxy"],
                "outboundTag": "direct",
                "domain": [
                    r"regexp:^([\w\-\.]+\.)ru$",
                    r"regexp:^([\w\-\.]+\.)su$",
                    r"regexp:^([\w\-\.]+\.)xn--p1ai$",
                    r"regexp:^([\w\-\.]+\.)xn--p1acf$",
                    r"regexp:^([\w\-\.]+\.)xn--80asehdb$",
                    r"regexp:^([\w\-\.]+\.)xn--c1avg$",
                    r"regexp:^([\w\-\.]+\.)xn--80aswg$",
                    r"regexp:^([\w\-\.]+\.)xn--80adxhks$",
                    r"regexp:^([\w\-\.]+\.)moscow$",
                    r"regexp:^([\w\-\.]+\.)xn--d1acj3b$",
                    "ext:geosite_v2fly.dat:category-gov-ru",
                    "ext:geosite_v2fly.dat:yandex",
                    "ext:geosite_v2fly.dat:vk",
                    "ext:geosite_v2fly.dat:steam",
                ],
            },
            {
                "type": "field",
                "inboundTag": ["redirect", "tproxy"],
                "outboundTag": "direct",
                "ip": ["ext:geoip_zkeenip.dat:ru"],
            },
            {
                "type": "field",
                "inboundTag": ["redirect", "tproxy"],
                **proxy_target,
                "domain": [
                    "ext:geosite_zkeen.dat:domains",
                    "ext:geosite_zkeen.dat:other",
                    "ext:geosite_zkeen.dat:youtube",
                ],
            },
            {
                "type": "field",
                "inboundTag": ["redirect", "tproxy"],
                **proxy_target,
                "network": "tcp,udp",
            },
        ],
    }
    if balancer_tag is not None and selector_prefix is not None:
        routing["balancers"] = [
            {
                "tag": balancer_tag,
                "selector": [selector_prefix],
                "strategy": {"type": "roundRobin"},
            }
        ]
    return {"routing": routing}


def build_diagnostic_routing(*, proxy_tag: str) -> dict[str, object]:
    return build_community_routing(proxy_tag=proxy_tag)


def build_private_routing(
    *,
    balancer_tag: str,
    selector_prefix: str,
) -> dict[str, object]:
    return build_community_routing(balancer_tag=balancer_tag, selector_prefix=selector_prefix)


def build_single_routing(*, proxy_tag: str) -> dict[str, object]:
    return build_community_routing(proxy_tag=proxy_tag)


def human_node_label(entry: SubscriptionEntry) -> str:
    label = entry.name
    if label and ord(label[0]) > 0x1F1E5:
        parts = label.split(" ", 1)
        if len(parts) == 2:
            label = parts[1]
    for token in (" WL", " Mobile", " Vless"):
        label = label.replace(token, "")
    return " ".join(label.split()).strip()


def slugify_node_label(label: str) -> str:
    label = label.lower().replace("(", "-").replace(")", "")
    label = re.sub(r"[^a-z0-9]+", "-", label)
    return label.strip("-")


def build_diagnostic_germany_y_profile(
    *,
    entries: list[SubscriptionEntry],
    diagnostics_dir: Path,
    proxy_tag: str = "xkeen-single",
) -> int:
    target_entry = next(
        (entry for entry in entries if slugify_node_label(human_node_label(entry)) == "germany-y"),
        None,
    )
    if target_entry is None:
        return 0

    profile_dir = diagnostics_dir / "germany-y-split"
    profile_dir.mkdir(parents=True, exist_ok=True)
    dns_path = profile_dir / "02_dns.json"
    if dns_path.exists():
        dns_path.unlink()
    write_json(profile_dir / "03_inbounds.json", build_inbounds())
    write_json(profile_dir / "04_outbounds.json", build_diagnostic_outbounds(target_entry, proxy_tag))
    write_json(profile_dir / "05_routing.json", build_diagnostic_routing(proxy_tag=proxy_tag))
    return 1


def write_single_profiles(
    *,
    entries: list[SubscriptionEntry],
    singles_dir: Path,
    proxy_tag: str = "xkeen-single",
) -> int:
    singles_dir.mkdir(parents=True, exist_ok=True)
    inbounds = build_inbounds()
    created = 0

    for entry in entries:
        slug = slugify_node_label(human_node_label(entry))
        profile_dir = singles_dir / slug
        profile_dir.mkdir(parents=True, exist_ok=True)
        write_json(profile_dir / "03_inbounds.json", inbounds)
        write_json(profile_dir / "04_outbounds.json", build_single_outbounds(entry, proxy_tag))
        write_json(profile_dir / "05_routing.json", build_single_routing(proxy_tag=proxy_tag))
        created += 1

    return created


def write_json(path: Path, payload: dict[str, object]) -> None:
    write_text_if_changed(path, json.dumps(payload, ensure_ascii=False, indent=2) + "\n")


def build_local_outputs(
    *,
    subscription_path: Path,
    output_dir: Path,
    balancer_tag: str = "xkeen-auto-wl",
    selector_prefix: str = "xkeen-wl-",
    singles_dir: Path | None = None,
    diagnostics_dir: Path | None = None,
) -> dict[str, int]:
    entries = load_subscription_entries(subscription_path)
    filtered_entries = [entry for entry in filter_auto_wl_nodes(entries) if node_transport(entry) == "tcp"]

    output_dir.mkdir(parents=True, exist_ok=True)
    write_json(output_dir / "03_inbounds.json", build_inbounds())
    write_json(output_dir / "04_outbounds.json", build_outbounds(filtered_entries, selector_prefix))
    write_json(
        output_dir / "05_routing.json",
        build_private_routing(
            balancer_tag=balancer_tag,
            selector_prefix=selector_prefix,
        ),
    )
    singles_output = singles_dir if singles_dir is not None else output_dir.parent / "singles"
    single_profiles = write_single_profiles(entries=filtered_entries, singles_dir=singles_output)
    diagnostics_output = diagnostics_dir if diagnostics_dir is not None else output_dir.parent / "diagnostics"
    diagnostic_profiles = build_diagnostic_germany_y_profile(
        entries=filtered_entries,
        diagnostics_dir=diagnostics_output,
    )

    return {
        "loaded_entries": len(entries),
        "selected_entries": len(filtered_entries),
        "single_profiles": single_profiles,
        "diagnostic_profiles": diagnostic_profiles,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build private local XKeen 03/04/05 configs from XKeen/sub/sub.txt."
    )
    parser.add_argument(
        "--subscription",
        type=Path,
        default=REPO_ROOT / "XKeen/sub/sub.txt",
        help="Path to a plain text subscription bundle with one URI per line.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=REPO_ROOT / "XKeen/local",
        help="Directory for local private XKeen outputs.",
    )
    parser.add_argument(
        "--balancer-tag",
        default="xkeen-auto-wl",
        help='Balancer tag for proxied traffic in local private routing (default: "xkeen-auto-wl").',
    )
    parser.add_argument(
        "--selector-prefix",
        default="xkeen-wl-",
        help='Shared prefix for generated local outbound tags (default: "xkeen-wl-").',
    )
    parser.add_argument(
        "--singles-dir",
        type=Path,
        default=REPO_ROOT / "XKeen/singles",
        help="Directory for one-node XKeen profile folders.",
    )
    parser.add_argument(
        "--diagnostics-dir",
        type=Path,
        default=REPO_ROOT / "XKeen/diagnostics",
        help="Directory for diagnostic XKeen profile folders.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    summary = build_local_outputs(
        subscription_path=args.subscription.resolve(),
        output_dir=args.output_dir.resolve(),
        balancer_tag=args.balancer_tag,
        selector_prefix=args.selector_prefix,
        singles_dir=args.singles_dir.resolve(),
        diagnostics_dir=args.diagnostics_dir.resolve(),
    )
    print(f"Loaded {summary['loaded_entries']} subscription entries from {args.subscription}")
    print(f"Selected {summary['selected_entries']} AUTO-WL VLESS nodes")
    print(f"Generated {args.output_dir / '03_inbounds.json'}")
    print(f"Generated {args.output_dir / '04_outbounds.json'}")
    print(f"Generated {args.output_dir / '05_routing.json'}")
    print(f"Generated {summary['single_profiles']} single-node profiles in {args.singles_dir}")
    print(f"Generated {summary['diagnostic_profiles']} diagnostic profiles in {args.diagnostics_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
