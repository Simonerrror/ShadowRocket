#!/usr/bin/env python3
"""Build HAPP routing artifacts from shadowrocket.conf and local rule lists."""

from __future__ import annotations

import argparse
import base64
import ipaddress
import json
import shlex
import shutil
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
HAPP_SUFFIX_ONLY_GEOSITE = False
DEFAULT_REMOTE_DNS_DOMAIN = "https://adfree.dns.nextdns.io/dns-query"
GEOSITE_COMPILER_REPO = "https://github.com/v2fly/domain-list-community.git"
ROSCOM_GEOSITE_SOURCE_REPO = "https://github.com/hydraponique/roscomvpn-geosite.git"
ROSCOM_GEOSITE_TAG = "202602210214"
ROSCOM_DEFAULT_PROFILE_URL = "https://raw.githubusercontent.com/hydraponique/roscomvpn-routing/main/HAPP/DEFAULT.JSON"
ROSCOM_GEOIP_SOURCE_REPO = "https://github.com/hydraponique/roscomvpn-geoip.git"
BONUS_PROFILE_NAME = "роутинг+"
BONUS_GEOIP_FILENAME = "bonus_geoip.dat"
BONUS_GEOSITE_FILENAME = "bonus_geosite.dat"
DEFAULT_DNS_HOSTS = {
    "adfree.dns.nextdns.io": "76.76.2.0",
    "cloudflare-dns.com": "1.1.1.1",
    "one.one.one.one": "1.1.1.1",
}
DEFAULT_EXTRA_DIRECT_SITES = [
    "geosite:category-ru",
    "geosite:microsoft",
    "geosite:apple",
    "geosite:google-play",
    "geosite:epicgames",
    "geosite:riot",
    "geosite:escapefromtarkov",
    "geosite:steam",
    "geosite:twitch",
    "geosite:pinterest",
    "geosite:faceit",
]
DEFAULT_EXTRA_PROXY_SITES = [
    "geosite:github",
    "geosite:twitch-ads",
    "geosite:youtube",
    "geosite:telegram",
]
DEFAULT_EXTRA_BLOCK_SITES = [
    "geosite:win-spy",
    "geosite:torrent",
    "geosite:category-ads",
]
GEOIP_TAG_ALIASES = {
    "ru": "direct",
}
HYDRA_GEOIP_EXTERNAL_SOURCES = {
    "antifilterdownloadcommunity.txt": "https://community.antifilter.download/list/community.lst",
    "refilter.txt": "https://raw.githubusercontent.com/1andrevich/Re-filter-lists/refs/heads/main/ipsum.lst",
    "refiltercommunity.txt": "https://raw.githubusercontent.com/1andrevich/Re-filter-lists/refs/heads/main/community_ips.lst",
    "antifilternetwork.txt": "https://antifilter.network/download/ip.lst",
    "antifilternetworkcommunity.txt": "https://antifilter.network/downloads/custom.lst",
    "cdn.lst": "https://raw.githubusercontent.com/mansourjabin/cdn-ip-database/refs/heads/main/data/cdn.lst",
    "merged.sum": "https://raw.githubusercontent.com/PentiumB/CDN-RuleSet/refs/heads/main/release/merged.sum",
    "geolite_ru.lst": "https://raw.githubusercontent.com/hydraponique/countrydb/refs/heads/main/output/geolite2-geo-whois-asn-country-ipv4/ru.lst",
    "geolite_by.lst": "https://raw.githubusercontent.com/hydraponique/countrydb/refs/heads/main/output/geolite2-geo-whois-asn-country-ipv4/by.lst",
    "ipinfo_ru.lst": "https://raw.githubusercontent.com/Davoyan/ipinfo/refs/heads/main/geo/geoip/ru.lst",
    "ipinfo_by.lst": "https://raw.githubusercontent.com/Davoyan/ipinfo/refs/heads/main/geo/geoip/by.lst",
    "dbip_ru.lst": "https://raw.githubusercontent.com/hydraponique/countrydb/refs/heads/main/output/dbip-country-ipv4/ru.lst",
    "dbip_by.lst": "https://raw.githubusercontent.com/hydraponique/countrydb/refs/heads/main/output/dbip-country-ipv4/by.lst",
}


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


