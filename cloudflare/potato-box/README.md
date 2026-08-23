# Private AWG2 subscriptions

`potato-box` serves two private Shadowrocket subscriptions named `primary` and
`secondary`. Each feed contains exactly five independent AmneziaWG 2.0 device
profiles. Keep the human-to-owner mapping outside the repository.

The repository contains only Worker and generator code. Native `.conf` files,
generated `wg://` links, Cloudflare secret payloads, and bearer URLs stay under
the ignored `private/` directory.

## First build

Create two local input directories and place exactly five AWG2 files in each:

```text
private/awg/primary/*.conf
private/awg/secondary/*.conf
```

End every filename with a two-letter country code, for example
`01-amneziawg_de.conf` or `amneziawg_pl (2).conf`. The suffix controls the
Shadowrocket name and flag.

Build the complete secret payload:

```bash
python3 scripts/build_private_awg_subscriptions.py
```

The generator fails before replacement unless both directories contain exactly
five profiles. It also rejects AWG3 fields, unresolved `$VARIABLE` placeholders,
invalid keys, unsupported country suffixes, and duplicate device private keys.
The output is `private/awg/worker-secrets.json` with mode `0600`. Each of the
ten generated links is stored in its own Worker secret because Cloudflare
limits one secret value to 5 KB. The Worker joins each five-link set only when
the matching subscription URL is requested.

## Deploy code and upload subscriptions

Install the reviewed exact dependency and verify Cloudflare authentication:

```bash
npm ci --ignore-scripts --prefix cloudflare/potato-box
cloudflare/potato-box/node_modules/.bin/wrangler whoami \
  --config cloudflare/potato-box/wrangler.jsonc
```

Deploy the Worker, then upload all twelve secrets in one operation:

```bash
npm run deploy --prefix cloudflare/potato-box
cloudflare/potato-box/node_modules/.bin/wrangler secret bulk \
  private/awg/worker-secrets.json \
  --config cloudflare/potato-box/wrangler.jsonc
```

Use the deployed HTTPS origin reported by Wrangler to produce the two local
subscription URLs without printing their bearer paths to the terminal:

```bash
python3 scripts/build_private_awg_subscriptions.py \
  --base-url https://potato-box.<workers-subdomain>.workers.dev
```

The resulting mode-`0600` file is
`private/awg/subscription-urls.txt`. Distribute the two URLs according to the
off-repository owner mapping and add each one to Shadowrocket as type
`Subscribe`.

## Replace one five-device set

Keep `private/awg/worker-secrets.json` on the trusted operator Mac. To replace
only the primary feed while preserving the secondary feed and both bearer URLs:

```bash
python3 scripts/build_private_awg_subscriptions.py \
  --owner primary \
  --input-dir /absolute/path/to/five/new/configs \
  --base-url https://potato-box.<workers-subdomain>.workers.dev
cloudflare/potato-box/node_modules/.bin/wrangler secret bulk \
  private/awg/worker-secrets.json \
  --config cloudflare/potato-box/wrangler.jsonc
```

Use `--owner secondary` for the other feed. A single-owner rotation still
uploads the complete twelve-secret payload, so the other five-profile
subscription remains unchanged. Rebuilding both directories replaces both
feeds.

The subscription URLs are bearer credentials. Anyone who obtains one can read
all five embedded WireGuard private keys. If a URL is exposed, issue five new
device profiles and run the same single-owner command with `--rotate-path`
before the bulk secret upload. The selected owner receives a new subscription
URL; the other owner’s URL and five links remain unchanged.
