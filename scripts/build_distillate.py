#!/usr/bin/env python3
"""Build manifest-driven distillate artifacts from BM7 Clash lists."""

from __future__ import annotations

import argparse
import ipaddress
import json
import math
import shlex
import shutil
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from urllib.request import Request, urlopen


SUPPORTED_DOMAIN_RULES = {"DOMAIN", "DOMAIN-SUFFIX", "DOMAIN-KEYWORD"}
SUPPORTED_IP_RULES = {"IP-CIDR", "IP-CIDR6"}
IGNORED_RULE_TYPES = {
    "PROCESS-NAME",
    "USER-AGENT",
    "SRC-IP-CIDR",
    "SRC-PORT",
    "DST-PORT",
    "URL-REGEX",
    "AND",
    "OR",
    "NOT",
}
MANIFEST_PATH = Path("distillate/manifest.json")
TEXT_DIR = Path("distillate/text")
DAT_DIR = Path("distillate/dat")
SUMMARY_PATH = Path("distillate/summary.json")
UPSTREAM_DIR = Path("distillate/upstream")
OBSOLETE_COMPILED_DIRS = (Path("distillate/mihomo"), Path("distillate/sing-box"))
GEOIP_REPO = "https://github.com/v2fly/geoip.git"
GEOSITE_REPO = "https://github.com/v2fly/domain-list-community.git"
RULE_HEADER = "# Generated from distillate/manifest.json"
FETCH_USER_AGENT = "ShadowRocketDistillate/1.0"
ANTI_ADVERTISING_MAX_CHUNK_BYTES = 7 * 1024 * 1024
ANTI_AD_RULE_GLOB = "anti_advertising.[0-9][0-9].list"
ANTI_AD_RULE_PREFIX = "RULE-SET, https://raw.githubusercontent.com/Simonerrror/ShadowRocket/main/rules/"


@dataclass
class CategoryResult:
    name: str
    domain_rules: list[str] = field(default_factory=list)
    ip_cidrs: list[str] = field(default_factory=list)
    ip_asns: list[str] = field(default_factory=list)
    dropped: dict[str, int] = field(default_factory=dict)


class DistillateError(RuntimeError):
    pass


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build distillate artifacts from BM7 manifest.")
    parser.add_argument("--manifest", default=str(MANIFEST_PATH), help="Path to manifest JSON")
    parser.add_argument(
        "--skip-compiled",
        action="store_true",
        help="Skip .dat compilation and only refresh canonical text + legacy rules.",
    )
    return parser.parse_args()


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
        raise DistillateError(f"Command failed: {shlex.join(cmd)}\n{detail}")
    return result.stdout.strip()


def run_with_retry(
    cmd: list[str],
    cwd: Path | None = None,
    attempts: int = 3,
    delay_seconds: float = 2.0,
) -> str:
    last_error: DistillateError | None = None
    for attempt in range(1, attempts + 1):
        try:
            return run(cmd, cwd=cwd)
        except DistillateError as exc:
            last_error = exc
            if attempt == attempts:
                break
            time.sleep(delay_seconds * attempt)
    assert last_error is not None
    raise last_error


def fetch_text(url: str, attempts: int = 3) -> str:
    last_error: Exception | None = None
    request = Request(url, headers={"User-Agent": FETCH_USER_AGENT})
    for attempt in range(1, attempts + 1):
        try:
            with urlopen(request, timeout=30) as response:
                return response.read().decode("utf-8")
        except Exception as exc:  # noqa: BLE001
            last_error = exc
            try:
                return run_with_retry(
                    [
                        "curl",
                        "-fsSL",
                        "--retry",
                        "5",
                        "--retry-delay",
                        "2",
                        "--retry-connrefused",
                        "-A",
                        FETCH_USER_AGENT,
                        url,
                    ],
                    attempts=2,
                    delay_seconds=2.0,
                )
            except DistillateError as curl_exc:
                last_error = curl_exc
            if attempt == attempts:
                break
            time.sleep(2.0 * attempt)
    raise DistillateError(f"Failed to fetch {url}: {last_error}")


