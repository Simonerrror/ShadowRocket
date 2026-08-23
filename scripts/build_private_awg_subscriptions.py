#!/usr/bin/env python3
"""Build two private five-device Shadowrocket AWG2 subscription secrets."""

from __future__ import annotations

import argparse
import base64
import binascii
import configparser
import ipaddress
import json
import os
import re
import secrets
import tempfile
from pathlib import Path
from urllib.parse import parse_qs, quote, urlencode, urlsplit


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PRIMARY_DIR = REPO_ROOT / "private/awg/primary"
DEFAULT_SECONDARY_DIR = REPO_ROOT / "private/awg/secondary"
DEFAULT_OUTPUT = REPO_ROOT / "private/awg/worker-secrets.json"
DEFAULT_URLS_OUTPUT = REPO_ROOT / "private/awg/subscription-urls.txt"
EXPECTED_PROFILE_COUNT = 5
MAX_CONFIG_SIZE = 64 * 1024
MAX_SECRET_SIZE = 5 * 1024
PLACEHOLDER_RE = re.compile(
    r"\$(?:[A-Za-z_][A-Za-z0-9_]*|\{[A-Za-z_][A-Za-z0-9_]*\})"
)
PATH_RE = re.compile(r"/s/[A-Za-z0-9_-]{32,128}")
COUNTRY_CODE_RE = re.compile(r"(?:^|[_\-\s])([a-z]{2})(?:\s*\(\d+\))?$", re.IGNORECASE)
HEADER_RE = re.compile(r"(\d+)(?:-(\d+))?")
INSTRUCTION_TOKEN_RE = re.compile(
    r"<(?:b 0x(?:[0-9A-Fa-f]{2})+|(?:r|rc|rd) [0-9]+|t)>"
)

AWG2_FIELDS = (
    "Jc", "Jmin", "Jmax", "S1", "S2", "S3", "S4",
    "H1", "H2", "H3", "H4", "I1", "I2", "I3", "I4", "I5",
)
AWG3_FIELDS = ("HeaderProtectionKey", "ContentPaddingAddition")
REQUIRED_INTERFACE_FIELDS = ("Address", "DNS", "PrivateKey", *AWG2_FIELDS)
REQUIRED_PEER_FIELDS = (
    "PublicKey", "PresharedKey", "AllowedIPs", "Endpoint", "PersistentKeepalive",
)
COUNTRIES = {
    "at": ("🇦🇹", "Австрия"),
    "be": ("🇧🇪", "Бельгия"),
    "bg": ("🇧🇬", "Болгария"),
    "ch": ("🇨🇭", "Швейцария"),
    "cz": ("🇨🇿", "Чехия"),
    "de": ("🇩🇪", "Германия"),
    "es": ("🇪🇸", "Испания"),
    "fi": ("🇫🇮", "Финляндия"),
    "fr": ("🇫🇷", "Франция"),
    "gb": ("🇬🇧", "Великобритания"),
    "gr": ("🇬🇷", "Греция"),
    "hk": ("🇭🇰", "Гонконг"),
    "it": ("🇮🇹", "Италия"),
    "nl": ("🇳🇱", "Нидерланды"),
    "no": ("🇳🇴", "Норвегия"),
    "pl": ("🇵🇱", "Польша"),
    "ro": ("🇷🇴", "Румыния"),
    "rs": ("🇷🇸", "Сербия"),
    "se": ("🇸🇪", "Швеция"),
    "tr": ("🇹🇷", "Турция"),
    "us": ("🇺🇸", "США"),
}


class SubscriptionBuildError(ValueError):
    """Raised when private AWG input cannot produce a safe complete feed."""


def _required(section: configparser.SectionProxy, key: str, path: Path) -> str:
    value = section.get(key, "").strip()
    if not value:
        raise SubscriptionBuildError(f"{path.name}: missing {key}")
    if PLACEHOLDER_RE.search(value):
        raise SubscriptionBuildError(f"{path.name}: unresolved placeholder in {key}")
    return value


