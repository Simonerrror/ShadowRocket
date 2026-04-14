from __future__ import annotations

import json
import unittest
from pathlib import Path

from scripts.build_xkeen_local import (
    SubscriptionEntry,
    build_diagnostic_germany_y_profile,
    build_diagnostic_outbounds,
    build_diagnostic_routing,
    build_local_outputs,
    build_private_routing,
    build_single_routing,
    filter_auto_wl_nodes,
    load_subscription_entries,
    node_transport,
    parse_vless_outbound,
)


class BuildXKeenLocalTests(unittest.TestCase):
    def test_load_subscription_entries_reads_mixed_uri_lines(self) -> None:
        from tempfile import TemporaryDirectory

        with TemporaryDirectory() as tmpdir:
            sub_file = Path(tmpdir) / "sub.txt"
            sub_file.write_text(
                "\n".join(
                    [
                        "",
                        "not-a-uri",
                        "vless://uuid@example.com:443?security=reality&sni=www.google.com#%F0%9F%87%B3%F0%9F%87%B1%20Netherlands%20WL%20Mobile%20Vless",
                        "ss://Y2hhY2hhMjAtaWV0Zi1wb2x5MTMwNTpwYXNz@example.com:8388#%F0%9F%87%B3%F0%9F%87%B1%20Netherlands%20WL%20Mobile%20SS",
                        "trojan://secret@example.com:443?security=tls&sni=example.com#%F0%9F%87%B3%F0%9F%87%B1%20Netherlands%20WL%20Mobile%20Trojan",
                    ]
                ),
                encoding="utf-8",
            )

            entries = load_subscription_entries(sub_file)

        self.assertEqual([entry.scheme for entry in entries], ["vless", "ss", "trojan"])
        self.assertEqual(entries[0].name, "🇳🇱 Netherlands WL Mobile Vless")

    def test_filter_auto_wl_nodes_keeps_only_vless_wl_non_cis(self) -> None:
        entries = [
            SubscriptionEntry(scheme="vless", raw_uri="vless://a", name="🇳🇱 Netherlands WL Mobile Vless"),
            SubscriptionEntry(scheme="vless", raw_uri="vless://b", name="🇷🇺 Russia WL Mobile Vless"),
            SubscriptionEntry(scheme="vless", raw_uri="vless://c", name="🇩🇪 Germany Vless Global"),
            SubscriptionEntry(scheme="trojan", raw_uri="trojan://d", name="🇵🇱 Poland WL Mobile Trojan"),
            SubscriptionEntry(scheme="vless", raw_uri="vless://e", name="🇧🇾 Belarus WL Mobile Vless"),
            SubscriptionEntry(scheme="vless", raw_uri="vless://f", name="🇺🇦 Ukraine WL Mobile Vless"),
        ]

        filtered = filter_auto_wl_nodes(entries)

        self.assertEqual([entry.name for entry in filtered], ["🇳🇱 Netherlands WL Mobile Vless"])

    def test_filter_auto_wl_nodes_keeps_xh_and_r_vless_variants(self) -> None:
        entries = [
            SubscriptionEntry(scheme="vless", raw_uri="vless://a", name="🇵🇱 Poland WL Mobile XH Vless"),
            SubscriptionEntry(scheme="vless", raw_uri="vless://b", name="🇵🇱 Poland WL Mobile R Vless"),
        ]

        filtered = filter_auto_wl_nodes(entries)

        self.assertEqual(
            [entry.name for entry in filtered],
            ["🇵🇱 Poland WL Mobile XH Vless", "🇵🇱 Poland WL Mobile R Vless"],
        )

    def test_node_transport_defaults_to_tcp(self) -> None:
        entry = SubscriptionEntry(
            scheme="vless",
            raw_uri="vless://uuid@nl.example:443?security=reality#node",
            name="node",
        )

        self.assertEqual(node_transport(entry), "tcp")

    def test_parse_vless_outbound_maps_reality_tcp_fields(self) -> None:
        entry = SubscriptionEntry(
            scheme="vless",
            raw_uri=(
                "vless://uuid@nl.example:443"
                "?encryption=none&flow=xtls-rprx-vision&type=tcp&security=reality"
                "&sni=www.google.com&fp=chrome&pbk=pubkey&sid=short"
                "#%F0%9F%87%B3%F0%9F%87%B1%20Netherlands%20WL%20Mobile%20Vless"
            ),
            name="🇳🇱 Netherlands WL Mobile Vless",
        )

        outbound = parse_vless_outbound(entry, "xkeen-wl-01")

        self.assertEqual(outbound["tag"], "xkeen-wl-01")
        self.assertEqual(outbound["protocol"], "vless")
        self.assertEqual(outbound["settings"]["vnext"][0]["address"], "nl.example")
        self.assertEqual(outbound["settings"]["vnext"][0]["users"][0]["id"], "uuid")
        self.assertEqual(outbound["streamSettings"]["network"], "tcp")
        self.assertEqual(outbound["streamSettings"]["security"], "reality")
        self.assertEqual(outbound["streamSettings"]["realitySettings"]["publicKey"], "pubkey")

    def test_parse_vless_outbound_maps_xhttp_variant(self) -> None:
        entry = SubscriptionEntry(
            scheme="vless",
            raw_uri=(
                "vless://uuid@nl.example:8443"
                "?encryption=none&type=xhttp&path=%2Fxhttp&host=www.google.com"
                "&mode=auto&security=reality&sni=www.google.com&fp=chrome"
                "&pbk=pubkey&sid=short"
                "#%F0%9F%87%B3%F0%9F%87%B1%20Netherlands%20WL%20Mobile%20XH%20Vless"
            ),
            name="🇳🇱 Netherlands WL Mobile XH Vless",
        )

        outbound = parse_vless_outbound(entry, "xkeen-wl-02")

        self.assertEqual(outbound["streamSettings"]["network"], "xhttp")
        self.assertEqual(outbound["streamSettings"]["xhttpSettings"]["path"], "/xhttp")
        self.assertEqual(outbound["streamSettings"]["xhttpSettings"]["host"], "www.google.com")
        self.assertEqual(outbound["streamSettings"]["xhttpSettings"]["mode"], "auto")

    def test_build_private_routing_uses_flat_ru_direct_then_balancer(self) -> None:
        routing = build_private_routing(balancer_tag="xkeen-auto-wl", selector_prefix="xkeen-wl-")

        self.assertEqual(routing["routing"]["domainStrategy"], "IPIfNonMatch")
        self.assertEqual(routing["routing"]["rules"][0]["outboundTag"], "block")
        self.assertEqual(
            routing["routing"]["balancers"],
            [
                {
                    "tag": "xkeen-auto-wl",
                    "selector": ["xkeen-wl-"],
                    "strategy": {"type": "roundRobin"},
                }
            ],
        )
        self.assertEqual(routing["routing"]["rules"][4]["ip"], ["ext:geoip_zkeenip.dat:ru"])
        self.assertEqual(routing["routing"]["rules"][5]["balancerTag"], "xkeen-auto-wl")
        self.assertNotIn("outboundTag", routing["routing"]["rules"][5])
        self.assertEqual(
            routing["routing"]["rules"][-1],
            {
                "type": "field",
                "inboundTag": ["redirect", "tproxy"],
                "balancerTag": "xkeen-auto-wl",
                "network": "tcp,udp",
            },
        )

    def test_build_single_routing_uses_flat_ru_direct_then_single_outbound(self) -> None:
        routing = build_single_routing(proxy_tag="xkeen-single")

        self.assertEqual(routing["routing"]["domainStrategy"], "IPIfNonMatch")
        self.assertEqual(routing["routing"]["rules"][0]["outboundTag"], "block")
        self.assertEqual(routing["routing"]["rules"][4]["ip"], ["ext:geoip_zkeenip.dat:ru"])
        self.assertEqual(
            routing["routing"]["rules"][-1],
            {
                "type": "field",
                "inboundTag": ["redirect", "tproxy"],
                "outboundTag": "xkeen-single",
                "network": "tcp,udp",
            },
        )
        self.assertNotIn("balancers", routing["routing"])

    def test_build_diagnostic_outbounds_matches_single_shape(self) -> None:
        entry = SubscriptionEntry(
            scheme="vless",
            raw_uri=(
                "vless://uuid@de.example:443"
                "?encryption=none&flow=xtls-rprx-vision&type=tcp&security=reality"
                "&sni=www.google.com&fp=chrome&pbk=pubkey&sid=short"
                "#%F0%9F%87%A9%F0%9F%87%AA%20Germany(Y)%20WL%20Mobile%20Vless"
            ),
            name="🇩🇪 Germany(Y) WL Mobile Vless",
        )

        outbounds = build_diagnostic_outbounds(entry, proxy_tag="xkeen-single")

        self.assertEqual(
            [item["tag"] for item in outbounds["outbounds"]],
            ["xkeen-single", "direct", "block"],
        )
        self.assertEqual(outbounds["outbounds"][-1]["protocol"], "blackhole")

    def test_build_diagnostic_routing_matches_community_layout(self) -> None:
        routing = build_diagnostic_routing(proxy_tag="xkeen-single")

        self.assertEqual(routing["routing"]["domainStrategy"], "IPIfNonMatch")
        self.assertEqual(routing["routing"]["rules"][0]["outboundTag"], "block")
        self.assertEqual(routing["routing"]["rules"][0]["inboundTag"], ["redirect", "tproxy"])
        self.assertEqual(
            routing["routing"]["rules"][3]["domain"][0],
            "regexp:^([\\w\\-\\.]+\\.)ru$",
        )
        self.assertEqual(
            routing["routing"]["rules"][4]["ip"],
            ["ext:geoip_zkeenip.dat:ru"],
        )
        self.assertEqual(
            routing["routing"]["rules"][-1],
            {
                "type": "field",
                "inboundTag": ["redirect", "tproxy"],
                "outboundTag": "xkeen-single",
                "network": "tcp,udp",
            },
        )

    def test_build_local_outputs_writes_private_03_04_05(self) -> None:
        from tempfile import TemporaryDirectory

        with TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            sub_file = tmp_path / "sub.txt"
            sub_file.write_text(
                "\n".join(
                    [
                        (
                            "vless://uuid@nl.example:443"
                            "?encryption=none&flow=xtls-rprx-vision&type=tcp&security=reality"
                            "&sni=www.google.com&fp=chrome&pbk=pubkey&sid=short"
                            "#%F0%9F%87%B3%F0%9F%87%B1%20Netherlands%20WL%20Mobile%20Vless"
                        ),
                        (
                            "vless://uuid@de.example:8443"
                            "?encryption=none&type=xhttp&path=%2Fxhttp&host=www.google.com"
                            "&mode=auto&security=reality&sni=www.google.com&fp=chrome"
                            "&pbk=pubkey&sid=short"
                            "#%F0%9F%87%A9%F0%9F%87%AA%20Germany%20WL%20Mobile%20XH%20Vless"
                        ),
                        (
                            "trojan://secret@ignore.example:443?security=tls&sni=example.com"
                            "#%F0%9F%87%B5%F0%9F%87%B1%20Poland%20WL%20Mobile%20Trojan"
                        ),
                    ]
                )
                + "\n",
                encoding="utf-8",
            )

            summary = build_local_outputs(
                subscription_path=sub_file,
                output_dir=tmp_path,
            )

            self.assertEqual(summary["loaded_entries"], 3)
            self.assertEqual(summary["selected_entries"], 1)

            inbounds = json.loads((tmp_path / "03_inbounds.json").read_text(encoding="utf-8"))
            outbounds = json.loads((tmp_path / "04_outbounds.json").read_text(encoding="utf-8"))
            routing = json.loads((tmp_path / "05_routing.json").read_text(encoding="utf-8"))

            self.assertEqual([item["tag"] for item in inbounds["inbounds"]], ["redirect", "tproxy"])
            self.assertEqual([item["tag"] for item in outbounds["outbounds"][:1]], ["xkeen-wl-01"])
            self.assertEqual(outbounds["outbounds"][-2]["tag"], "direct")
            self.assertEqual(outbounds["outbounds"][-1]["tag"], "block")
            self.assertEqual(routing["routing"]["balancers"][0]["tag"], "xkeen-auto-wl")
            self.assertEqual(routing["routing"]["balancers"][0]["selector"], ["xkeen-wl-"])
            self.assertEqual(routing["routing"]["rules"][3]["outboundTag"], "direct")
            self.assertEqual(routing["routing"]["rules"][4]["ip"], ["ext:geoip_zkeenip.dat:ru"])
            self.assertEqual(routing["routing"]["rules"][-1]["balancerTag"], "xkeen-auto-wl")
            self.assertNotIn("outboundTag", routing["routing"]["rules"][-1])

    def test_build_local_outputs_excludes_xhttp_nodes_for_router_compat(self) -> None:
        from tempfile import TemporaryDirectory

        with TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            sub_file = tmp_path / "sub.txt"
            sub_file.write_text(
                "\n".join(
                    [
                        (
                            "vless://uuid@nl.example:443"
                            "?encryption=none&flow=xtls-rprx-vision&type=tcp&security=reality"
                            "&sni=www.google.com&fp=chrome&pbk=pubkey&sid=short"
                            "#%F0%9F%87%B3%F0%9F%87%B1%20Netherlands%20WL%20Mobile%20Vless"
                        ),
                        (
                            "vless://uuid@de.example:8443"
                            "?encryption=none&type=xhttp&path=%2Fxhttp&host=www.google.com"
                            "&mode=auto&security=reality&sni=www.google.com&fp=chrome"
                            "&pbk=pubkey&sid=short"
                            "#%F0%9F%87%A9%F0%9F%87%AA%20Germany%20WL%20Mobile%20XH%20Vless"
                        ),
                    ]
                )
                + "\n",
                encoding="utf-8",
            )

            summary = build_local_outputs(
                subscription_path=sub_file,
                output_dir=tmp_path,
            )
            outbounds = json.loads((tmp_path / "04_outbounds.json").read_text(encoding="utf-8"))

            self.assertEqual(summary["loaded_entries"], 2)
            self.assertEqual(summary["selected_entries"], 1)
            self.assertEqual(
                [item["tag"] for item in outbounds["outbounds"] if item.get("protocol") == "vless"],
                ["xkeen-wl-01"],
            )

    def test_build_local_outputs_writes_single_node_profiles(self) -> None:
        from tempfile import TemporaryDirectory

        with TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            sub_file = tmp_path / "sub.txt"
            sub_file.write_text(
                "\n".join(
                    [
                        (
                            "vless://uuid@de.example:443"
                            "?encryption=none&flow=xtls-rprx-vision&type=tcp&security=reality"
                            "&sni=www.google.com&fp=chrome&pbk=pubkey&sid=short"
                            "#%F0%9F%87%A9%F0%9F%87%AA%20Germany(Y)%20WL%20Mobile%20Vless"
                        ),
                        (
                            "vless://uuid@nl.example:443"
                            "?encryption=none&flow=xtls-rprx-vision&type=tcp&security=reality"
                            "&sni=www.google.com&fp=chrome&pbk=pubkey&sid=short"
                            "#%F0%9F%87%B3%F0%9F%87%B1%20Netherlands%20WL%20Mobile%20Vless"
                        ),
                    ]
                )
                + "\n",
                encoding="utf-8",
            )

            summary = build_local_outputs(
                subscription_path=sub_file,
                output_dir=tmp_path / "local",
                singles_dir=tmp_path / "singles",
            )

            self.assertEqual(summary["selected_entries"], 2)
            self.assertEqual(summary["single_profiles"], 2)

            germany_dir = tmp_path / "singles" / "germany-y"
            self.assertTrue((germany_dir / "03_inbounds.json").exists())
            self.assertTrue((germany_dir / "04_outbounds.json").exists())
            self.assertTrue((germany_dir / "05_routing.json").exists())

            germany_outbounds = json.loads((germany_dir / "04_outbounds.json").read_text(encoding="utf-8"))
            germany_routing = json.loads((germany_dir / "05_routing.json").read_text(encoding="utf-8"))

            self.assertEqual(
                [item["tag"] for item in germany_outbounds["outbounds"] if item.get("protocol") == "vless"],
                ["xkeen-single"],
            )
            self.assertEqual(germany_routing["routing"]["rules"][0]["outboundTag"], "block")
            self.assertEqual(germany_routing["routing"]["rules"][4]["outboundTag"], "direct")
            self.assertEqual(germany_routing["routing"]["rules"][-1]["outboundTag"], "xkeen-single")
            self.assertNotIn("balancerTag", germany_routing["routing"]["rules"][-1])

    def test_build_local_outputs_writes_germany_y_diagnostic_profile(self) -> None:
        from tempfile import TemporaryDirectory

        with TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            sub_file = tmp_path / "sub.txt"
            sub_file.write_text(
                "\n".join(
                    [
                        (
                            "vless://uuid@de.example:443"
                            "?encryption=none&flow=xtls-rprx-vision&type=tcp&security=reality"
                            "&sni=www.google.com&fp=chrome&pbk=pubkey&sid=short"
                            "#%F0%9F%87%A9%F0%9F%87%AA%20Germany(Y)%20WL%20Mobile%20Vless"
                        ),
                        (
                            "vless://uuid@nl.example:443"
                            "?encryption=none&flow=xtls-rprx-vision&type=tcp&security=reality"
                            "&sni=www.google.com&fp=chrome&pbk=pubkey&sid=short"
                            "#%F0%9F%87%B3%F0%9F%87%B1%20Netherlands%20WL%20Mobile%20Vless"
                        ),
                    ]
                )
                + "\n",
                encoding="utf-8",
            )

            summary = build_local_outputs(
                subscription_path=sub_file,
                output_dir=tmp_path / "local",
                singles_dir=tmp_path / "singles",
                diagnostics_dir=tmp_path / "diagnostics",
            )

            self.assertEqual(summary["diagnostic_profiles"], 1)

            diagnostic_dir = tmp_path / "diagnostics" / "germany-y-split"
            self.assertTrue((diagnostic_dir / "03_inbounds.json").exists())
            self.assertTrue((diagnostic_dir / "04_outbounds.json").exists())
            self.assertTrue((diagnostic_dir / "05_routing.json").exists())

            inbounds = json.loads((diagnostic_dir / "03_inbounds.json").read_text(encoding="utf-8"))
            outbounds = json.loads((diagnostic_dir / "04_outbounds.json").read_text(encoding="utf-8"))
            routing = json.loads((diagnostic_dir / "05_routing.json").read_text(encoding="utf-8"))

            self.assertFalse((diagnostic_dir / "02_dns.json").exists())
            self.assertEqual(inbounds["inbounds"][0]["sniffing"]["destOverride"], ["http", "tls"])
            self.assertEqual([item["tag"] for item in outbounds["outbounds"]], ["xkeen-single", "direct", "block"])
            self.assertEqual(routing["routing"]["domainStrategy"], "IPIfNonMatch")
            self.assertEqual(routing["routing"]["rules"][0]["outboundTag"], "block")
            self.assertEqual(routing["routing"]["rules"][-1]["outboundTag"], "xkeen-single")

    def test_build_diagnostic_germany_y_profile_returns_zero_without_matching_node(self) -> None:
        from tempfile import TemporaryDirectory

        with TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            count = build_diagnostic_germany_y_profile(
                entries=[
                    SubscriptionEntry(
                        scheme="vless",
                        raw_uri="vless://uuid@nl.example:443?type=tcp#%F0%9F%87%B3%F0%9F%87%B1%20Netherlands%20WL%20Mobile%20Vless",
                        name="🇳🇱 Netherlands WL Mobile Vless",
                    )
                ],
                diagnostics_dir=tmp_path / "diagnostics",
            )

            self.assertEqual(count, 0)
            self.assertFalse((tmp_path / "diagnostics" / "germany-y-split").exists())


if __name__ == "__main__":
    unittest.main()