def load_manifest(path: Path) -> dict[str, Any]:
    manifest = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(manifest, dict):
        raise DistillateError("Manifest must be a JSON object")
    categories = manifest.get("categories")
    if not isinstance(categories, list) or not categories:
        raise DistillateError("Manifest categories[] is required")
    return manifest


def manifest_upstream_dir(repo_root: Path, manifest: dict[str, Any]) -> Path:
    value = manifest.get("upstream_dir", str(UPSTREAM_DIR))
    if not isinstance(value, str) or not value:
        raise DistillateError("Manifest upstream_dir must be a non-empty string")
    return repo_root / value


def source_remote_url(manifest: dict[str, Any], source: dict[str, Any]) -> str:
    source_type = source.get("type")
    if source_type == "bm7":
        pack = source.get("pack")
        base_url = manifest.get("bm7_base_url")
        if not isinstance(pack, str) or not isinstance(base_url, str) or not base_url:
            raise DistillateError("bm7 source requires pack and bm7_base_url")
        return f"{base_url}/{pack}/{pack}.list"
    if source_type == "url":
        url = source.get("url")
        if not isinstance(url, str) or not url:
            raise DistillateError("url source requires url")
        return url
    raise DistillateError(f"Unsupported remote source type: {source_type!r}")


def source_cache_path(repo_root: Path, manifest: dict[str, Any], source: dict[str, Any]) -> Path:
    source_type = source.get("type")
    if source_type == "bm7":
        pack = source.get("pack")
        if not isinstance(pack, str) or not pack:
            raise DistillateError("bm7 source requires pack")
        return manifest_upstream_dir(repo_root, manifest) / "bm7" / f"{pack}.list"
    if source_type == "url":
        cache_path = source.get("cache_path")
        if not isinstance(cache_path, str) or not cache_path:
            raise DistillateError("url source requires cache_path")
        return repo_root / cache_path
    raise DistillateError(f"Unsupported cache source type: {source_type!r}")


def iter_external_sources(repo_root: Path, manifest: dict[str, Any]) -> list[dict[str, str]]:
    seen: set[tuple[str, str]] = set()
    targets: list[dict[str, str]] = []
    for spec in manifest.get("categories", []):
        if not isinstance(spec, dict):
            continue
        for source in spec.get("sources", []):
            if not isinstance(source, dict):
                continue
            if source.get("type") not in {"bm7", "url"}:
                continue
            cache_path = source_cache_path(repo_root, manifest, source)
            url = source_remote_url(manifest, source)
            key = (str(cache_path), url)
            if key in seen:
                continue
            seen.add(key)
            label = source.get("pack") if source.get("type") == "bm7" else url
            targets.append({"cache_path": str(cache_path), "url": url, "label": str(label)})
    return targets


def read_cached_source(repo_root: Path, manifest: dict[str, Any], source: dict[str, Any], label: str) -> str:
    cache_path = source_cache_path(repo_root, manifest, source)
    if not cache_path.exists():
        raise DistillateError(
            f"Cached source is missing for {label}: {cache_path}. Run scripts/sync_lists.py to refresh vendored upstream lists."
        )
    return cache_path.read_text(encoding="utf-8")


def dedupe_preserve(items: list[str]) -> list[str]:
    seen: set[str] = set()
    output: list[str] = []
    for item in items:
        if item in seen:
            continue
        seen.add(item)
        output.append(item)
    return output


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


def normalize_keyword(value: str) -> str:
    return value.strip().strip(".")


def normalize_cidr(value: str) -> str:
    return str(ipaddress.ip_network(value.strip(), strict=False))


def normalize_asn(value: str) -> str:
    cleaned = value.strip().upper()
    if cleaned.startswith("AS"):
        cleaned = cleaned[2:]
    if not cleaned.isdigit():
        raise ValueError(f"Invalid ASN: {value}")
    return f"AS{cleaned}"