def _validate_key(value: str, field: str, path: Path) -> str:
    try:
        decoded = base64.b64decode(value, validate=True)
    except (binascii.Error, ValueError) as exc:
        raise SubscriptionBuildError(f"{path.name}: invalid {field}") from exc
    if len(decoded) != 32:
        raise SubscriptionBuildError(f"{path.name}: invalid {field} length")
    if base64.b64encode(decoded).decode("ascii") != value:
        raise SubscriptionBuildError(f"{path.name}: invalid {field} encoding")
    return value


def _validate_uint(
    value: str,
    field: str,
    path: Path,
    *,
    maximum: int = 2**32 - 1,
) -> int:
    if not value.isdecimal():
        raise SubscriptionBuildError(f"{path.name}: invalid {field}")
    number = int(value)
    if number > maximum:
        raise SubscriptionBuildError(f"{path.name}: invalid {field}")
    return number


def _validate_awg_fields(values: dict[str, str], path: Path) -> None:
    _validate_uint(values["Jc"], "Jc", path)
    jmin = _validate_uint(values["Jmin"], "Jmin", path)
    jmax = _validate_uint(values["Jmax"], "Jmax", path)
    if jmin > jmax:
        raise SubscriptionBuildError(f"{path.name}: invalid Jmin/Jmax range")
    for field in ("S1", "S2", "S3", "S4"):
        _validate_uint(values[field], field, path, maximum=65535)
    for field in ("H1", "H2", "H3", "H4"):
        match = HEADER_RE.fullmatch(values[field])
        if match is None:
            raise SubscriptionBuildError(f"{path.name}: invalid {field}")
        lower = int(match.group(1))
        upper = int(match.group(2) or match.group(1))
        if lower > upper or upper > 2**32 - 1:
            raise SubscriptionBuildError(f"{path.name}: invalid {field}")
    for field in ("I1", "I2", "I3", "I4", "I5"):
        value = values[field]
        tokens = INSTRUCTION_TOKEN_RE.findall(value)
        if not tokens or "".join(tokens) != value:
            raise SubscriptionBuildError(f"{path.name}: invalid {field}")
        for token in tokens:
            match = re.fullmatch(r"<(?:r|rc|rd) (\d+)>", token)
            if match is not None and int(match.group(1)) > 65535:
                raise SubscriptionBuildError(f"{path.name}: invalid {field}")


def _parse_endpoint(value: str, path: Path) -> tuple[str, int]:
    if value.startswith("["):
        closing = value.rfind("]")
        if closing < 0 or value[closing + 1:closing + 2] != ":":
            raise SubscriptionBuildError(f"{path.name}: invalid Endpoint")
        host = value[: closing + 1]
        port_text = value[closing + 2:]
    else:
        host, separator, port_text = value.rpartition(":")
        if not separator or not host:
            raise SubscriptionBuildError(f"{path.name}: invalid Endpoint")
    try:
        port = int(port_text)
    except ValueError as exc:
        raise SubscriptionBuildError(f"{path.name}: invalid Endpoint port") from exc
    if not 1 <= port <= 65535:
        raise SubscriptionBuildError(f"{path.name}: invalid Endpoint port")
    raw_host = host[1:-1] if host.startswith("[") and host.endswith("]") else host
    try:
        ipaddress.ip_address(raw_host)
    except ValueError:
        if (
            len(raw_host) > 253
            or any(not label or len(label) > 63 for label in raw_host.split("."))
            or any(
                re.fullmatch(r"[A-Za-z0-9](?:[A-Za-z0-9-]*[A-Za-z0-9])?", label)
                is None
                for label in raw_host.split(".")
            )
        ):
            raise SubscriptionBuildError(f"{path.name}: invalid Endpoint host")
    return host, port


def _country_title(path: Path) -> str:
    match = COUNTRY_CODE_RE.search(path.stem)
    if match is None or match.group(1).lower() not in COUNTRIES:
        raise SubscriptionBuildError(
            f"{path.name}: filename must end with a supported two-letter country code"
        )
    flag, country = COUNTRIES[match.group(1).lower()]
    return f"{flag} {country} AWG2"


