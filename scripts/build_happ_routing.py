#!/usr/bin/env python3
"""Build HAPP routing artifacts from distillate outputs."""

from __future__ import annotations

import argparse
import base64
import ipaddress
import json
import shlex
import subprocess
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable
from urllib.parse import urlparse


DEFAULT_PROFILE_NAME = "роут-MotivatoPotato"
OBSOLETE_HAPP_FILES = (
    "geoip.dat",
    "geosite.dat",
    "default_geoip.dat",
    "default_geosite.dat",
    "BONUS.JSON",
    "BONUS.DEEPLINK",
    "bonus_geoip.dat",
    "bonus_geosite.dat",
    "REPORT.md",
)
DEFAULT_REMOTE_DNS_IP = "8.8.8.8"
DEFAULT_REMOTE_DNS_DOMAIN = "https://8.8.8.8/dns-query"
DEFAULT_DOMESTIC_DNS_IP = "77.88.8.8"
DEFAULT_DOMESTIC_DNS_DOMAIN = "https://77.88.8.8/dns-query"
DEFAULT_DNS_HOSTS: dict[str, str] = {}
@dataclass
class Bucket:
    site_rules: list[str] = field(default_factory=list)
    cidrs: list[str] = field(default_factory=list)


@dataclass
class BuildData:
    direct: Bucket = field(default_factory=Bucket)
    proxy: Bucket = field(default_factory=Bucket)
    block: Bucket = field(default_factory=Bucket)
    processed_domain_lines: int = 0
    processed_ip_lines: int = 0

    def bucket(self, action: str) -> Bucket:
        if action == "direct":
            return self.direct
        if action == "proxy":
            return self.proxy
        return self.block


