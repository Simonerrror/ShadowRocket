from __future__ import annotations

import base64
import hashlib
import json
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from scripts.build_happ_routing import (
    RU_PROFILE_NAME,
    BuildData,
    Bucket,
    build_profile as build_happ_profile,
)
from scripts.build_incy_routing import (
    build_profile,
    profile_to_deeplink,
    resolve_build_stamp,
)


class IncyProfileContractTests(unittest.TestCase):
    def _profile_kwargs(self) -> dict[str, object]:
        data = BuildData(
            direct=Bucket(site_rules=["domain:ru"], cidrs=["192.0.2.0/24"]),
            proxy=Bucket(site_rules=["domain:openai.com"], cidrs=["198.51.100.0/24"]),
            block=Bucket(site_rules=["domain:ads.example"], cidrs=["203.0.113.0/24"]),
        )
        return {
            "data": data,
            "geodata_base": "https://example.test/dat",
            "last_updated": "123",
            "route_order": "block-proxy-direct",
            "remote_dns_ip": "8.8.8.8",
            "remote_dns_domain": "https://8.8.8.8/dns-query",
            "domestic_dns_ip": "77.88.8.8",
            "remote_dns_type": "DoH",
            "domestic_dns_type": "DoH",
            "general_direct_ips": ["127.0.0.1"],
            "profile_name": RU_PROFILE_NAME,
            "block_geosite_tag": "motivato-block",
            "global_proxy": "false",
            "direct_geosite_tag": None,
            "direct_geoip_tag": None,
            "proxy_geosite_tag": "category-ru",
            "proxy_geoip_tag": "ru",
        }

    def test_incy_profile_matches_happ_routing_semantics_with_official_field(self) -> None:
        kwargs = self._profile_kwargs()

        happ = build_happ_profile(**kwargs)
        incy = build_profile(**kwargs)

        expected = dict(happ)
        expected.pop("UseChunkFiles")
        expected["useChunkFiles"] = False
        self.assertEqual(incy, expected)
        self.assertEqual(incy["RouteOrder"], "block-proxy-direct")
        self.assertIs(incy["useChunkFiles"], False)
        self.assertNotIn("UseChunkFiles", incy)

    def test_incy_deeplink_is_compact_standard_base64_and_decodes_to_profile(self) -> None:
        profile = {"Name": "RU-VPN", "GlobalProxy": "false", "useChunkFiles": False}

        pretty, compact, deeplink = profile_to_deeplink(profile, "onadd")
        encoded = deeplink.rsplit("/", 1)[1]

        self.assertTrue(deeplink.startswith("incy://routing/onadd/"))
        self.assertEqual(base64.b64decode(encoded).decode("utf-8"), compact)
        self.assertEqual(json.loads(pretty), profile)
        self.assertEqual(json.loads(compact), profile)

    def test_incy_supports_add_and_onadd_modes(self) -> None:
        profile = {"Name": "test", "useChunkFiles": False}

        self.assertTrue(profile_to_deeplink(profile, "add")[2].startswith("incy://routing/add/"))
        self.assertTrue(profile_to_deeplink(profile, "onadd")[2].startswith("incy://routing/onadd/"))

    def test_incy_stamp_preserves_existing_profile_stamp(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            out_dir = root / "INCY"
            out_dir.mkdir()
            (out_dir / "DEFAULT.JSON").write_text(
                json.dumps({"LastUpdated": "1234567890"}),
                encoding="utf-8",
            )

            self.assertEqual(resolve_build_stamp(root, "", out_dir), "1234567890")

    def test_generator_publishes_release_urls_and_sha256_sidecars(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "shadowrocket.conf").write_text("[General]\n", encoding="utf-8")
            dat_dir = root / "distillate" / "dat"
            dat_dir.mkdir(parents=True)
            dat_contents = {
                "geoip.dat": b"test geoip payload\n",
                "geosite.dat": b"test geosite payload\n",
            }
            for name, content in dat_contents.items():
                (dat_dir / name).write_bytes(content)

            for kind in ("domain", "ip"):
                directory = root / "distillate" / "text" / kind
                directory.mkdir(parents=True)
                for bucket in ("direct", "proxy", "block"):
                    (directory / f"sr-{bucket}.txt").write_text("\n", encoding="utf-8")
            (root / "distillate" / "text" / "domain" / "motivato_block.txt").write_text(
                "domain:block.example\n", encoding="utf-8"
            )

            subprocess.run(
                ["git", "init", "--quiet"],
                cwd=root,
                check=True,
            )
            subprocess.run(
                ["git", "remote", "add", "origin", "https://github.com/Simonerrror/ShadowRocket.git"],
                cwd=root,
                check=True,
            )
            subprocess.run(
                [
                    sys.executable,
                    str(Path(__file__).parents[1] / "scripts" / "build_incy_routing.py"),
                    "--build-stamp",
                    "42",
                ],
                cwd=root,
                check=True,
            )

            expected_base = "https://github.com/Simonerrror/ShadowRocket/releases/download/incy-geodata"
            for profile_name in ("DEFAULT.JSON", "RU-VPN.JSON"):
                profile = json.loads((root / "INCY" / profile_name).read_text(encoding="utf-8"))
                self.assertEqual(profile["Geoipurl"], f"{expected_base}/geoip.dat")
                self.assertEqual(profile["Geositeurl"], f"{expected_base}/geosite.dat")

            for name, content in dat_contents.items():
                sidecar = dat_dir / f"{name}.sha256"
                sidecar_text = sidecar.read_text(encoding="utf-8")
                self.assertIsNotNone(re.fullmatch(r"[0-9a-f]{64}\n", sidecar_text))
                self.assertEqual(sidecar_text, f"{hashlib.sha256(content).hexdigest()}\n")


if __name__ == "__main__":
    unittest.main()
