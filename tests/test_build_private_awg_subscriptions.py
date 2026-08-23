from __future__ import annotations

import base64
import json
import tempfile
import unittest
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlsplit

from scripts.build_private_awg_subscriptions import (
    SubscriptionBuildError,
    build_secret_payload,
    replace_owner_feed,
    write_outputs,
    write_secret_payload,
    write_subscription_urls,
)


COUNTRY_CODES = ("de", "fi", "gr", "nl", "pl")


def key(seed: int) -> str:
    return base64.b64encode(bytes([seed]) * 32).decode("ascii")


def config_text(
    seed: int,
    *,
    dns: str = "8.8.8.8",
    jc: str = "4",
    s1: str = "15",
    i1: str = "<b 0x0102>",
    allowed_ips: str = "0.0.0.0/0",
    keepalive: str = "25",
    extra: str = "",
) -> str:
    return f"""[Interface]
Address = 10.77.0.{seed}/32
DNS = {dns}
PrivateKey = {key(seed)}
Jc = {jc}
Jmin = 20
Jmax = 120
S1 = {s1}
S2 = 25
S3 = 35
S4 = 45
H1 = 1000000001-1000000010
H2 = 2000000001-2000000010
H3 = 3000000001-3000000010
H4 = 4000000001-4000000010
I1 = {i1}
I2 = <b 0x0304>
I3 = <b 0x0506>
I4 = <b 0x0708>
I5 = <b 0x090a>
{extra}[Peer]
PublicKey = {key(seed + 40)}
PresharedKey = {key(seed + 80)}
AllowedIPs = {allowed_ips}
Endpoint = 192.0.2.{seed}:443
PersistentKeepalive = {keepalive}
"""


def populate(directory: Path, seed_start: int) -> None:
    directory.mkdir(parents=True)
    for offset, country in enumerate(COUNTRY_CODES):
        (directory / f"{offset + 1:02d}-amneziawg_{country}.conf").write_text(
            config_text(seed_start + offset),
            encoding="utf-8",
        )