def run_with_retry(
    cmd: list[str],
    cwd: Path | None = None,
    attempts: int = 3,
    delay_seconds: float = 2.0,
) -> str:
    last_error: RuntimeError | None = None
    for attempt in range(1, attempts + 1):
        try:
            return run(cmd, cwd=cwd)
        except RuntimeError as exc:
            last_error = exc
            if attempt == attempts:
                break
            print(
                f"[retry {attempt}/{attempts}] {shlex.join(cmd)} failed, retrying in {delay_seconds * attempt:.1f}s",
                file=sys.stderr,
            )
            time.sleep(delay_seconds * attempt)
    assert last_error is not None
    raise last_error


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
        default="block-direct-proxy",
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


def normalize_geoip_tag(value: str) -> str:
    tag = value.strip().lower()
    return GEOIP_TAG_ALIASES.get(tag, tag)


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
            # HAPP compatibility: keep suffix-style matching only.
            if HAPP_SUFFIX_ONLY_GEOSITE:
                bucket.site_rules.append(f"domain:{normalize_domain(raw_value)}")
            else:
                bucket.site_rules.append(f"full:{normalize_domain(raw_value)}")
        else:
            if HAPP_SUFFIX_ONLY_GEOSITE:
                data.drop("domain_keyword_not_supported_in_happ", f"{source}: {line}")
                return
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
        bucket.geo_tags.append(f"geoip:{normalize_geoip_tag(raw_value)}")
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


def overlay_roscom_geosite_data(geosite_data_dir: Path, roscom_data_dir: Path) -> None:
    geosite_data_dir.mkdir(parents=True, exist_ok=True)
    for existing in geosite_data_dir.iterdir():
        if existing.is_file():
            existing.unlink()
    for src in sorted(roscom_data_dir.iterdir()):
        if src.is_file():
            shutil.copy2(src, geosite_data_dir / src.name)


def build_geosite_dat(out_dir: Path, data: BuildData, output_name: str = BONUS_GEOSITE_FILENAME) -> Path:
    with tempfile.TemporaryDirectory(prefix="sr-happ-geosite-") as tmp_dir:
        tmp = Path(tmp_dir)
        repo = tmp / "domain-list-community-compiler"
        roscom_repo = tmp / "roscomvpn-geosite"
        data_dir = tmp / "data"
        run_with_retry(["git", "clone", "--depth", "1", GEOSITE_COMPILER_REPO, str(repo)])
        run_with_retry(
            [
                "git",
                "clone",
                "--depth",
                "1",
                "--branch",
                ROSCOM_GEOSITE_TAG,
                ROSCOM_GEOSITE_SOURCE_REPO,
                str(roscom_repo),
            ]
        )
        overlay_roscom_geosite_data(data_dir, roscom_repo / "data")
        write_geosite_inputs(data_dir, data)
        run_with_retry(["go", "mod", "download"], cwd=repo)
        run(["go", "run", "./", f"--datapath={data_dir}", f"--outputname={output_name}"], cwd=repo)
        candidates = [repo / output_name, repo / "output" / "dat" / output_name, repo / "dlc.dat", repo / "output" / "dat" / "dlc.dat"]
        source = next((path for path in candidates if path.exists()), None)
        if source is None:
            raise RuntimeError("Failed to build geosite.dat: dlc.dat not found")
        target = out_dir / output_name
        target.write_bytes(source.read_bytes())
        return target