def dedupe_preserve(items: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    output: list[str] = []
    for item in items:
        if item in seen:
            continue
        seen.add(item)
        output.append(item)
    return output


def run(cmd: list[str], cwd: Path | None = None) -> str:
    result = subprocess.run(
        cmd,
        cwd=str(cwd) if cwd else None,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    if result.returncode != 0:
        detail = result.stderr.strip() or result.stdout.strip() or f"exit code {result.returncode}"
        raise RuntimeError(f"Command failed: {shlex.join(cmd)}\n{detail}")
    return result.stdout.strip()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build HAPP routing artifacts.")
    parser.add_argument("--conf", default="shadowrocket.conf", help="Path to shadowrocket.conf")
    parser.add_argument("--distillate-dir", default="distillate", help="Directory containing distillate outputs")
    parser.add_argument("--out-dir", default="HAPP", help="Output directory")
    parser.add_argument(
        "--deeplink-mode",
        default="onadd",
        choices=["onadd", "add"],
        help="HAPP deeplink mode",
    )
    parser.add_argument(
        "--route-order",
        default="block-proxy-direct",
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
    parser.add_argument("--remote-dns-ip", default=DEFAULT_REMOTE_DNS_IP, help="Remote DNS IP")
    parser.add_argument("--domestic-dns-ip", default=DEFAULT_DOMESTIC_DNS_IP, help="Domestic DNS IP")
    parser.add_argument(
        "--remote-dns-type",
        default="DoH",
        choices=["DoH", "DoU"],
        help="Remote DNS type",
    )
    parser.add_argument(
        "--remote-dns-domain",
        default=DEFAULT_REMOTE_DNS_DOMAIN,
        help="Remote DNS domain or URL (used for DoH)",
    )
    parser.add_argument(
        "--domestic-dns-type",
        default="DoH",
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


def extract_remote_dns_ip(conf_path: Path) -> str | None:
    values = extract_general_values(conf_path)
    dns_value = values.get("dns-server")
    if not dns_value:
        return None
    first = dns_value.split(",", 1)[0].strip()
    if not first:
        return None
    if "://" in first:
        parsed = urlparse(first)
        return parsed.hostname
    return first


def normalize_cidr(value: str) -> str:
    return str(ipaddress.ip_network(value.strip(), strict=False))


def extract_general_ips(conf_path: Path, key: str) -> list[str]:
    values = extract_general_values(conf_path)
    raw_value = values.get(key, "")
    if not raw_value:
        return []

    ips: list[str] = []
    for token in (item.strip() for item in raw_value.split(",")):
        if not token:
            continue
        try:
            if "/" in token:
                ips.append(normalize_cidr(token))
            else:
                ips.append(str(ipaddress.ip_address(token)))
        except ValueError:
            continue
    return dedupe_preserve(ips)


def extract_skip_proxy_ips(conf_path: Path) -> list[str]:
    return extract_general_ips(conf_path, "skip-proxy")


def extract_bypass_tun_ips(conf_path: Path) -> list[str]:
    return extract_general_ips(conf_path, "bypass-tun")


def read_text_lines(path: Path) -> list[str]:
    if not path.exists():
        return []
    return [line.strip() for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def load_build_data_from_distillate(distillate_dir: Path) -> BuildData:
    data = BuildData()
    for bucket_name in ("direct", "proxy", "block"):
        bucket = data.bucket(bucket_name)
        site_lines = read_text_lines(distillate_dir / "text" / "domain" / f"sr-{bucket_name}.txt")
        ip_lines = read_text_lines(distillate_dir / "text" / "ip" / f"sr-{bucket_name}.txt")
        bucket.site_rules = dedupe_preserve(site_lines)
        bucket.cidrs = dedupe_preserve(ip_lines)
        data.processed_domain_lines += len(bucket.site_rules)
        data.processed_ip_lines += len(bucket.cidrs)
    return data


def repo_slug(repo_root: Path) -> str:
    remote = run(["git", "-C", str(repo_root), "remote", "get-url", "origin"]).strip()
    if remote.endswith(".git"):
        remote = remote[:-4]
    if remote.startswith("git@github.com:"):
        return remote.removeprefix("git@github.com:")
    marker = "github.com/"
    if marker in remote:
        return remote.split(marker, 1)[1]
    raise RuntimeError(f"Unsupported origin URL format: {remote}")


def build_profile(
    data: BuildData,
    geodata_base: str,
    route_order: str,
    remote_dns_ip: str,
    remote_dns_domain: str,
    domestic_dns_ip: str,
    remote_dns_type: str,
    domestic_dns_type: str,
    general_direct_ips: list[str],
    profile_name: str,
    block_geosite_tag: str | None,
) -> dict[str, object]:
    direct_ip = dedupe_preserve(general_direct_ips + (["geoip:sr-direct"] if data.direct.cidrs else []))
    proxy_ip = ["geoip:sr-proxy"] if data.proxy.cidrs else []
    block_ip = ["geoip:sr-block"] if data.block.cidrs else []
    direct_sites = ["geosite:sr-direct"] if data.direct.site_rules else []
    proxy_sites = ["geosite:sr-proxy"] if data.proxy.site_rules else []
    block_sites = [f"geosite:{block_geosite_tag}"] if data.block.site_rules and block_geosite_tag else []

    return {
        "Name": profile_name,
        "GlobalProxy": "true",
        "UseChunkFiles": "false",
        "RemoteDns": remote_dns_ip,
        "DomesticDns": domestic_dns_ip,
        "RemoteDNSType": remote_dns_type,
        "RemoteDNSDomain": remote_dns_domain,
        "RemoteDNSIP": remote_dns_ip,
        "DomesticDNSType": domestic_dns_type,
        "DomesticDNSDomain": DEFAULT_DOMESTIC_DNS_DOMAIN if domestic_dns_type == "DoH" else "",
        "DomesticDNSIP": domestic_dns_ip,
        "Geoipurl": f"{geodata_base}/geoip.dat",
        "Geositeurl": f"{geodata_base}/geosite.dat",
        "LastUpdated": str(int(time.time())),
        "DnsHosts": DEFAULT_DNS_HOSTS,
        "RouteOrder": route_order,
        "DirectSites": direct_sites,
        "DirectIp": direct_ip,
        "ProxySites": proxy_sites,
        "ProxyIp": proxy_ip,
        "BlockSites": block_sites,
        "BlockIp": block_ip,
        "DomainStrategy": "IPIfNonMatch",
        "FakeDNS": "false",
    }


def profile_to_deeplink(profile: dict[str, object], mode: str) -> tuple[str, str, str]:
    json_pretty = json.dumps(profile, indent=2, ensure_ascii=False)
    json_compact = json.dumps(profile, separators=(",", ":"), ensure_ascii=False)
    encoded = base64.b64encode(json_compact.encode("utf-8")).decode("ascii")
    deeplink = f"happ://routing/{mode}/{encoded}"
    return json_pretty, json_compact, deeplink
def remove_obsolete_happ_files(out_dir: Path) -> None:
    for name in OBSOLETE_HAPP_FILES:
        (out_dir / name).unlink(missing_ok=True)


def main() -> int:
    args = parse_args()
    repo_root = Path.cwd()
    conf_path = (repo_root / args.conf).resolve()
    distillate_dir = (repo_root / args.distillate_dir).resolve()
    out_dir = (repo_root / args.out_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    if not conf_path.exists():
        raise FileNotFoundError(f"Config not found: {conf_path}")
    if not distillate_dir.exists():
        raise FileNotFoundError(f"Distillate directory not found: {distillate_dir}")
    if not (distillate_dir / "dat" / "geosite.dat").exists() or not (distillate_dir / "dat" / "geoip.dat").exists():
        raise FileNotFoundError(
            "distillate dat artifacts are missing; run scripts/build_distillate.py before build_happ_routing.py"
        )

    remove_obsolete_happ_files(out_dir)

    remote_dns_ip = args.remote_dns_ip
    general_direct_ips = dedupe_preserve(extract_skip_proxy_ips(conf_path) + extract_bypass_tun_ips(conf_path))
    data = load_build_data_from_distillate(distillate_dir)

    slug = repo_slug(repo_root)
    geodata_base = f"https://raw.githubusercontent.com/{slug}/main/{args.distillate_dir.strip('/')}/dat"
    block_site_tag = "motivato-block" if read_text_lines(distillate_dir / "text" / "domain" / "motivato_block.txt") else None
    default_profile = build_profile(
        data=data,
        geodata_base=geodata_base,
        route_order=args.route_order,
        remote_dns_ip=remote_dns_ip,
        remote_dns_domain=args.remote_dns_domain,
        domestic_dns_ip=args.domestic_dns_ip,
        remote_dns_type=args.remote_dns_type,
        domestic_dns_type=args.domestic_dns_type,
        general_direct_ips=general_direct_ips,
        profile_name=DEFAULT_PROFILE_NAME,
        block_geosite_tag=block_site_tag,
    )
    default_pretty, _, default_deeplink = profile_to_deeplink(default_profile, args.deeplink_mode)
    (out_dir / "DEFAULT.JSON").write_text(default_pretty + "\n", encoding="utf-8")
    (out_dir / "DEFAULT.DEEPLINK").write_text(default_deeplink + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
