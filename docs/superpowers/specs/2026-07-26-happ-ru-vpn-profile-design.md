# HAPP RU-VPN Profile Design

## Goal

Add a second generated HAPP routing profile for access to Russian resources through a selected Russian VPN node:

- Russian domains and Russian IP ranges use the proxy outbound.
- All unmatched public traffic uses the direct outbound.
- Private, loopback, link-local, and other locally bypassed networks remain direct.
- The existing `HAPP/DEFAULT.JSON` and `HAPP/DEFAULT.DEEPLINK` keep their current behavior.

This is a `shared` change because the additional profile and its geodata are useful to every repository consumer.

## Generated artifacts

`scripts/build_happ_routing.py` continues to generate:

- `HAPP/DEFAULT.JSON`
- `HAPP/DEFAULT.DEEPLINK`

It additionally generates:

- `HAPP/RU-VPN.JSON`
- `HAPP/RU-VPN.DEEPLINK`

The new profile name is `RU-VPN`. The deeplink uses the same selected mode as the existing profile (`onadd` by default), so importing `RU-VPN.DEEPLINK` adds and activates the additional profile. The generator writes both profiles in one run and preserves a stable `LastUpdated` value for each generated JSON/deeplink pair.

## RU geodata

The repository's compact geodata gains two standard V2Ray tags:

- `geosite:category-ru`
- `geoip:ru`

`geosite:category-ru` is compiled from the already pinned
`v2fly/domain-list-community` commit
`bb622a2b75b3dfbec83719c1eb6e748720ea698e`. Its category includes the
`.ru`, `.рф`, and `.su` families through `tld-ru`, Russian banks, government
services, media, retailers, telecom operators, Yandex, Mail.ru, and other
Russian services hosted in international top-level domains.

`geoip:ru` is imported from the official V2Fly GeoIP release artifact pinned
to immutable release-branch commit
`402b99afef60cf55058350b5d8c29322835636cd` (`202607171233`). The artifact is
accepted only after checksum verification and is cached under
`distillate/upstream/v2fly/`; deterministic local builds consume the cached
copy rather than a floating release URL.

The existing custom tags (`sr-direct`, `sr-proxy`, `sr-block`,
`motivato-block`, and the other published categories) remain available.
Adding the RU tags must not change which entries belong to the existing
custom tags.

## RU-VPN routing

`RU-VPN.JSON` uses:

- `GlobalProxy: "false"` so unmatched traffic is direct.
- `RouteOrder: "block-proxy-direct"`.
- `ProxySites: ["geosite:category-ru"]`.
- `ProxyIp: ["geoip:ru"]`.
- The existing `motivato-block` geosite tag and `sr-block` GeoIP tag when
  their source buckets are non-empty.
- The same local/direct IP exceptions, DNS settings, geodata URLs,
  `DomainStrategy`, `FakeDNS`, and `UseChunkFiles` policy as `DEFAULT`.

The profile does not put `sr-proxy` into `ProxySites` or `ProxyIp`: foreign
services such as OpenAI, Google, and Microsoft must remain direct unless they
also match the Russian domain or IP datasets. It also does not use
`sr-direct` as the proxy list because that aggregate contains local
allowlist entries that are not necessarily Russian.

With `DomainStrategy: "IPIfNonMatch"`, a hostname first matches
`geosite:category-ru`; if it does not, a resolved Russian destination IP can
still match `geoip:ru`.

## DNS behavior

Proxy-matched Russian resources use the existing Remote DNS configuration.
Direct unmatched resources use the existing Domestic DNS configuration.
No new DNS provider or secret is introduced.

## Generator structure

The generator reuses the existing profile/deeplink serializer. Profile
construction receives explicit routing-policy inputs rather than mutating or
swapping `BuildData` buckets. This keeps `DEFAULT` behavior unchanged and
makes `RU-VPN` intent visible:

- default profile: existing `sr-direct` / `sr-proxy` mapping;
- RU-VPN profile: `category-ru` / `ru` proxy mapping with a direct default.

`remove_obsolete_happ_files()` must not delete the new artifacts.
Repository publication allowlists and workflow path filters include both
`RU-VPN` files.

## Documentation

`HAPP/README.md` documents both profiles and provides raw GitHub links for
the additional JSON and deeplink. The root `README.md` explains that the
selected proxy server for `RU-VPN` must itself have a Russian exit IP; the
routing profile selects traffic, not the server's country.

## Verification

Automated tests cover:

- `DEFAULT` remains byte-for-byte stable when only the new profile is added.
- `RU-VPN` has `GlobalProxy == "false"`.
- `RU-VPN` proxies `geosite:category-ru` and `geoip:ru`.
- `RU-VPN` does not proxy `geosite:sr-proxy` or `geoip:sr-proxy`.
- Local/direct network exceptions remain in `DirectIp`.
- Both deeplinks decode to their corresponding JSON objects.
- Both profile pairs share the intended stable build stamp.
- The compiled geodata contains `category-ru` and `ru`.
- Publication validation and workflows include the new generated artifacts.

Required repository checks remain:

```bash
python3 -m unittest discover -s tests -v
python3 -m compileall -q scripts tests
python3 scripts/build_distillate.py
python3 scripts/build_happ_routing.py
```

Manual acceptance:

1. Import `HAPP/RU-VPN.DEEPLINK` into HAPP.
2. Select a VPN server with a verified Russian exit IP.
3. Confirm a Russian IP-check or geo-restricted Russian service sees the
   Russian exit.
4. Confirm a non-Russian IP-check uses the device's normal direct exit.
5. Switch back to `роут-MotivatoPotato` and confirm its behavior is unchanged.

## Non-goals

- Selecting or provisioning a Russian VPN server.
- Changing `shadowrocket.conf`, Clash routing, or the existing HAPP default
  profile.
- Adding per-application routing.
- Automatically following floating `latest` geodata releases.