def clean_input_lines(raw_text: str) -> list[str]:
    lines: list[str] = []
    for raw in raw_text.splitlines():
        stripped = raw.strip().lstrip("\ufeff")
        if not stripped or stripped.startswith(("#", "!", ";", "[", "//")):
            continue
        lines.append(stripped)
    return lines


def canonicalize_rule_lines(lines: list[str], retain_ip_asn: bool, source: str) -> tuple[list[str], list[str], list[str], dict[str, int]]:
    domain_rules: list[str] = []
    ip_cidrs: list[str] = []
    ip_asns: list[str] = []
    dropped: dict[str, int] = {}

    def note(reason: str) -> None:
        dropped[reason] = dropped.get(reason, 0) + 1

    for line in lines:
        parts = [part.strip() for part in line.split(",")]
        if len(parts) < 2:
            note("invalid_rule")
            continue
        rule_type = parts[0].upper()
        raw_value = parts[1]

        if rule_type in SUPPORTED_DOMAIN_RULES:
            if not raw_value:
                note("invalid_domain")
                continue
            if rule_type == "DOMAIN":
                value = normalize_domain(raw_value)
                domain_rules.append(f"full:{value}")
            elif rule_type == "DOMAIN-SUFFIX":
                value = normalize_domain(raw_value)
                domain_rules.append(f"domain:{value}")
            else:
                value = normalize_keyword(raw_value)
                if not value:
                    note("invalid_keyword")
                    continue
                domain_rules.append(f"keyword:{value}")
            continue

        if rule_type in SUPPORTED_IP_RULES:
            if not raw_value:
                note("invalid_ip")
                continue
            try:
                ip_cidrs.append(normalize_cidr(raw_value))
            except ValueError:
                note("invalid_cidr")
            continue

        if rule_type == "IP-ASN":
            if not retain_ip_asn:
                note("ignored_ip_asn")
                continue
            try:
                ip_asns.append(normalize_asn(raw_value))
            except ValueError:
                note("invalid_ip_asn")
            continue

        if rule_type in IGNORED_RULE_TYPES:
            note(f"ignored_{rule_type.lower().replace('-', '_')}")
            continue

        note(f"unsupported_{rule_type.lower().replace('-', '_')}")

    return (
        dedupe_preserve(domain_rules),
        dedupe_preserve(ip_cidrs),
        dedupe_preserve(ip_asns),
        dropped,
    )


def parse_source_payload(raw_text: str, source_format: str, retain_ip_asn: bool, source: str) -> tuple[list[str], list[str], list[str], dict[str, int]]:
    if source_format == "domain-lines":
        domain_rules = [f"domain:{normalize_domain(line)}" for line in clean_input_lines(raw_text)]
        return dedupe_preserve(domain_rules), [], [], {}
    if source_format in {"shadowrocket", "clash-list", "rules"}:
        return canonicalize_rule_lines(clean_input_lines(raw_text), retain_ip_asn=retain_ip_asn, source=source)
    raise DistillateError(f"Unsupported source format {source_format!r} for {source}")


def extend_result(target: CategoryResult, source_result: CategoryResult) -> None:
    target.domain_rules.extend(source_result.domain_rules)
    target.ip_cidrs.extend(source_result.ip_cidrs)
    target.ip_asns.extend(source_result.ip_asns)
    for reason, count in source_result.dropped.items():
        target.dropped[reason] = target.dropped.get(reason, 0) + count


def load_overlay(path: Path, retain_ip_asn: bool, label: str) -> CategoryResult:
    if not path.exists():
        return CategoryResult(name=label)
    domain_rules, ip_cidrs, ip_asns, dropped = parse_source_payload(
        path.read_text(encoding="utf-8"),
        source_format="rules",
        retain_ip_asn=retain_ip_asn,
        source=label,
    )
    return CategoryResult(
        name=label,
        domain_rules=domain_rules,
        ip_cidrs=ip_cidrs,
        ip_asns=ip_asns,
        dropped=dropped,
    )


