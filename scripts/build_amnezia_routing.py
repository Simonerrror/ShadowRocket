#!/usr/bin/env python3
"""Build the shared IPv4 exclusion list for AmneziaVPN."""

from __future__ import annotations

import argparse
import ipaddress
import json
import os
import sys
import tempfile
from pathlib import Path
from typing import Iterable


RU_IPV4_PATH = Path("distillate/upstream/v2fly/ru_ipv4.txt")
SR_DIRECT_IP_PATH = Path("distillate/text/ip/sr-direct.txt")
SR_DIRECT_DOMAIN_PATH = Path("distillate/text/domain/sr-direct.txt")
OUTPUT_PATH = Path("Amnezia/SR-DEFAULT-EXCLUDE.json")
SUMMARY_PATH = Path("Amnezia/SR-DEFAULT-EXCLUDE.summary.json")

FIXED_EXCLUSIONS = (
    "10.0.0.0/8",
    "100.64.0.0/10",
    "169.254.0.0/16",
    "172.16.0.0/12",
    "192.168.0.0/16",
    "224.0.0.0/4",
)


class AmneziaRoutingError(RuntimeError):
    """Raised when an Amnezia routing input or output is invalid."""


def _input_lines(path: Path) -> list[str]:
    if not path.exists():
        raise AmneziaRoutingError(f"Input file is missing: {path}")
    if not path.is_file():
        raise AmneziaRoutingError(f"Input path is not a file: {path}")
    try:
        payload = path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        raise AmneziaRoutingError(f"Unable to read input {path}: {exc}") from exc

    lines: list[str] = []
    for raw in payload.splitlines():
        line = raw.strip().lstrip("\ufeff")
        if not line or line.startswith(("#", "!", ";", "//")):
            continue
        lines.append(line)
    return lines


def parse_ipv4_cidrs(path: Path, source_name: str | None = None) -> list[ipaddress.IPv4Network]:
    """Read and canonicalize IPv4 CIDRs from *path*, retaining source order."""

    label = source_name or str(path)
    networks: list[ipaddress.IPv4Network] = []
    for line_number, value in enumerate(_input_lines(path), start=1):
        try:
            network = ipaddress.ip_network(value, strict=False)
        except ValueError as exc:
            raise AmneziaRoutingError(
                f"Invalid IPv4 CIDR in {label} at input line {line_number}: {value!r}"
            ) from exc
        if network.version != 4:
            raise AmneziaRoutingError(
                f"IPv4 CIDR required in {label} at input line {line_number}: {value!r}"
            )
        networks.append(network)
    return networks


def canonicalize_ipv4_networks(networks: Iterable[ipaddress.IPv4Network]) -> list[str]:
    """Collapse only exactly covered adjacent ranges and sort numerically."""

    collapsed = ipaddress.collapse_addresses(networks)
    ordered = sorted(collapsed, key=lambda network: (int(network.network_address), network.prefixlen))
    return [str(network) for network in ordered]


def read_domain_rules(path: Path) -> list[str]:
    """Read canonical domain rules for reporting without resolving any names."""

    return _input_lines(path)


def _hostname_for_cidr(cidr: str) -> str:
    """Encode a CIDR as an importer-safe reserved pseudo-hostname."""

    network = ipaddress.ip_network(cidr)
    octets = str(network.network_address).split(".")
    return f"cidr-{'-'.join(octets)}-{network.prefixlen}.invalid"


def _source_counts(networks: list[ipaddress.IPv4Network]) -> dict[str, int]:
    return {
        "count": len(networks),
        "unique_count": len(set(networks)),
    }


def _atomic_write(path: Path, payload: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".tmp",
            delete=False,
        ) as handle:
            temporary_path = Path(handle.name)
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(temporary_path, 0o644)
        os.replace(temporary_path, path)
        temporary_path = None
    except OSError as exc:
        raise AmneziaRoutingError(f"Unable to replace output {path}: {exc}") from exc
    finally:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)