class PrivateAwgSubscriptionBuildTests(unittest.TestCase):
    def test_builds_two_five_device_feeds_and_reuses_existing_paths(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            primary = root / "primary"
            secondary = root / "secondary"
            populate(primary, 1)
            populate(secondary, 11)
            existing = {
                "PRIMARY_PATH": "/s/primary-existing-token-1234567890ab",
                "SECONDARY_PATH": "/s/secondary-existing-token-12345678",
            }

            payload = build_secret_payload(primary, secondary, existing_payload=existing)

            self.assertEqual(payload["PRIMARY_PATH"], existing["PRIMARY_PATH"])
            self.assertEqual(payload["SECONDARY_PATH"], existing["SECONDARY_PATH"])
            expected_titles = {
                "🇩🇪 Германия AWG2",
                "🇫🇮 Финляндия AWG2",
                "🇬🇷 Греция AWG2",
                "🇳🇱 Нидерланды AWG2",
                "🇵🇱 Польша AWG2",
            }
            all_private_keys: set[str] = set()
            for owner in ("PRIMARY", "SECONDARY"):
                lines = [payload[f"{owner}_LINK_{index}"] for index in range(1, 6)]
                self.assertEqual(len(lines), 5)
                for line in lines:
                    self.assertLessEqual(len(line.encode("utf-8")), 5 * 1024)
                    parsed = urlsplit(line)
                    query = parse_qs(parsed.query, strict_parsing=True)
                    self.assertEqual(parsed.scheme, "wg")
                    self.assertEqual(query["obfs"], ["amneziawg"])
                    self.assertEqual(
                        set(json.loads(query["obfsParam"][0])),
                        {
                            "jc", "jmin", "jmax", "s1", "s2", "s3", "s4",
                            "h1", "h2", "h3", "h4", "i1", "i2", "i3", "i4", "i5",
                        },
                    )
                    self.assertIn(unquote(parsed.fragment), expected_titles)
                    private_key = query["privateKey"][0]
                    self.assertNotIn(private_key, all_private_keys)
                    all_private_keys.add(private_key)

            output = root / "private" / "worker-secrets.json"
            write_secret_payload(payload, output)
            self.assertEqual(output.stat().st_mode & 0o777, 0o600)
            self.assertEqual(json.loads(output.read_text(encoding="utf-8")), payload)

            urls_output = root / "private" / "subscription-urls.txt"
            write_subscription_urls(
                payload,
                "https://potato-box.example.workers.dev",
                urls_output,
            )
            self.assertEqual(urls_output.stat().st_mode & 0o777, 0o600)
            self.assertEqual(
                urls_output.read_text(encoding="utf-8").splitlines(),
                [
                    f"primary=https://potato-box.example.workers.dev{existing['PRIMARY_PATH']}",
                    f"secondary=https://potato-box.example.workers.dev{existing['SECONDARY_PATH']}",
                ],
            )

    def test_rejects_incomplete_incompatible_or_reused_device_sets(self) -> None:
        cases = (
            "wrong-count",
            "placeholder",
            "braced-placeholder",
            "awg3",
            "invalid-awg-number",
            "invalid-s-size",
            "invalid-instruction",
            "invalid-allowed-ips",
            "invalid-keepalive",
            "duplicate-device",
            "noncanonical-duplicate-device",
        )
        for case in cases:
            with self.subTest(case=case), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                primary = root / "primary"
                secondary = root / "secondary"
                populate(primary, 1)
                populate(secondary, 11)
                message = ""
                if case == "wrong-count":
                    (primary / "01-amneziawg_de.conf").unlink()
                    message = "exactly 5"
                elif case == "placeholder":
                    path = primary / "01-amneziawg_de.conf"
                    path.write_text(config_text(1, dns="$PRIMARY_DNS"), encoding="utf-8")
                    message = "placeholder"
                elif case == "braced-placeholder":
                    path = primary / "01-amneziawg_de.conf"
                    path.write_text(config_text(1, jc="${JC}"), encoding="utf-8")
                    message = "placeholder"
                elif case == "awg3":
                    path = primary / "01-amneziawg_de.conf"
                    path.write_text(
                        config_text(1, extra=f"HeaderProtectionKey = {key(120)}\n"),
                        encoding="utf-8",
                    )
                    message = "AWG3"
                elif case == "invalid-awg-number":
                    path = primary / "01-amneziawg_de.conf"
                    path.write_text(config_text(1, jc="nonsense"), encoding="utf-8")
                    message = "invalid Jc"
                elif case == "invalid-s-size":
                    path = primary / "01-amneziawg_de.conf"
                    path.write_text(config_text(1, s1="65536"), encoding="utf-8")
                    message = "invalid S1"
                elif case == "invalid-instruction":
                    path = primary / "01-amneziawg_de.conf"
                    path.write_text(
                        config_text(1, i1="<b 0xGG>"),
                        encoding="utf-8",
                    )
                    message = "invalid I1"
                elif case == "invalid-allowed-ips":
                    path = primary / "01-amneziawg_de.conf"
                    path.write_text(
                        config_text(1, allowed_ips="invalid"),
                        encoding="utf-8",
                    )
                    message = "invalid AllowedIPs"
                elif case == "invalid-keepalive":
                    path = primary / "01-amneziawg_de.conf"
                    path.write_text(
                        config_text(1, keepalive="forever"),
                        encoding="utf-8",
                    )
                    message = "invalid PersistentKeepalive"
                elif case == "duplicate-device":
                    path = secondary / "01-amneziawg_de.conf"
                    path.write_text(config_text(1), encoding="utf-8")
                    message = "duplicate device"
                else:
                    path = secondary / "01-amneziawg_de.conf"
                    canonical = key(1)
                    replacement = "F" if canonical[-2] == "E" else "E"
                    alias = f"{canonical[:-2]}{replacement}="
                    path.write_text(
                        config_text(11).replace(key(11), alias, 1),
                        encoding="utf-8",
                    )
                    message = "invalid PrivateKey"

                with self.assertRaisesRegex(SubscriptionBuildError, message):
                    build_secret_payload(primary, secondary)

    def test_single_owner_rotation_preserves_the_other_feed_and_bearer_paths(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            primary = root / "primary"
            secondary = root / "secondary"
            populate(primary, 1)
            populate(secondary, 11)
            original = build_secret_payload(primary, secondary)
            replacement = root / "replacement"
            populate(replacement, 21)

            rotated = replace_owner_feed(original, "primary", replacement)

            self.assertNotEqual(
                [rotated[f"PRIMARY_LINK_{index}"] for index in range(1, 6)],
                [original[f"PRIMARY_LINK_{index}"] for index in range(1, 6)],
            )
            self.assertEqual(
                [rotated[f"SECONDARY_LINK_{index}"] for index in range(1, 6)],
                [original[f"SECONDARY_LINK_{index}"] for index in range(1, 6)],
            )
            self.assertEqual(rotated["PRIMARY_PATH"], original["PRIMARY_PATH"])
            self.assertEqual(rotated["SECONDARY_PATH"], original["SECONDARY_PATH"])

            path_rotated = replace_owner_feed(
                original,
                "primary",
                replacement,
                rotate_path=True,
            )
            self.assertNotEqual(path_rotated["PRIMARY_PATH"], original["PRIMARY_PATH"])
            self.assertEqual(path_rotated["SECONDARY_PATH"], original["SECONDARY_PATH"])

            duplicate = root / "duplicate"
            populate(duplicate, 11)
            with self.assertRaisesRegex(SubscriptionBuildError, "duplicate device"):
                replace_owner_feed(original, "primary", duplicate)

    def test_rejects_identical_bearer_paths(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            primary = root / "primary"
            secondary = root / "secondary"
            populate(primary, 1)
            populate(secondary, 11)
            shared_path = "/s/shared-existing-token-1234567890abcdef"

            with self.assertRaisesRegex(SubscriptionBuildError, "bearer paths"):
                build_secret_payload(
                    primary,
                    secondary,
                    existing_payload={
                        "PRIMARY_PATH": shared_path,
                        "SECONDARY_PATH": shared_path,
                    },
                )

    def test_invalid_base_url_leaves_existing_outputs_untouched(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            primary = root / "primary"
            secondary = root / "secondary"
            populate(primary, 1)
            populate(secondary, 11)
            payload = build_secret_payload(primary, secondary)
            output = root / "worker-secrets.json"
            urls_output = root / "subscription-urls.txt"
            output.write_text("original\n", encoding="utf-8")

            with self.assertRaisesRegex(SubscriptionBuildError, "HTTPS origin"):
                write_outputs(
                    payload,
                    output,
                    base_url="http://invalid.example",
                    urls_output=urls_output,
                )

            self.assertEqual(output.read_text(encoding="utf-8"), "original\n")
            self.assertFalse(urls_output.exists())

    def test_repeated_country_profiles_receive_distinct_visible_names(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            primary = root / "primary"
            secondary = root / "secondary"
            primary.mkdir()
            for offset in range(5):
                (primary / f"{offset + 1:02d}-amneziawg_pl.conf").write_text(
                    config_text(offset + 1),
                    encoding="utf-8",
                )
            populate(secondary, 11)

            payload = build_secret_payload(primary, secondary)

            titles = [
                unquote(urlsplit(line).fragment)
                for line in [payload[f"PRIMARY_LINK_{index}"] for index in range(1, 6)]
            ]
            self.assertEqual(
                titles,
                [
                    "🇵🇱 Польша AWG2",
                    "🇵🇱 Польша 2 AWG2",
                    "🇵🇱 Польша 3 AWG2",
                    "🇵🇱 Польша 4 AWG2",
                    "🇵🇱 Польша 5 AWG2",
                ],
            )


if __name__ == "__main__":
    unittest.main()