def load_exact_filter(path: Path, label: str) -> tuple[set[str], set[str], set[str]]:
    if not path.exists():
        raise DistillateError(f"Exact filter file is missing for {label}: {path}")
    domains: set[str] = set()
    cidrs: set[str] = set()
    asns: set[str] = set()
    for line in clean_input_lines(path.read_text(encoding="utf-8")):
        if line.startswith(("full:", "domain:", "keyword:")):
            domains.add(line)
            continue
        if "/" in line:
            cidrs.add(normalize_cidr(line))
            continue
        if line.upper().startswith("AS") or line.isdigit():
            asns.add(normalize_asn(line))
            continue
        raise DistillateError(f"Unsupported exact filter line in {label}: {line}")
    return domains, cidrs, asns


def apply_exact_filter(
    domain_rules: list[str],
    ip_cidrs: list[str],
    ip_asns: list[str],
    filter_path: Path,
    label: str,
) -> tuple[list[str], list[str], list[str]]:
    exact_domains, exact_cidrs, exact_asns = load_exact_filter(filter_path, label)
    return (
        [rule for rule in domain_rules if rule in exact_domains],
        [rule for rule in ip_cidrs if rule in exact_cidrs],
        [rule for rule in ip_asns if rule in exact_asns],
    )


def domain_rule_value(rule: str) -> str:
    if ":" not in rule:
        raise DistillateError(f"Unsupported canonical domain rule: {rule}")
    return rule.split(":", 1)[1]


def apply_domain_substring_excludes(domain_rules: list[str], substrings: list[str]) -> list[str]:
    normalized = [item.strip().lower() for item in substrings if item.strip()]
    if not normalized:
        return domain_rules
    filtered: list[str] = []
    for rule in domain_rules:
        value = domain_rule_value(rule).lower()
        if any(token in value for token in normalized):
            continue
        filtered.append(rule)
    return filtered


def apply_domain_suffix_excludes(domain_rules: list[str], suffixes: list[str]) -> list[str]:
    normalized = [item.strip().lower().strip(".") for item in suffixes if item.strip()]
    if not normalized:
        return domain_rules
    filtered: list[str] = []
    for rule in domain_rules:
        value = domain_rule_value(rule).lower().strip(".")
        if any(value == suffix or value.endswith(f".{suffix}") for suffix in normalized):
            continue
        filtered.append(rule)
    return filtered


