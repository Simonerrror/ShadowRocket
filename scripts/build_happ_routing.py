#!/usr/bin/env python3
"""Build HAPP routing artifacts from shadowrocket.conf and local rule lists."""

from __future__ import annotations

import argparse
import base64
import ipaddress
import json
import subprocess
import sys
import tempfile
import time
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable
from urllib.parse import urlparse


SUPPORTED_SITE_RULES = {"DOMAIN-SUFFIX", "DOMAIN", "DOMAIN-KEYWORD"}
SUPPORTED_IP_RULES = {"IP-CIDR", "IP-CIDR6", "GEOIP"}
HAPP_EXCLUDED_RULESETS = {"google-all.list", "microsoft.list", "voice_ports.list"}
HAPP_GEOIP_WANTED_LIST = ["ru", "private", "sr-direct", "sr-proxy"]


@dataclass
class Bucket:
    site_rules: list[str] = field(default_factory=list)
    cidrs: list[str] = field(default_factory=list)
    geo_tags: list[str] = field(default_factory=list)


@dataclass
class BuildData:
    direct: Bucket = field(default_factory=Bucket)
    proxy: Bucket = field(default_factory=Bucket)
    block: Bucket = field(default_factory=Bucket)
    dropped: dict[str, list[str]] = field(default_factory=lambda: defaultdict(list))
    converted_lines: int = 0
    processed_conf_rules: int = 0
    processed_ruleset_lines: int = 0

    def bucket(self, action: str) -> Bucket:
        if action == "direct":
            return self.direct
        if action == "proxy":
            return self.proxy
        return self.block

    def drop(self, reason: str, line: str) -> None:
        self.dropped[reason].append(line)


@dataclass
class DnsResolution:
    remote_ip: str
    domestic_ip: str
    notes: list[str] = field(default_factory=list)