def fetch_to_file(url: str, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    run_with_retry(
        ["curl", "-fsSL", "--retry", "5", "--retry-delay", "2", "--retry-connrefused", "-o", str(dest), url],
        attempts=3,
        delay_seconds=3.0,
    )


def write_geoip_bonus_config(geoip_repo: Path, data: BuildData) -> Path:
    lists_dir = geoip_repo / "custom-lists"
    lists_dir.mkdir(parents=True, exist_ok=True)

    def write_list(name: str, values: list[str]) -> Path:
        path = lists_dir / f"{name}.txt"
        path.write_text("\n".join(values) + ("\n" if values else ""), encoding="utf-8")
        return path

    direct_file = write_list("sr-direct", data.direct.cidrs)
    proxy_file = write_list("sr-proxy", data.proxy.cidrs)
    block_file = write_list("sr-block", data.block.cidrs)
    wanted_lists = dedupe_preserve(
        ["private", "direct", "sr-direct", "sr-proxy"]
        + (["sr-block"] if data.block.cidrs or data.block.geo_tags else [])
        + [tag.split(":", 1)[1] for tag in data.direct.geo_tags if tag.startswith("geoip:")]
        + [tag.split(":", 1)[1] for tag in data.proxy.geo_tags if tag.startswith("geoip:")]
        + [tag.split(":", 1)[1] for tag in data.block.geo_tags if tag.startswith("geoip:")]
    )

    config = json.loads((geoip_repo / "config.json").read_text(encoding="utf-8"))
    if "input" not in config or not isinstance(config["input"], list):
        raise RuntimeError("Unexpected hydraponique config.json format: missing input[]")
    if "output" not in config or not isinstance(config["output"], list) or not config["output"]:
        raise RuntimeError("Unexpected hydraponique config.json format: missing output[]")

    config["input"].append(
        {
            "type": "text",
            "action": "add",
            "args": {"name": "sr-direct", "uri": str(direct_file)},
        }
    )
    config["input"].append(
        {
            "type": "text",
            "action": "add",
            "args": {"name": "sr-proxy", "uri": str(proxy_file)},
        }
    )
    if data.block.cidrs:
        config["input"].append(
            {
                "type": "text",
                "action": "add",
                "args": {"name": "sr-block", "uri": str(block_file)},
            }
        )

    output_args = config["output"][0].setdefault("args", {})
    output_args["outputDir"] = str(geoip_repo / "output" / "dat")
    output_args["outputName"] = BONUS_GEOIP_FILENAME
    output_args["wantedList"] = wanted_lists

    config_path = geoip_repo / "config.bonus.json"
    config_path.write_text(json.dumps(config, indent=2), encoding="utf-8")
    return config_path


def write_release_direct_fallback_config(geoip_repo: Path) -> None:
    inputs: list[dict[str, object]] = [
        {
            "type": "text",
            "action": "add",
            "args": {
                "name": "direct",
                "uri": "./fallback-direct.txt",
                "onlyIPType": "ipv4",
            },
        },
        {
            "type": "text",
            "action": "add",
            "args": {
                "name": "whitelist",
                "uri": "./whitelist.txt",
                "onlyIPType": "ipv4",
            },
        },
        {
            "type": "private",
            "action": "add",
        },
        {
            "type": "text",
            "action": "remove",
            "args": {
                "name": "private",
                "ipOrCIDR": ["0.0.0.0/8", "::/128"],
            },
        },
    ]
    custom_whitelist = geoip_repo / "CUSTOM-WHITELIST.txt"
    if custom_whitelist.exists():
        inputs.insert(
            2,
            {
                "type": "text",
                "action": "add",
                "args": {
                    "name": "whitelist",
                    "uri": "./CUSTOM-WHITELIST.txt",
                },
            },
        )

    fallback_config = {
        "input": inputs,
        "output": [
            {
                "type": "v2rayGeoIPDat",
                "action": "output",
                "args": {
                    "outputName": "geoip.dat",
                },
            },
            {
                "type": "text",
                "action": "output",
            },
        ],
    }
    (geoip_repo / "config.json").write_text(json.dumps(fallback_config, indent=2), encoding="utf-8")


def sync_hydra_text_inputs(geoip_repo: Path, hydra_repo: Path) -> None:
    config = json.loads((geoip_repo / "config.json").read_text(encoding="utf-8"))
    inputs = config.get("input", [])
    if not isinstance(inputs, list):
        raise RuntimeError("Unexpected hydraponique config.json format: missing input[]")

    fallback_reasons: list[str] = []

    for item in inputs:
        if not isinstance(item, dict) or item.get("type") != "text":
            continue
        args = item.get("args", {})
        if not isinstance(args, dict):
            continue
        uri = args.get("uri")
        if not isinstance(uri, str) or not uri.startswith("./"):
            continue

        relative = Path(uri.removeprefix("./"))
        if relative.is_absolute():
            continue

        dest = geoip_repo / relative
        if dest.exists():
            continue

        candidates = (
            hydra_repo / relative,
            hydra_repo / relative.name,
            hydra_repo / "release" / "text" / relative.name,
        )
        source = next((path for path in candidates if path.exists()), None)
        if source is not None:
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, dest)
            continue

        source_url = HYDRA_GEOIP_EXTERNAL_SOURCES.get(relative.name)
        if source_url is not None:
            try:
                fetch_to_file(source_url, dest)
            except RuntimeError as exc:
                fallback_reasons.append(str(exc))
            continue

        if relative.name.startswith("CUSTOM-"):
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_text("", encoding="utf-8")
            continue

        if relative == Path("tmp/text/final.txt"):
            fallback_reasons.append("Upstream config requires tmp/text/final.txt but no generator is present.")
            continue

        raise RuntimeError(f"Missing required hydraponique file referenced by config.json: {relative}")

    if not fallback_reasons:
        return

    fallback_direct = hydra_repo / "release" / "text" / "direct.txt"
    if not fallback_direct.exists():
        raise RuntimeError(
            "Failed to prepare live geoip inputs and fallback release/text/direct.txt is missing"
        )
    shutil.copy2(fallback_direct, geoip_repo / "fallback-direct.txt")
    write_release_direct_fallback_config(geoip_repo)
    print(
        "Warning: using fallback release/text/direct.txt for geoip input because live inputs are unavailable.\n"
        + "\n".join(fallback_reasons),
        file=sys.stderr,
    )