def build_categories(manifest: dict[str, Any], repo_root: Path) -> tuple[dict[str, dict[str, Any]], dict[str, CategoryResult]]:
    specs = manifest["categories"]
    spec_by_name: dict[str, dict[str, Any]] = {}
    for spec in specs:
        if not isinstance(spec, dict) or not isinstance(spec.get("name"), str):
            raise DistillateError("Each category must be an object with a string name")
        name = spec["name"]
        if name in spec_by_name:
            raise DistillateError(f"Duplicate category name: {name}")
        spec_by_name[name] = spec

    cache: dict[str, CategoryResult] = {}
    def compose(name: str) -> CategoryResult:
        if name in cache:
            cached = cache[name]
            return CategoryResult(
                name=cached.name,
                domain_rules=list(cached.domain_rules),
                ip_cidrs=list(cached.ip_cidrs),
                ip_asns=list(cached.ip_asns),
                dropped=dict(cached.dropped),
            )

        spec = spec_by_name.get(name)
        if spec is None:
            raise DistillateError(f"Unknown category reference: {name}")

        retain_ip_asn = bool(spec.get("retain_ip_asn", False))
        result = CategoryResult(name=name)
        for source in spec.get("sources", []):
            if not isinstance(source, dict):
                raise DistillateError(f"Invalid source in category {name}")
            source_type = source.get("type")
            if source_type == "category":
                child_name = source.get("name")
                if not isinstance(child_name, str):
                    raise DistillateError(f"category source requires name in {name}")
                extend_result(result, compose(child_name))
                continue
            if source_type == "bm7":
                pack = source.get("pack")
                if not isinstance(pack, str):
                    raise DistillateError(f"bm7 source requires pack in {name}")
                payload = read_cached_source(repo_root, manifest, source, f"{name}:{pack}")
                parsed = parse_source_payload(payload, "clash-list", retain_ip_asn, f"{name}:{pack}")
            elif source_type == "url":
                url = source.get("url")
                source_format = source.get("format", "shadowrocket")
                if not isinstance(url, str):
                    raise DistillateError(f"url source requires url in {name}")
                payload = read_cached_source(repo_root, manifest, source, f"{name}:{url}")
                parsed = parse_source_payload(payload, str(source_format), retain_ip_asn, f"{name}:{url}")
            else:
                raise DistillateError(f"Unsupported source type {source_type!r} in {name}")

            domain_rules, ip_cidrs, ip_asns, dropped = parsed
            include_exact = source.get("include_exact")
            if include_exact is not None:
                if not isinstance(include_exact, str) or not include_exact:
                    raise DistillateError(f"include_exact must be a non-empty string in {name}")
                domain_rules, ip_cidrs, ip_asns = apply_exact_filter(
                    domain_rules,
                    ip_cidrs,
                    ip_asns,
                    repo_root / include_exact,
                    f"{name}:{source_type}:include_exact",
                )
            result.domain_rules.extend(domain_rules)
            result.ip_cidrs.extend(ip_cidrs)
            result.ip_asns.extend(ip_asns)
            for reason, count in dropped.items():
                result.dropped[reason] = result.dropped.get(reason, 0) + count

        overlays = spec.get("overlays", {})
        if overlays:
            if not isinstance(overlays, dict):
                raise DistillateError(f"overlays must be an object in {name}")
            add_path_value = overlays.get("add")
            if isinstance(add_path_value, str):
                add_overlay = load_overlay(repo_root / add_path_value, retain_ip_asn, f"{name}:overlay:add")
                extend_result(result, add_overlay)
            remove_path_value = overlays.get("remove")
            if isinstance(remove_path_value, str):
                remove_overlay = load_overlay(repo_root / remove_path_value, retain_ip_asn, f"{name}:overlay:remove")
                remove_domains = set(remove_overlay.domain_rules)
                remove_ip_cidrs = set(remove_overlay.ip_cidrs)
                remove_ip_asns = set(remove_overlay.ip_asns)
                result.domain_rules = [rule for rule in result.domain_rules if rule not in remove_domains]
                result.ip_cidrs = [rule for rule in result.ip_cidrs if rule not in remove_ip_cidrs]
                result.ip_asns = [rule for rule in result.ip_asns if rule not in remove_ip_asns]
                for reason, count in remove_overlay.dropped.items():
                    result.dropped[reason] = result.dropped.get(reason, 0) + count

        exclude_domain_substrings = spec.get("exclude_domain_substrings")
        if exclude_domain_substrings is not None:
            if (
                not isinstance(exclude_domain_substrings, list)
                or not all(isinstance(item, str) for item in exclude_domain_substrings)
            ):
                raise DistillateError(f"exclude_domain_substrings must be an array of strings in {name}")
            result.domain_rules = apply_domain_substring_excludes(result.domain_rules, exclude_domain_substrings)

        exclude_domain_suffixes = spec.get("exclude_domain_suffixes")
        if exclude_domain_suffixes is not None:
            if (
                not isinstance(exclude_domain_suffixes, list)
                or not all(isinstance(item, str) for item in exclude_domain_suffixes)
            ):
                raise DistillateError(f"exclude_domain_suffixes must be an array of strings in {name}")
            result.domain_rules = apply_domain_suffix_excludes(result.domain_rules, exclude_domain_suffixes)

        result.domain_rules = dedupe_preserve(result.domain_rules)
        result.ip_cidrs = dedupe_preserve(result.ip_cidrs)
        result.ip_asns = dedupe_preserve(result.ip_asns)
        cache[name] = result
        return compose(name)

    results = {name: compose(name) for name in spec_by_name}
    return spec_by_name, results