def run(cmd: list[str], cwd: Path | None = None) -> str:
    result = subprocess.run(
        cmd,
        cwd=str(cwd) if cwd else None,
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    return result.stdout.strip()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build HAPP routing artifacts.")
    parser.add_argument("--conf", default="shadowrocket.conf", help="Path to shadowrocket.conf")
    parser.add_argument("--rules-dir", default="rules", help="Directory containing *.list files")
    parser.add_argument("--out-dir", default="HAPP", help="Output directory")
    parser.add_argument(
        "--deeplink-mode",
        default="onadd",
        choices=["onadd", "add"],
        help="HAPP deeplink mode",
    )
    parser.add_argument(
        "--route-order",
        default="proxy-direct-block",
        choices=[
            "block-proxy-direct",
            "block-direct-proxy",
            "proxy-direct-block",
            "proxy-block-direct",
            "direct-proxy-block",
            "direct-block-proxy",
        ],
        help="RouteOrder value for HAPP profile",
    )
    parser.add_argument("--remote-dns-ip", default="76.76.2.0", help="Remote DNS IP")
    parser.add_argument("--domestic-dns-ip", default="77.88.8.8", help="Domestic DNS IP")
    parser.add_argument(
        "--remote-dns-type",
        default="DoU",
        choices=["DoH", "DoU"],
        help="Remote DNS type",
    )
    parser.add_argument(
        "--domestic-dns-type",
        default="DoU",
        choices=["DoH", "DoU"],
        help="Domestic DNS type",
    )
    return parser.parse_args()


def extract_general_values(conf_path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    in_general = False
    for raw in conf_path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if line.startswith("[General]"):
            in_general = True
            continue
        if in_general and line.startswith("["):
            break
        if not in_general or not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip()
    return values


def parse_dns_endpoint(value: str) -> str | None:
    candidate = value.strip()
    if not candidate:
        return None
    if "://" in candidate:
        parsed = urlparse(candidate)
        return parsed.hostname
    if candidate.count(":") == 1:
        host, port = candidate.rsplit(":", 1)
        if host and port.isdigit():
            candidate = host
    return candidate or None


def extract_first_dns_endpoint(values: dict[str, str], key: str) -> str | None:
    raw = values.get(key)
    if raw is None:
        return None
    first = raw.split(",", 1)[0].strip()
    if not first:
        return None
    return parse_dns_endpoint(first)


def resolve_happ_dns(conf_path: Path, args: argparse.Namespace) -> DnsResolution:
    values = extract_general_values(conf_path)
    notes: list[str] = []

    if "--remote-dns-ip" in sys.argv:
        remote_ip = args.remote_dns_ip
        notes.append(f"- Remote DNS source: CLI `--remote-dns-ip` -> `{remote_ip}`")
    else:
        remote_ip = extract_first_dns_endpoint(values, "dns-server")
        if remote_ip:
            notes.append(f"- Remote DNS source: `dns-server` -> `{remote_ip}`")
        else:
            remote_ip = args.remote_dns_ip
            raw = values.get("dns-server")
            if raw is None:
                notes.append(f"- Remote DNS source: default `{remote_ip}` (missing `dns-server` in `[General]`)")
            else:
                notes.append(f"- Remote DNS source: default `{remote_ip}` (invalid `dns-server`: `{raw}`)")

    if "--domestic-dns-ip" in sys.argv:
        domestic_ip = args.domestic_dns_ip
        notes.append(f"- Domestic DNS source: CLI `--domestic-dns-ip` -> `{domestic_ip}`")
    else:
        domestic_ip = extract_first_dns_endpoint(values, "fallback-dns-server")
        if domestic_ip:
            notes.append(f"- Domestic DNS source: `fallback-dns-server` -> `{domestic_ip}`")
        else:
            domestic_ip = args.domestic_dns_ip
            raw = values.get("fallback-dns-server")
            if raw is None:
                notes.append(f"- Domestic DNS source: default `{domestic_ip}` (missing `fallback-dns-server` in `[General]`)")
            else:
                notes.append(f"- Domestic DNS source: default `{domestic_ip}` (invalid `fallback-dns-server`: `{raw}`)")

    return DnsResolution(remote_ip=remote_ip, domestic_ip=domestic_ip, notes=notes)


def iter_rule_section(conf_path: Path) -> Iterable[tuple[int, str]]:
    in_rule = False
    for idx, raw in enumerate(conf_path.read_text(encoding="utf-8").splitlines(), start=1):
        line = raw.strip()
        if line.startswith("[Rule]"):
            in_rule = True
            continue
        if in_rule and line.startswith("["):
            break
        if not in_rule or not line or line.startswith("#"):
            continue
        yield idx, line


def parse_action(raw_action: str) -> str | None:
    action = raw_action.upper()
    if action == "DIRECT":
        return "direct"
    if action in {"PROXY", "GOOGLE"}:
        return "proxy"
    if action.startswith("REJECT"):
        return "block"
    return None


def normalize_domain(value: str) -> str:
    value = value.strip().rstrip(".")
    if not value:
        return value
    labels = value.split(".")
    encoded: list[str] = []
    for label in labels:
        if not label:
            continue
        encoded.append(label.encode("idna").decode("ascii"))
    return ".".join(encoded)


def normalize_cidr(value: str) -> str:
    value = value.strip()
    network = ipaddress.ip_network(value, strict=False)
    return str(network)


def convert_rule_line(
    line: str,
    action: str,
    data: BuildData,
    source: str,
) -> None:
    parts = [part.strip() for part in line.split(",")]
    if not parts:
        return
    rule_type = parts[0].upper()
    bucket = data.bucket(action)

    if rule_type in SUPPORTED_SITE_RULES:
        if len(parts) < 2 or not parts[1]:
            data.drop("invalid_site_rule", f"{source}: {line}")
            return
        raw_value = parts[1]
        if rule_type == "DOMAIN-SUFFIX":
            bucket.site_rules.append(f"domain:{normalize_domain(raw_value)}")
        elif rule_type == "DOMAIN":
            bucket.site_rules.append(f"full:{normalize_domain(raw_value)}")
        else:
            bucket.site_rules.append(f"keyword:{raw_value}")
        data.converted_lines += 1
        return

    if rule_type in SUPPORTED_IP_RULES:
        if len(parts) < 2 or not parts[1]:
            data.drop("invalid_ip_rule", f"{source}: {line}")
            return
        raw_value = parts[1]
        if rule_type in {"IP-CIDR", "IP-CIDR6"}:
            try:
                bucket.cidrs.append(normalize_cidr(raw_value))
                data.converted_lines += 1
            except ValueError:
                data.drop("invalid_cidr", f"{source}: {line}")
            return
        bucket.geo_tags.append(f"geoip:{raw_value.lower()}")
        data.converted_lines += 1
        return

    if rule_type == "USER-AGENT":
        data.drop("user_agent", f"{source}: {line}")
        return
    if rule_type == "DST-PORT":
        data.drop("dst_port", f"{source}: {line}")
        return
    if rule_type == "IP-ASN":
        data.drop("ip_asn", f"{source}: {line}")
        return
    if rule_type == "AND":
        data.drop("composite_and", f"{source}: {line}")
        return

    data.drop("unsupported_rule_type", f"{source}: {line}")


def parse_ruleset_url(url: str) -> str:
    path = urlparse(url).path
    return Path(path).name


def parse_conf_and_lists(conf_path: Path, rules_dir: Path) -> BuildData:
    data = BuildData()
    for lineno, line in iter_rule_section(conf_path):
        data.processed_conf_rules += 1
        parts = [part.strip() for part in line.split(",")]
        head = parts[0].upper()
        source = f"{conf_path.name}:{lineno}"

        if head in {"FINAL", "MATCH"}:
            continue

        if head == "AND":
            data.drop("composite_and", f"{source}: {line}")
            continue

        if head == "RULE-SET":
            if len(parts) < 3:
                data.drop("invalid_ruleset", f"{source}: {line}")
                continue
            ruleset_url = parts[1]
            action = parse_action(parts[2])
            if action is None:
                data.drop("unsupported_action", f"{source}: {line}")
                continue
            local_name = parse_ruleset_url(ruleset_url)
            if local_name in HAPP_EXCLUDED_RULESETS:
                data.drop("excluded_happ_ruleset", f"{source}: {local_name}")
                continue
            list_path = rules_dir / local_name
            if not list_path.exists():
                data.drop("missing_ruleset_file", f"{source}: {local_name}")
                continue
            for idx, raw in enumerate(list_path.read_text(encoding="utf-8", errors="ignore").splitlines(), start=1):
                entry = raw.strip()
                if not entry or entry.startswith(("#", "!", ";", "[")):
                    continue
                data.processed_ruleset_lines += 1
                convert_rule_line(entry, action, data, f"{local_name}:{idx}")
            continue

        if head in SUPPORTED_SITE_RULES | SUPPORTED_IP_RULES:
            if len(parts) < 3:
                data.drop("missing_inline_action", f"{source}: {line}")
                continue
            action = parse_action(parts[2])
            if action is None:
                data.drop("unsupported_action", f"{source}: {line}")
                continue
            convert_rule_line(line, action, data, source)
            continue

        data.drop("unsupported_rule_type", f"{source}: {line}")
    return data


def dedupe_preserve(items: list[str]) -> list[str]:
    seen: set[str] = set()
    output: list[str] = []
    for item in items:
        if item in seen:
            continue
        seen.add(item)
        output.append(item)
    return output


def ensure_bucket_uniques(data: BuildData) -> None:
    for bucket in (data.direct, data.proxy, data.block):
        bucket.site_rules = dedupe_preserve(bucket.site_rules)
        bucket.cidrs = dedupe_preserve(bucket.cidrs)
        bucket.geo_tags = dedupe_preserve(bucket.geo_tags)


def write_geosite_inputs(geosite_data_dir: Path, data: BuildData) -> None:
    (geosite_data_dir / "sr-direct").write_text("\n".join(data.direct.site_rules) + ("\n" if data.direct.site_rules else ""), encoding="utf-8")
    (geosite_data_dir / "sr-proxy").write_text("\n".join(data.proxy.site_rules) + ("\n" if data.proxy.site_rules else ""), encoding="utf-8")
    if data.block.site_rules:
        (geosite_data_dir / "sr-block").write_text("\n".join(data.block.site_rules) + "\n", encoding="utf-8")
    else:
        block_file = geosite_data_dir / "sr-block"
        if block_file.exists():
            block_file.unlink()


def build_geosite_dat(out_dir: Path, data: BuildData) -> Path:
    with tempfile.TemporaryDirectory(prefix="sr-happ-geosite-") as tmp_dir:
        tmp = Path(tmp_dir)
        repo = tmp / "domain-list-community"
        run(["git", "clone", "--depth", "1", "https://github.com/v2fly/domain-list-community.git", str(repo)])
        write_geosite_inputs(repo / "data", data)
        run(["go", "mod", "download"], cwd=repo)
        run(["go", "run", "./", f"--datapath={repo / 'data'}"], cwd=repo)
        candidates = [repo / "dlc.dat", repo / "output" / "dat" / "dlc.dat"]
        source = next((path for path in candidates if path.exists()), None)
        if source is None:
            raise RuntimeError("Failed to build geosite.dat: dlc.dat not found")
        target = out_dir / "geosite.dat"
        target.write_bytes(source.read_bytes())
        return target


def write_geoip_config(geoip_repo: Path, data: BuildData) -> Path:
    lists_dir = geoip_repo / "custom-lists"
    lists_dir.mkdir(parents=True, exist_ok=True)

    def write_list(name: str, values: list[str]) -> Path:
        path = lists_dir / f"{name}.txt"
        path.write_text("\n".join(values) + ("\n" if values else ""), encoding="utf-8")
        return path

    direct_file = write_list("sr-direct", data.direct.cidrs)
    proxy_file = write_list("sr-proxy", data.proxy.cidrs)
    block_file = write_list("sr-block", data.block.cidrs)

    config = {
        "input": [
            {
                "type": "v2rayGeoIPDat",
                "action": "add",
                "args": {
                    "uri": "https://github.com/v2fly/geoip/releases/latest/download/geoip.dat",
                },
            },
            {
                "type": "text",
                "action": "add",
                "args": {"name": "sr-direct", "uri": str(direct_file)},
            },
            {
                "type": "text",
                "action": "add",
                "args": {"name": "sr-proxy", "uri": str(proxy_file)},
            },
        ],
        "output": [
            {
                "type": "v2rayGeoIPDat",
                "action": "output",
                "args": {
                    "outputDir": str(geoip_repo / "output" / "dat"),
                    "outputName": "geoip.dat",
                    "wantedList": HAPP_GEOIP_WANTED_LIST,
                    "onlyIPType": "ipv4",
                },
            }
        ],
    }
    if data.block.cidrs:
        config["input"].append(
            {
                "type": "text",
                "action": "add",
                "args": {"name": "sr-block", "uri": str(block_file)},
            }
        )
    config_path = geoip_repo / "config.custom.json"
    config_path.write_text(json.dumps(config, indent=2), encoding="utf-8")
    return config_path


def build_geoip_dat(out_dir: Path, data: BuildData) -> Path:
    with tempfile.TemporaryDirectory(prefix="sr-happ-geoip-") as tmp_dir:
        tmp = Path(tmp_dir)
        repo = tmp / "geoip"
        run(["git", "clone", "--depth", "1", "https://github.com/v2fly/geoip.git", str(repo)])
        run(["go", "mod", "download"], cwd=repo)
        config_path = write_geoip_config(repo, data)
        run(["go", "run", "./", "-c", str(config_path)], cwd=repo)
        source = repo / "output" / "dat" / "geoip.dat"
        if not source.exists():
            raise RuntimeError("Failed to build geoip.dat: output/dat/geoip.dat not found")
        target = out_dir / "geoip.dat"
        target.write_bytes(source.read_bytes())
        return target


def repo_slug(repo_root: Path) -> str:
    remote = run(["git", "-C", str(repo_root), "remote", "get-url", "origin"])
    remote = remote.strip()
    if remote.endswith(".git"):
        remote = remote[:-4]
    if remote.startswith("git@github.com:"):
        return remote.removeprefix("git@github.com:")
    marker = "github.com/"
    if marker in remote:
        return remote.split(marker, 1)[1]
    raise RuntimeError(f"Unsupported origin URL format: {remote}")


def commit_sha(repo_root: Path) -> str:
    return run(["git", "-C", str(repo_root), "rev-parse", "HEAD"])


def build_profile(
    data: BuildData,
    raw_base: str,
    route_order: str,
    remote_dns_ip: str,
    domestic_dns_ip: str,
    remote_dns_type: str,
    domestic_dns_type: str,
) -> dict[str, object]:
    direct_geo = dedupe_preserve(data.direct.geo_tags)
    proxy_geo = dedupe_preserve(data.proxy.geo_tags)
    block_geo = dedupe_preserve(data.block.geo_tags)

    direct_ip = dedupe_preserve(["geoip:private", "geoip:ru", "geoip:sr-direct"] + direct_geo)
    proxy_ip = dedupe_preserve(["geoip:sr-proxy"] + proxy_geo)
    block_ip = dedupe_preserve((["geoip:sr-block"] if data.block.cidrs else []) + block_geo)

    profile = {
        "Name": "ShadowRocket-HAPP",
        "GlobalProxy": "true",
        "UseChunkFiles": "true",
        "RemoteDns": remote_dns_ip,
        "DomesticDns": domestic_dns_ip,
        "RemoteDNSType": remote_dns_type,
        "RemoteDNSDomain": "",
        "RemoteDNSIP": remote_dns_ip,
        "DomesticDNSType": domestic_dns_type,
        "DomesticDNSDomain": "",
        "DomesticDNSIP": domestic_dns_ip,
        "Geoipurl": f"{raw_base}/geoip.dat",
        "Geositeurl": f"{raw_base}/geosite.dat",
        "LastUpdated": str(int(time.time())),
        "DnsHosts": {},
        "RouteOrder": route_order,
        "DirectSites": ["geosite:private", "geosite:sr-direct"],
        "DirectIp": direct_ip,
        "ProxySites": ["geosite:sr-proxy"],
        "ProxyIp": proxy_ip,
        "BlockSites": ["geosite:sr-block"] if data.block.site_rules else [],
        "BlockIp": block_ip if data.block.cidrs or block_geo else [],
        "DomainStrategy": "IPIfNonMatch",
        "FakeDNS": "false",
    }
    return profile


def write_report(
    out_path: Path,
    conf_path: Path,
    data: BuildData,
    json_length: int,
    deeplink_length: int,
    sha: str,
    mode: str,
    profile: dict[str, object],
    dns_notes: list[str],
) -> None:
    dropped_total = sum(len(items) for items in data.dropped.values())

    lines: list[str] = []
    lines.append("# HAPP Routing Build Report")
    lines.append("")
    lines.append("## Source")
    lines.append(f"- Config: `{conf_path}`")
    lines.append(f"- Commit: `{sha}`")
    lines.append("")
    lines.append("## Processed")
    lines.append(f"- Rules in `[Rule]`: {data.processed_conf_rules}")
    lines.append(f"- RULE-SET entries parsed: {data.processed_ruleset_lines}")
    lines.append(f"- Converted lines: {data.converted_lines}")
    lines.append(f"- Dropped lines: {dropped_total}")
    lines.append("")
    lines.append("## Output")
    lines.append(f"- Deeplink mode: `{mode}`")
    lines.append(f"- JSON length (compact): {json_length}")
    lines.append(f"- Deeplink length: {deeplink_length}")
    lines.append(f"- DirectSites: {len(profile['DirectSites'])}")
    lines.append(f"- ProxySites: {len(profile['ProxySites'])}")
    lines.append(f"- BlockSites: {len(profile['BlockSites'])}")
    lines.append(f"- DirectIp: {len(profile['DirectIp'])}")
    lines.append(f"- ProxyIp: {len(profile['ProxyIp'])}")
    lines.append(f"- BlockIp: {len(profile['BlockIp'])}")
    lines.append("")
    lines.append("## DNS source")
    for item in dns_notes:
        lines.append(item)
    if not dns_notes:
        lines.append("- none")
    lines.append("")
    lines.append("## Dropped USER-AGENT")
    for item in data.dropped.get("user_agent", []):
        lines.append(f"- {item}")
    if not data.dropped.get("user_agent"):
        lines.append("- none")
    lines.append("")
    lines.append("## Dropped DST-PORT")
    for item in data.dropped.get("dst_port", []):
        lines.append(f"- {item}")
    if not data.dropped.get("dst_port"):
        lines.append("- none")
    lines.append("")
    lines.append("## Dropped IP-ASN")
    for item in data.dropped.get("ip_asn", []):
        lines.append(f"- {item}")
    if not data.dropped.get("ip_asn"):
        lines.append("- none")
    lines.append("")
    lines.append("## Dropped composite AND")
    for item in data.dropped.get("composite_and", []):
        lines.append(f"- {item}")
    if not data.dropped.get("composite_and"):
        lines.append("- none")
    lines.append("")
    lines.append("## Other dropped reasons")
    other_reasons = [
        reason
        for reason in sorted(data.dropped)
        if reason not in {"user_agent", "dst_port", "ip_asn", "composite_and"}
    ]
    if not other_reasons:
        lines.append("- none")
    else:
        for reason in other_reasons:
            lines.append(f"- {reason}: {len(data.dropped[reason])}")

    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    args = parse_args()
    repo_root = Path.cwd()
    conf_path = (repo_root / args.conf).resolve()
    rules_dir = (repo_root / args.rules_dir).resolve()
    out_dir = (repo_root / args.out_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    if not conf_path.exists():
        raise FileNotFoundError(f"Config not found: {conf_path}")
    if not rules_dir.exists():
        raise FileNotFoundError(f"Rules directory not found: {rules_dir}")

    dns = resolve_happ_dns(conf_path, args)

    data = parse_conf_and_lists(conf_path, rules_dir)
    ensure_bucket_uniques(data)

    build_geosite_dat(out_dir, data)
    build_geoip_dat(out_dir, data)

    slug = repo_slug(repo_root)
    raw_base = f"https://raw.githubusercontent.com/{slug}/main/{args.out_dir.strip('/')}"
    profile = build_profile(
        data=data,
        raw_base=raw_base,
        route_order=args.route_order,
        remote_dns_ip=dns.remote_ip,
        domestic_dns_ip=dns.domestic_ip,
        remote_dns_type=args.remote_dns_type,
        domestic_dns_type=args.domestic_dns_type,
    )

    json_pretty = json.dumps(profile, indent=2, ensure_ascii=False)
    json_compact = json.dumps(profile, separators=(",", ":"), ensure_ascii=False)
    encoded = base64.b64encode(json_compact.encode("utf-8")).decode("ascii")
    deeplink = f"happ://routing/{args.deeplink_mode}/{encoded}"

    (out_dir / "DEFAULT.JSON").write_text(json_pretty + "\n", encoding="utf-8")
    (out_dir / "DEFAULT.DEEPLINK").write_text(deeplink + "\n", encoding="utf-8")

    write_report(
        out_path=out_dir / "REPORT.md",
        conf_path=conf_path,
        data=data,
        json_length=len(json_compact),
        deeplink_length=len(deeplink),
        sha=commit_sha(repo_root),
        mode=args.deeplink_mode,
        profile=profile,
        dns_notes=dns.notes,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