def _read_profile(path: Path, title: str) -> tuple[str, str]:
    if path.stat().st_size > MAX_CONFIG_SIZE:
        raise SubscriptionBuildError(f"{path.name}: config exceeds 64 KiB")
    parser = configparser.ConfigParser(interpolation=None, strict=True)
    parser.optionxform = str
    try:
        with path.open("r", encoding="utf-8-sig") as handle:
            parser.read_file(handle)
    except (OSError, UnicodeError, configparser.Error) as exc:
        raise SubscriptionBuildError(f"{path.name}: invalid config") from exc
    if set(parser.sections()) != {"Interface", "Peer"}:
        raise SubscriptionBuildError(f"{path.name}: expected Interface and Peer sections")
    interface = parser["Interface"]
    peer = parser["Peer"]
    lower_interface_keys = {key.lower() for key in interface}
    if any(field.lower() in lower_interface_keys for field in AWG3_FIELDS):
        raise SubscriptionBuildError(f"{path.name}: AWG3 is not supported by Shadowrocket")
    values = {key: _required(interface, key, path) for key in REQUIRED_INTERFACE_FIELDS}
    peer_values = {key: _required(peer, key, path) for key in REQUIRED_PEER_FIELDS}
    _validate_awg_fields(values, path)
    private_key = _validate_key(values["PrivateKey"], "PrivateKey", path)
    _validate_key(peer_values["PublicKey"], "PublicKey", path)
    _validate_key(peer_values["PresharedKey"], "PresharedKey", path)
    try:
        for address in values["Address"].split(","):
            ipaddress.ip_interface(address.strip())
        for dns in values["DNS"].split(","):
            ipaddress.ip_address(dns.strip())
    except ValueError as exc:
        raise SubscriptionBuildError(f"{path.name}: invalid Address or DNS") from exc
    host, port = _parse_endpoint(peer_values["Endpoint"], path)
    try:
        for allowed_ip in peer_values["AllowedIPs"].split(","):
            ipaddress.ip_network(allowed_ip.strip(), strict=False)
    except ValueError as exc:
        raise SubscriptionBuildError(f"{path.name}: invalid AllowedIPs") from exc
    _validate_uint(
        peer_values["PersistentKeepalive"],
        "PersistentKeepalive",
        path,
        maximum=65535,
    )
    awg = {key.lower(): values[key] for key in AWG2_FIELDS}
    query = {
        "publicKey": peer_values["PublicKey"],
        "privateKey": private_key,
        "presharedKey": peer_values["PresharedKey"],
        "ip": values["Address"],
        "dns": values["DNS"],
        "keepalive": peer_values["PersistentKeepalive"],
        "obfs": "amneziawg",
        "obfsParam": json.dumps(awg, ensure_ascii=False, separators=(",", ":")),
    }
    mtu = interface.get("MTU", "").strip()
    if mtu:
        if PLACEHOLDER_RE.search(mtu):
            raise SubscriptionBuildError(f"{path.name}: invalid MTU")
        _validate_uint(mtu, "MTU", path, maximum=65535)
        query["mtu"] = mtu
    link = (
        f"wg://{host}:{port}?"
        f"{urlencode(query, quote_via=quote, safe='')}#{quote(title, safe='')}"
    )
    return link, private_key


def _build_links(directory: Path) -> tuple[list[str], set[str]]:
    if not directory.is_dir():
        raise SubscriptionBuildError(f"{directory}: input directory is missing")
    paths = sorted(directory.glob("*.conf"))
    if len(paths) != EXPECTED_PROFILE_COUNT:
        raise SubscriptionBuildError(f"{directory}: expected exactly 5 .conf files")
    links: list[str] = []
    private_keys: set[str] = set()
    title_counts: dict[str, int] = {}
    for path in paths:
        base_title = _country_title(path)
        title_counts[base_title] = title_counts.get(base_title, 0) + 1
        occurrence = title_counts[base_title]
        title = base_title if occurrence == 1 else (
            f"{base_title.removesuffix(' AWG2')} {occurrence} AWG2"
        )
        link, private_key = _read_profile(path, title)
        if private_key in private_keys:
            raise SubscriptionBuildError(f"{path.name}: duplicate device PrivateKey")
        links.append(link)
        private_keys.add(private_key)
    return links, private_keys


