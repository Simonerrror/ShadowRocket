#!/usr/bin/env python3
"""Build INCY routing artifacts from the same distillate data as HAPP."""

from __future__ import annotations

import argparse
import base64
import json
from pathlib import Path

try:
    from scripts import build_happ_routing as happ
except ModuleNotFoundError:  # pragma: no cover - supports direct script execution
    import build_happ_routing as happ


DEFAULT_OUTPUT_DIR = "INCY"
INCY_SCHEME = "incy"
DEFAULT_PROFILE_NAME = happ.DEFAULT_PROFILE_NAME
RU_PROFILE_NAME = happ.RU_PROFILE_NAME
OBSOLETE_INCY_FILES = happ.OBSOLETE_HAPP_FILES


def build_profile(
    data: happ.BuildData,
    geodata_base: str,
    last_updated: str,
    route_order: str,
    remote_dns_ip: str,
    remote_dns_domain: str,
    domestic_dns_ip: str,
    remote_dns_type: str,
    domestic_dns_type: str,
    general_direct_ips: list[str],
    profile_name: str,
    block_geosite_tag: str | None,
    global_proxy: str = "true",
    direct_geosite_tag: str | None = "sr-direct",
    direct_geoip_tag: str | None = "sr-direct",
    proxy_geosite_tag: str | None = "sr-proxy",
    proxy_geoip_tag: str | None = "sr-proxy",
) -> dict[str, object]:
    """Adapt HAPP's routing payload to the official INCY field spelling/types."""

    happ_profile = happ.build_profile(
        data=data,
        geodata_base=geodata_base,
        last_updated=last_updated,
        route_order=route_order,
        remote_dns_ip=remote_dns_ip,
        remote_dns_domain=remote_dns_domain,
        domestic_dns_ip=domestic_dns_ip,
        remote_dns_type=remote_dns_type,
        domestic_dns_type=domestic_dns_type,
        general_direct_ips=general_direct_ips,
        profile_name=profile_name,
        block_geosite_tag=block_geosite_tag,
        global_proxy=global_proxy,
        direct_geosite_tag=direct_geosite_tag,
        direct_geoip_tag=direct_geoip_tag,
        proxy_geosite_tag=proxy_geosite_tag,
        proxy_geoip_tag=proxy_geoip_tag,
    )

    # Preserve HAPP's key order for reproducible compact payloads while using
    # INCY's documented lower-case boolean field.
    return {
        ("useChunkFiles" if key == "UseChunkFiles" else key): (
            False if key == "UseChunkFiles" else value
        )
        for key, value in happ_profile.items()
    }


# Name the adapter explicitly for callers that want to distinguish it from HAPP.
build_incy_profile = build_profile


def profile_to_deeplink(profile: dict[str, object], mode: str) -> tuple[str, str, str]:
    """Serialize an INCY profile and return pretty JSON, compact JSON, and deeplink."""

    if mode not in {"add", "onadd"}:
        raise ValueError(f"Unsupported INCY deeplink mode: {mode}")
    json_pretty = json.dumps(profile, indent=2, ensure_ascii=False)
    json_compact = json.dumps(profile, separators=(",", ":"), ensure_ascii=False)
    encoded = base64.b64encode(json_compact.encode("utf-8")).decode("ascii")
    return json_pretty, json_compact, f"{INCY_SCHEME}://routing/{mode}/{encoded}"


def existing_build_stamp(out_dir: Path) -> str | None:
    return happ.existing_build_stamp(out_dir)