def build_artifacts(
    ru_ipv4_path: Path,
    sr_direct_ip_path: Path,
    sr_direct_domain_path: Path,
    output_path: Path,
    summary_path: Path,
) -> dict[str, object]:
    """Build and atomically publish the profile and its loss summary."""

    ru_networks = parse_ipv4_cidrs(ru_ipv4_path, "RU IPv4 source")
    if not ru_networks:
        raise AmneziaRoutingError(f"RU IPv4 source is empty: {ru_ipv4_path}")
    direct_networks = parse_ipv4_cidrs(sr_direct_ip_path, "Shadowrocket DIRECT IPv4 source")
    fixed_networks = parse_ipv4_cidrs_from_values(FIXED_EXCLUSIONS, "fixed exclusions")
    domain_rules = read_domain_rules(sr_direct_domain_path)

    cidrs = canonicalize_ipv4_networks((*ru_networks, *direct_networks, *fixed_networks))
    profile = [{"hostname": _hostname_for_cidr(cidr), "ip": cidr} for cidr in cidrs]
    summary: dict[str, object] = {
        "mode": "exclude-vpn",
        "intent": (
            "Addresses from this list must not go through VPN; all other IPv4 addresses "
            "go through VPN."
        ),
        "encoding": {
            "hostname": "cidr-<network-octets>-<prefix>.invalid",
            "ip": "canonical IPv4 CIDR",
            "note": "CIDR stays in ip because the Amnezia importer strips '/' from hostname",
        },
        "sources": {
            "ru_ipv4": _source_counts(ru_networks),
            "sr_direct_ipv4": _source_counts(direct_networks),
            "fixed_exclusions": _source_counts(fixed_networks),
            "sr_direct_domains": {"count": len(domain_rules)},
        },
        "output_cidr_count": len(cidrs),
        "unrepresented_domain_direct_rules": {
            "count": len(domain_rules),
            "entries": domain_rules,
        },
    }

    profile_payload = json.dumps(profile, indent=2, ensure_ascii=False) + "\n"
    summary_payload = json.dumps(summary, indent=2, ensure_ascii=False) + "\n"
    _atomic_write(output_path, profile_payload)
    _atomic_write(summary_path, summary_payload)
    return {"cidrs": cidrs, "summary": summary}


def parse_ipv4_cidrs_from_values(
    values: Iterable[str], source_name: str,
) -> list[ipaddress.IPv4Network]:
    """Parse fixed in-code CIDRs through the same validation path as files."""

    networks: list[ipaddress.IPv4Network] = []
    for line_number, value in enumerate(values, start=1):
        try:
            network = ipaddress.ip_network(value, strict=False)
        except ValueError as exc:
            raise AmneziaRoutingError(
                f"Invalid IPv4 CIDR in {source_name} at input line {line_number}: {value!r}"
            ) from exc
        if network.version != 4:
            raise AmneziaRoutingError(
                f"IPv4 CIDR required in {source_name} at input line {line_number}: {value!r}"
            )
        networks.append(network)
    return networks


def _path_from_cwd(value: str | Path) -> Path:
    path = Path(value)
    return path if path.is_absolute() else Path.cwd() / path


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build the AmneziaVPN IPv4 exclusion profile.")
    parser.add_argument("--ru-ipv4", default=str(RU_IPV4_PATH), help="Compiled RU IPv4 CIDR source")
    parser.add_argument("--sr-direct-ip", default=str(SR_DIRECT_IP_PATH), help="Shadowrocket DIRECT IPv4 source")
    parser.add_argument(
        "--sr-direct-domain",
        default=str(SR_DIRECT_DOMAIN_PATH),
        help="Shadowrocket DIRECT domain source used for the loss summary",
    )
    parser.add_argument("--output", default=str(OUTPUT_PATH), help="Amnezia profile output path")
    parser.add_argument("--summary-output", default=str(SUMMARY_PATH), help="Loss summary output path")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        result = build_artifacts(
            _path_from_cwd(args.ru_ipv4),
            _path_from_cwd(args.sr_direct_ip),
            _path_from_cwd(args.sr_direct_domain),
            _path_from_cwd(args.output),
            _path_from_cwd(args.summary_output),
        )
    except AmneziaRoutingError as exc:
        print(f"Amnezia routing build failed: {exc}", file=sys.stderr)
        return 1
    print(f"Built Amnezia IPv4 exclusion profile with {len(result['cidrs'])} CIDRs")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