def write_text_file(path: Path, lines: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    content = "\n".join(lines)
    if content:
        content += "\n"
    path.write_text(content, encoding="utf-8")


def canonical_domain_to_legacy(line: str) -> str:
    if line.startswith("full:"):
        return f"DOMAIN,{line[5:]}"
    if line.startswith("domain:"):
        return f"DOMAIN-SUFFIX,{line[7:]}"
    if line.startswith("keyword:"):
        return f"DOMAIN-KEYWORD,{line[8:]}"
    raise DistillateError(f"Unsupported canonical domain line: {line}")


def cidr_to_legacy(line: str) -> str:
    network = ipaddress.ip_network(line, strict=False)
    return f"IP-CIDR6,{network}" if network.version == 6 else f"IP-CIDR,{network}"


def asn_to_legacy(line: str) -> str:
    return f"IP-ASN,{line.removeprefix('AS')}"


def render_legacy_rules(path: Path, result: CategoryResult) -> None:
    lines = [RULE_HEADER]
    lines.extend(canonical_domain_to_legacy(rule) for rule in result.domain_rules)
    lines.extend(cidr_to_legacy(rule) for rule in result.ip_cidrs)
    lines.extend(asn_to_legacy(rule) for rule in result.ip_asns)
    write_text_file(path, lines)
    render_chunked_legacy_rules(path, lines)


def render_chunked_legacy_rules(path: Path, lines: list[str]) -> None:
    if path.name != "anti_advertising.list":
        return

    for stale_path in sorted(path.parent.glob("anti_advertising.[0-9][0-9].list")):
        stale_path.unlink(missing_ok=True)

    payload = lines[1:]
    if not payload:
        return

    weights = [len((line + "\n").encode("utf-8")) for line in payload]
    total_bytes = sum(weights)
    chunk_count = max(1, math.ceil(total_bytes / ANTI_ADVERTISING_MAX_CHUNK_BYTES))

    offset = 0
    remaining_bytes = total_bytes
    for chunk_index in range(1, chunk_count + 1):
        remaining_chunks = chunk_count - chunk_index + 1
        target_bytes = math.ceil(remaining_bytes / remaining_chunks)
        chunk_payload: list[str] = []
        chunk_bytes = 0

        while offset < len(payload):
            line = payload[offset]
            line_weight = weights[offset]
            if chunk_payload and chunk_bytes + line_weight > target_bytes:
                break
            chunk_payload.append(line)
            chunk_bytes += line_weight
            offset += 1
            if chunk_bytes >= target_bytes:
                break

        chunk_path = path.with_name(f"anti_advertising.{chunk_index:02d}.list")
        write_text_file(chunk_path, [RULE_HEADER, *chunk_payload])
        remaining_bytes -= chunk_bytes


def anti_ad_chunk_rule_lines(repo_root: Path) -> list[str]:
    chunk_paths = sorted((repo_root / "rules").glob(ANTI_AD_RULE_GLOB))
    return [f"{ANTI_AD_RULE_PREFIX}{path.name},REJECT" for path in chunk_paths]


def rewrite_module_chunks(module_path: Path, chunk_lines: list[str]) -> None:
    if not module_path.exists():
        return

    lines = module_path.read_text(encoding="utf-8").splitlines()
    kept_lines = [
        line
        for line in lines
        if "anti_advertising.list,REJECT" not in line and "anti_advertising." not in line
    ]
    if chunk_lines:
        if kept_lines and kept_lines[-1] != "":
            kept_lines.append("")
        kept_lines.extend(chunk_lines)
    module_path.write_text("\n".join(kept_lines) + "\n", encoding="utf-8")


def rewrite_anti_ad_modules(repo_root: Path) -> None:
    chunk_lines = anti_ad_chunk_rule_lines(repo_root)
    rewrite_module_chunks(repo_root / "modules" / "anti_advertising.module", chunk_lines)
    rewrite_module_chunks(repo_root / "modules" / "anti_advertising_custom.module", chunk_lines)


def prepare_output_dirs(repo_root: Path, skip_compiled: bool) -> None:
    text_root = repo_root / TEXT_DIR
    for subdir in (text_root / "domain", text_root / "ip"):
        if subdir.exists():
            shutil.rmtree(subdir)
        subdir.mkdir(parents=True, exist_ok=True)
    for obsolete_dir in OBSOLETE_COMPILED_DIRS:
        target = repo_root / obsolete_dir
        if target.exists():
            shutil.rmtree(target)
    if skip_compiled:
        return
    output_dir = repo_root / DAT_DIR
    if output_dir.exists():
        shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)