def _link_payload(prefix: str, links: list[str]) -> dict[str, str]:
    if len(links) != EXPECTED_PROFILE_COUNT:
        raise SubscriptionBuildError(f"{prefix.lower()} must contain exactly 5 links")
    payload: dict[str, str] = {}
    for index, link in enumerate(links, start=1):
        if len(link.encode("utf-8")) > MAX_SECRET_SIZE:
            raise SubscriptionBuildError(
                f"{prefix.lower()} link {index} exceeds Cloudflare's 5 KB secret limit"
            )
        payload[f"{prefix}_LINK_{index}"] = link
    return payload


def _new_path() -> str:
    return f"/s/{secrets.token_urlsafe(32)}"


def _path(existing_payload: dict[str, str], key: str) -> str:
    value = existing_payload.get(key)
    if value is None:
        return _new_path()
    if not isinstance(value, str) or PATH_RE.fullmatch(value) is None:
        raise SubscriptionBuildError(f"existing {key} is not a valid opaque path")
    return value


def build_secret_payload(
    primary_dir: Path,
    secondary_dir: Path,
    *,
    existing_payload: dict[str, str] | None = None,
) -> dict[str, str]:
    existing = existing_payload or {}
    primary_links, primary_keys = _build_links(primary_dir)
    secondary_links, secondary_keys = _build_links(secondary_dir)
    if duplicate_keys := primary_keys & secondary_keys:
        raise SubscriptionBuildError(
            f"duplicate device PrivateKey across owners ({len(duplicate_keys)} found)"
        )
    primary_path = _path(existing, "PRIMARY_PATH")
    secondary_path = _path(existing, "SECONDARY_PATH")
    if primary_path == secondary_path:
        raise SubscriptionBuildError("primary and secondary bearer paths must differ")
    return {
        "PRIMARY_PATH": primary_path,
        "SECONDARY_PATH": secondary_path,
        **_link_payload("PRIMARY", primary_links),
        **_link_payload("SECONDARY", secondary_links),
    }


def _existing_links(payload: dict[str, str], prefix: str) -> list[str]:
    links = [payload.get(f"{prefix}_LINK_{index}") for index in range(1, 6)]
    if any(not isinstance(link, str) for link in links):
        raise SubscriptionBuildError(f"existing {prefix.lower()} links are invalid")
    return links


def _private_keys_from_links(links: list[str], owner: str) -> set[str]:
    private_keys: set[str] = set()
    for line in links:
        parsed = urlsplit(line)
        query = parse_qs(parsed.query, strict_parsing=True)
        values = query.get("privateKey", [])
        if parsed.scheme != "wg" or len(values) != 1:
            raise SubscriptionBuildError(f"existing {owner} links are invalid")
        private_keys.add(_validate_key(values[0], "privateKey", Path(f"{owner}-feed")))
    if len(private_keys) != EXPECTED_PROFILE_COUNT:
        raise SubscriptionBuildError(f"existing {owner} links contain duplicate devices")
    return private_keys


def replace_owner_feed(
    existing_payload: dict[str, str],
    owner: str,
    input_dir: Path,
    *,
    rotate_path: bool = False,
) -> dict[str, str]:
    prefixes = {"primary": "PRIMARY", "secondary": "SECONDARY"}
    try:
        prefix = prefixes[owner]
    except KeyError as exc:
        raise SubscriptionBuildError(f"unsupported owner {owner!r}") from exc
    other_prefix = "SECONDARY" if prefix == "PRIMARY" else "PRIMARY"
    new_links, new_keys = _build_links(input_dir)
    other_links = _existing_links(existing_payload, other_prefix)
    other_keys = _private_keys_from_links(other_links, other_prefix.lower())
    if duplicate_keys := new_keys & other_keys:
        raise SubscriptionBuildError(
            f"duplicate device PrivateKey across owners ({len(duplicate_keys)} found)"
        )
    primary_links = new_links if prefix == "PRIMARY" else other_links
    secondary_links = new_links if prefix == "SECONDARY" else other_links
    primary_path = _path(existing_payload, "PRIMARY_PATH")
    secondary_path = _path(existing_payload, "SECONDARY_PATH")
    if rotate_path:
        replacement_path = _new_path()
        while replacement_path in (primary_path, secondary_path):
            replacement_path = _new_path()
        if prefix == "PRIMARY":
            primary_path = replacement_path
        else:
            secondary_path = replacement_path
    if primary_path == secondary_path:
        raise SubscriptionBuildError("primary and secondary bearer paths must differ")
    return {
        "PRIMARY_PATH": primary_path,
        "SECONDARY_PATH": secondary_path,
        **_link_payload("PRIMARY", primary_links),
        **_link_payload("SECONDARY", secondary_links),
    }