def prepare_hydra_geoip_inputs(geoip_repo: Path, hydra_repo: Path) -> None:
    for name in ("config.json",):
        source = hydra_repo / name
        if not source.exists():
            raise RuntimeError(f"Missing required hydraponique file: {name}")
        shutil.copy2(source, geoip_repo / name)
    sync_hydra_text_inputs(geoip_repo, hydra_repo)


def build_geoip_dat(out_dir: Path, data: BuildData, output_name: str = BONUS_GEOIP_FILENAME) -> Path:
    with tempfile.TemporaryDirectory(prefix="sr-happ-geoip-") as tmp_dir:
        tmp = Path(tmp_dir)
        geoip_repo = tmp / "geoip"
        hydra_repo = tmp / "roscomvpn-geoip"
        run_with_retry(["git", "clone", "--depth", "1", "https://github.com/v2fly/geoip.git", str(geoip_repo)])
        run_with_retry(["git", "clone", "--depth", "1", ROSCOM_GEOIP_SOURCE_REPO, str(hydra_repo)])
        run_with_retry(["go", "mod", "download"], cwd=geoip_repo)
        run(["go", "build", "-o", "geoip"], cwd=geoip_repo)
        prepare_hydra_geoip_inputs(geoip_repo, hydra_repo)
        config_path = write_geoip_bonus_config(geoip_repo, data)
        run(["./geoip", "-c", str(config_path)], cwd=geoip_repo)
        source = geoip_repo / "output" / "dat" / output_name
        if not source.exists():
            raise RuntimeError(f"Failed to build {output_name}: output/dat/{output_name} not found")
        target = out_dir / output_name
        target.write_bytes(source.read_bytes())
        return target


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


def commit_sha(repo_root: Path) -> str:
    return run(["git", "-C", str(repo_root), "rev-parse", "HEAD"])


def fetch_roscom_profile_payload() -> str:
    return run_with_retry(
        ["curl", "-fsSL", "--retry", "5", "--retry-delay", "2", "--retry-connrefused", ROSCOM_DEFAULT_PROFILE_URL],
        attempts=3,
        delay_seconds=3.0,
    )


def parse_json_object(payload: str) -> dict[str, object]:
    profile = json.loads(payload)
    if not isinstance(profile, dict):
        raise RuntimeError("Unexpected roscom profile payload: expected JSON object")
    return profile


def build_profile(
    data: BuildData,
    raw_base: str,
    route_order: str,
    remote_dns_ip: str,
    remote_dns_domain: str,
    domestic_dns_ip: str,
    remote_dns_type: str,
    domestic_dns_type: str,
    general_direct_ips: list[str],
    geoip_filename: str = BONUS_GEOIP_FILENAME,
    geosite_filename: str = BONUS_GEOSITE_FILENAME,
) -> dict[str, object]:
    direct_geo = dedupe_preserve(data.direct.geo_tags)
    proxy_geo = dedupe_preserve(data.proxy.geo_tags)
    block_geo = dedupe_preserve(data.block.geo_tags)

    direct_ip = dedupe_preserve(
        ["geoip:private", "geoip:direct", "geoip:sr-direct"] + general_direct_ips + direct_geo
    )
    proxy_ip = dedupe_preserve(["geoip:sr-proxy"] + proxy_geo)
    block_ip = dedupe_preserve((["geoip:sr-block"] if data.block.cidrs else []) + block_geo)
    direct_sites = dedupe_preserve(["geosite:private", "geosite:sr-direct"] + DEFAULT_EXTRA_DIRECT_SITES)
    proxy_sites = dedupe_preserve(["geosite:sr-proxy"] + DEFAULT_EXTRA_PROXY_SITES)
    block_sites = dedupe_preserve(
        (["geosite:sr-block"] if data.block.site_rules else []) + DEFAULT_EXTRA_BLOCK_SITES
    )

    profile = {
        "Name": "ShadowRocket-HAPP",
        "GlobalProxy": "true",
        "UseChunkFiles": "false",
        "RemoteDns": remote_dns_ip,
        "DomesticDns": domestic_dns_ip,
        "RemoteDNSType": remote_dns_type,
        "RemoteDNSDomain": remote_dns_domain,
        "RemoteDNSIP": remote_dns_ip,
        "DomesticDNSType": domestic_dns_type,
        "DomesticDNSDomain": "",
        "DomesticDNSIP": domestic_dns_ip,
        "Geoipurl": f"{raw_base}/{geoip_filename}",
        "Geositeurl": f"{raw_base}/{geosite_filename}",
        "LastUpdated": str(int(time.time())),
        "DnsHosts": DEFAULT_DNS_HOSTS,
        "RouteOrder": route_order,
        "DirectSites": direct_sites,
        "DirectIp": direct_ip,
        "ProxySites": proxy_sites,
        "ProxyIp": proxy_ip,
        "BlockSites": block_sites,
        "BlockIp": block_ip if data.block.cidrs or block_geo else [],
        "DomainStrategy": "IPIfNonMatch",
        "FakeDNS": "true",
    }
    return profile