def write_text_outputs(
    repo_root: Path,
    spec_by_name: dict[str, dict[str, Any]],
    results: dict[str, CategoryResult],
) -> dict[str, CategoryResult]:
    published: dict[str, CategoryResult] = {}
    for name, spec in spec_by_name.items():
        if not spec.get("publish", False):
            continue
        result = results[name]
        published[name] = result
        write_text_file(repo_root / TEXT_DIR / "domain" / f"{name}.txt", result.domain_rules)
        write_text_file(repo_root / TEXT_DIR / "ip" / f"{name}.txt", result.ip_cidrs)
        legacy_rule_path = spec.get("legacy_rule_path")
        if isinstance(legacy_rule_path, str):
            render_legacy_rules(repo_root / legacy_rule_path, result)
    return published


def build_bucket_aggregates(
    repo_root: Path,
    spec_by_name: dict[str, dict[str, Any]],
    results: dict[str, CategoryResult],
) -> dict[str, CategoryResult]:
    aggregates: dict[str, CategoryResult] = {}
    for bucket in ("direct", "proxy", "block"):
        aggregate = CategoryResult(name=f"sr-{bucket}")
        for name, spec in spec_by_name.items():
            if spec.get("bucket") != bucket:
                continue
            extend_result(aggregate, results[name])
        aggregate.domain_rules = dedupe_preserve(aggregate.domain_rules)
        aggregate.ip_cidrs = dedupe_preserve(aggregate.ip_cidrs)
        aggregate.ip_asns = dedupe_preserve(aggregate.ip_asns)
        if not aggregate.domain_rules and not aggregate.ip_cidrs:
            continue
        aggregates[aggregate.name] = aggregate
        write_text_file(repo_root / TEXT_DIR / "domain" / f"{aggregate.name}.txt", aggregate.domain_rules)
        write_text_file(repo_root / TEXT_DIR / "ip" / f"{aggregate.name}.txt", aggregate.ip_cidrs)
    return aggregates


def compiled_categories(
    spec_by_name: dict[str, dict[str, Any]],
    published: dict[str, CategoryResult],
    aggregates: dict[str, CategoryResult],
) -> dict[str, CategoryResult]:
    compiled: dict[str, CategoryResult] = {}
    for name, result in published.items():
        spec = spec_by_name[name]
        if spec.get("compiled", True):
            compiled[name] = result
    compiled.update(aggregates)
    return compiled


def compile_geosite_dat(repo_root: Path, categories: dict[str, CategoryResult]) -> None:
    with tempfile.TemporaryDirectory(prefix="sr-distillate-geosite-") as tmp_dir:
        tmp = Path(tmp_dir)
        repo = tmp / "domain-list-community"
        data_dir = tmp / "data"
        out_dir = tmp / "out"
        data_dir.mkdir(parents=True, exist_ok=True)
        out_dir.mkdir(parents=True, exist_ok=True)
        for name, result in categories.items():
            if not result.domain_rules:
                continue
            write_text_file(data_dir / dat_category_name(name), result.domain_rules)
        run_with_retry(["git", "clone", "--depth", "1", GEOSITE_REPO, str(repo)])
        run_with_retry(["go", "mod", "download"], cwd=repo)
        run(["go", "run", "./", f"--datapath={data_dir}", f"--outputdir={out_dir}"], cwd=repo)
        source = out_dir / "dlc.dat"
        if not source.exists():
            raise DistillateError("Failed to build geosite.dat: output dlc.dat not found")
        shutil.copy2(source, repo_root / DAT_DIR / "geosite.dat")