def _atomic_write_text(value: str, output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            "w",
            encoding="utf-8",
            dir=output.parent,
            prefix=f".{output.name}.",
            delete=False,
        ) as handle:
            temporary_path = Path(handle.name)
            os.chmod(temporary_path, 0o600)
            handle.write(value)
        os.replace(temporary_path, output)
        os.chmod(output, 0o600)
    finally:
        if temporary_path is not None and temporary_path.exists():
            temporary_path.unlink()


def write_secret_payload(payload: dict[str, str], output: Path) -> None:
    value = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
    _atomic_write_text(value, output)


def build_subscription_urls(payload: dict[str, str], base_url: str) -> str:
    parsed = urlsplit(base_url)
    if (
        parsed.scheme != "https"
        or not parsed.netloc
        or parsed.path not in ("", "/")
        or parsed.query
        or parsed.fragment
    ):
        raise SubscriptionBuildError("base URL must be an HTTPS origin without a path")
    origin = f"https://{parsed.netloc}"
    return (
        f"primary={origin}{payload['PRIMARY_PATH']}\n"
        f"secondary={origin}{payload['SECONDARY_PATH']}\n"
    )


def write_subscription_urls(payload: dict[str, str], base_url: str, output: Path) -> None:
    _atomic_write_text(build_subscription_urls(payload, base_url), output)


def write_outputs(
    payload: dict[str, str],
    output: Path,
    *,
    base_url: str | None = None,
    urls_output: Path = DEFAULT_URLS_OUTPUT,
) -> None:
    urls_value = build_subscription_urls(payload, base_url) if base_url else None
    write_secret_payload(payload, output)
    if urls_value is not None:
        _atomic_write_text(urls_value, urls_output)


def _read_existing_payload(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise SubscriptionBuildError(f"{path}: invalid existing secret payload") from exc
    if not isinstance(value, dict):
        raise SubscriptionBuildError(f"{path}: existing secret payload must be an object")
    return value


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Build two private five-profile Shadowrocket AWG2 subscriptions."
    )
    parser.add_argument("--primary-dir", type=Path, default=DEFAULT_PRIMARY_DIR)
    parser.add_argument("--secondary-dir", type=Path, default=DEFAULT_SECONDARY_DIR)
    parser.add_argument("--owner", choices=("both", "primary", "secondary"), default="both")
    parser.add_argument("--input-dir", type=Path)
    parser.add_argument(
        "--rotate-path",
        action="store_true",
        help="replace the selected owner's bearer path as well as its five links",
    )
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--base-url")
    parser.add_argument("--urls-output", type=Path, default=DEFAULT_URLS_OUTPUT)
    args = parser.parse_args()
    try:
        existing = _read_existing_payload(args.output)
        if args.owner == "both":
            if args.rotate_path:
                raise SubscriptionBuildError("--rotate-path requires a single owner")
            payload = build_secret_payload(
                args.primary_dir,
                args.secondary_dir,
                existing_payload=existing,
            )
        else:
            selected_dir = args.input_dir or (
                args.primary_dir if args.owner == "primary" else args.secondary_dir
            )
            if not existing:
                raise SubscriptionBuildError(
                    "single-owner rotation requires an existing secret payload"
                )
            payload = replace_owner_feed(
                existing,
                args.owner,
                selected_dir,
                rotate_path=args.rotate_path,
            )
        write_outputs(
            payload,
            args.output,
            base_url=args.base_url,
            urls_output=args.urls_output,
        )
    except SubscriptionBuildError as exc:
        parser.exit(1, f"AWG subscription build failed: {exc}\n")
    print(f"Built two private subscriptions with {EXPECTED_PROFILE_COUNT} profiles each")
    print(f"Secrets payload: {args.output}")
    if args.base_url:
        print(f"Subscription URLs: {args.urls_output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