def resolve_build_stamp(repo_root: Path, explicit_value: str, out_dir: Path | None = None) -> str:
    """Preserve INCY's stamp, then the paired HAPP stamp, then HAPP's fallback."""

    if explicit_value:
        return explicit_value
    if out_dir is not None:
        preserved = existing_build_stamp(out_dir)
        if preserved is not None:
            return preserved
    happ_stamp = existing_build_stamp(repo_root / "HAPP")
    if happ_stamp is not None:
        return happ_stamp
    return happ.resolve_build_stamp(repo_root, explicit_value, out_dir)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build INCY routing artifacts.")
    parser.add_argument("--conf", default="shadowrocket.conf", help="Path to shadowrocket.conf")
    parser.add_argument("--distillate-dir", default="distillate", help="Directory containing distillate outputs")
    parser.add_argument("--out-dir", default=DEFAULT_OUTPUT_DIR, help="Output directory")
    parser.add_argument(
        "--deeplink-mode",
        default="onadd",
        choices=["onadd", "add"],
        help="INCY deeplink mode",
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
        help="RouteOrder value for INCY profile",
    )
    parser.add_argument("--remote-dns-ip", default=happ.DEFAULT_REMOTE_DNS_IP, help="Remote DNS IP")
    parser.add_argument("--domestic-dns-ip", default=happ.DEFAULT_DOMESTIC_DNS_IP, help="Domestic DNS IP")
    parser.add_argument(
        "--remote-dns-type",
        default="DoH",
        choices=["DoH", "DoU"],
        help="Remote DNS type",
    )
    parser.add_argument(
        "--remote-dns-domain",
        default=happ.DEFAULT_REMOTE_DNS_DOMAIN,
        help="Remote DNS domain or URL (used for DoH)",
    )
    parser.add_argument(
        "--domestic-dns-type",
        default="DoH",
        choices=["DoH", "DoU"],
        help="Domestic DNS type",
    )
    parser.add_argument(
        "--build-stamp",
        default="",
        help="Stable LastUpdated value written into DEFAULT.JSON/DEEPLINK.",
    )
    return parser.parse_args(argv)


def write_text_if_changed(path: Path, content: str) -> None:
    happ.write_text_if_changed(path, content)


def remove_obsolete_incy_files(out_dir: Path) -> None:
    for name in OBSOLETE_INCY_FILES:
        (out_dir / name).unlink(missing_ok=True)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
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
            "distillate dat artifacts are missing; run scripts/build_distillate.py before build_incy_routing.py"
        )

    remove_obsolete_incy_files(out_dir)
    data = happ.load_build_data_from_distillate(distillate_dir)
    general_direct_ips = happ.dedupe_preserve(
        happ.extract_skip_proxy_ips(conf_path) + happ.extract_bypass_tun_ips(conf_path)
    )
    geodata_base = f"https://raw.githubusercontent.com/{happ.repo_slug(repo_root)}/main/{args.distillate_dir.strip('/')}/dat"
    block_site_tag = (
        "motivato-block"
        if happ.read_text_lines(distillate_dir / "text" / "domain" / "motivato_block.txt")
        else None
    )
    build_stamp = resolve_build_stamp(repo_root, args.build_stamp, out_dir)

    common = {
        "data": data,
        "geodata_base": geodata_base,
        "last_updated": build_stamp,
        "route_order": args.route_order,
        "remote_dns_ip": args.remote_dns_ip,
        "remote_dns_domain": args.remote_dns_domain,
        "domestic_dns_ip": args.domestic_dns_ip,
        "remote_dns_type": args.remote_dns_type,
        "domestic_dns_type": args.domestic_dns_type,
        "general_direct_ips": general_direct_ips,
        "block_geosite_tag": block_site_tag,
    }
    default_profile = build_profile(
        **common,
        profile_name=DEFAULT_PROFILE_NAME,
    )
    default_pretty, _, default_deeplink = profile_to_deeplink(default_profile, args.deeplink_mode)
    write_text_if_changed(out_dir / "DEFAULT.JSON", default_pretty + "\n")
    write_text_if_changed(out_dir / "DEFAULT.DEEPLINK", default_deeplink + "\n")

    ru_profile = build_profile(
        **common,
        profile_name=RU_PROFILE_NAME,
        global_proxy="false",
        direct_geosite_tag=None,
        direct_geoip_tag=None,
        proxy_geosite_tag="category-ru",
        proxy_geoip_tag="ru",
    )
    ru_pretty, _, ru_deeplink = profile_to_deeplink(ru_profile, args.deeplink_mode)
    write_text_if_changed(out_dir / "RU-VPN.JSON", ru_pretty + "\n")
    write_text_if_changed(out_dir / "RU-VPN.DEEPLINK", ru_deeplink + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