def compile_geoip_dat(repo_root: Path, categories: dict[str, CategoryResult]) -> None:
    with tempfile.TemporaryDirectory(prefix="sr-distillate-geoip-") as tmp_dir:
        tmp = Path(tmp_dir)
        repo = tmp / "geoip"
        run_with_retry(["git", "clone", "--depth", "1", GEOIP_REPO, str(repo)])
        run_with_retry(["go", "mod", "download"], cwd=repo)
        run(["go", "build", "-o", "geoip"], cwd=repo)

        inputs: list[dict[str, Any]] = []
        wanted_lists: list[str] = []
        for name, result in categories.items():
            if not result.ip_cidrs:
                continue
            source = repo_root / TEXT_DIR / "ip" / f"{name}.txt"
            dat_name = dat_category_name(name)
            inputs.append(
                {
                    "type": "text",
                    "action": "add",
                    "args": {
                        "name": dat_name,
                        "uri": str(source),
                    },
                }
            )
            wanted_lists.append(dat_name)

        config = {
            "input": inputs,
            "output": [
                {
                    "type": "v2rayGeoIPDat",
                    "action": "output",
                    "args": {
                        "outputDir": str(repo / "output" / "dat"),
                        "outputName": "geoip.dat",
                        "wantedList": wanted_lists,
                    },
                }
            ],
        }
        config_path = repo / "config.distillate.json"
        config_path.write_text(json.dumps(config, indent=2), encoding="utf-8")
        run(["./geoip", "-c", str(config_path)], cwd=repo)
        source = repo / "output" / "dat" / "geoip.dat"
        if not source.exists():
            raise DistillateError("Failed to build geoip.dat: output/dat/geoip.dat not found")
        shutil.copy2(source, repo_root / DAT_DIR / "geoip.dat")


def write_summary(
    repo_root: Path,
    spec_by_name: dict[str, dict[str, Any]],
    published: dict[str, CategoryResult],
    aggregates: dict[str, CategoryResult],
) -> None:
    summary = {
        "published_categories": [
            {
                "name": name,
                "bucket": spec_by_name[name].get("bucket"),
                "legacy_rule_path": spec_by_name[name].get("legacy_rule_path"),
                "domains": len(result.domain_rules),
                "ip_cidrs": len(result.ip_cidrs),
                "ip_asns": len(result.ip_asns),
                "dropped": result.dropped,
            }
            for name, result in sorted(published.items())
        ],
        "aggregates": [
            {
                "name": name,
                "domains": len(result.domain_rules),
                "ip_cidrs": len(result.ip_cidrs),
            }
            for name, result in sorted(aggregates.items())
        ],
    }
    (repo_root / SUMMARY_PATH).write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def dat_category_name(name: str) -> str:
    return name.replace("_", "-")


def main() -> int:
    args = parse_args()
    repo_root = Path.cwd()
    manifest_path = (repo_root / args.manifest).resolve()
    if not manifest_path.exists():
        raise FileNotFoundError(f"Manifest not found: {manifest_path}")

    manifest = load_manifest(manifest_path)
    prepare_output_dirs(repo_root, skip_compiled=args.skip_compiled)
    spec_by_name, results = build_categories(manifest, repo_root)
    published = write_text_outputs(repo_root, spec_by_name, results)
    aggregates = build_bucket_aggregates(repo_root, spec_by_name, results)
    write_summary(repo_root, spec_by_name, published, aggregates)
    rewrite_anti_ad_modules(repo_root)

    if args.skip_compiled:
        return 0

    artifacts = compiled_categories(spec_by_name, published, aggregates)
    compile_geosite_dat(repo_root, artifacts)
    compile_geoip_dat(repo_root, artifacts)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