def profile_to_deeplink(profile: dict[str, object], mode: str) -> tuple[str, str, str]:
    json_pretty = json.dumps(profile, indent=2, ensure_ascii=False)
    json_compact = json.dumps(profile, separators=(",", ":"), ensure_ascii=False)
    encoded = base64.b64encode(json_compact.encode("utf-8")).decode("ascii")
    deeplink = f"happ://routing/{mode}/{encoded}"
    return json_pretty, json_compact, deeplink


def write_report(
    out_path: Path,
    conf_path: Path,
    data: BuildData,
    json_length: int,
    deeplink_length: int,
    sha: str,
    mode: str,
    profile: dict[str, object],
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

    # Pack 1 (default): pure roscom profile, copied as-is from upstream JSON.
    default_payload = fetch_roscom_profile_payload()
    default_profile = parse_json_object(default_payload)
    _, _, default_deeplink = profile_to_deeplink(default_profile, args.deeplink_mode)
    (out_dir / "DEFAULT.JSON").write_text(default_payload if default_payload.endswith("\n") else default_payload + "\n", encoding="utf-8")
    (out_dir / "DEFAULT.DEEPLINK").write_text(default_deeplink + "\n", encoding="utf-8")

    # Pack 2 (bonus): local augmentation based on shadowrocket.conf + rules/*.list.
    remote_dns_ip = args.remote_dns_ip
    if "--remote-dns-ip" not in sys.argv:
        remote_dns_ip = extract_remote_dns_ip(conf_path) or args.remote_dns_ip
    general_direct_ips = dedupe_preserve(
        extract_skip_proxy_ips(conf_path) + extract_bypass_tun_ips(conf_path)
    )
    data = parse_conf_and_lists(conf_path, rules_dir)
    ensure_bucket_uniques(data)
    build_geosite_dat(out_dir, data, BONUS_GEOSITE_FILENAME)
    build_geoip_dat(out_dir, data, BONUS_GEOIP_FILENAME)
    slug = repo_slug(repo_root)
    raw_base = f"https://raw.githubusercontent.com/{slug}/main/{args.out_dir.strip('/')}"
    bonus_profile = build_profile(
        data=data,
        raw_base=raw_base,
        route_order=args.route_order,
        remote_dns_ip=remote_dns_ip,
        remote_dns_domain=args.remote_dns_domain,
        domestic_dns_ip=args.domestic_dns_ip,
        remote_dns_type=args.remote_dns_type,
        domestic_dns_type=args.domestic_dns_type,
        general_direct_ips=general_direct_ips,
        geoip_filename=BONUS_GEOIP_FILENAME,
        geosite_filename=BONUS_GEOSITE_FILENAME,
    )
    bonus_profile["Name"] = BONUS_PROFILE_NAME
    bonus_pretty, bonus_compact, bonus_deeplink = profile_to_deeplink(bonus_profile, args.deeplink_mode)
    (out_dir / "BONUS.JSON").write_text(bonus_pretty + "\n", encoding="utf-8")
    (out_dir / "BONUS.DEEPLINK").write_text(bonus_deeplink + "\n", encoding="utf-8")

    write_report(
        out_path=out_dir / "REPORT.md",
        conf_path=conf_path,
        data=data,
        json_length=len(bonus_compact),
        deeplink_length=len(bonus_deeplink),
        sha=commit_sha(repo_root),
        mode=args.deeplink_mode,
        profile=bonus_profile,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
