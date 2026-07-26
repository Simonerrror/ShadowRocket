# Potato Link Worker Design

## Goal

Publish a neutral, clickable `workers.dev` URL that redirects directly to the
current HAPP RU routing-profile deeplink. The public Worker name is
`potato-link`; it must not contain `vpn`, `proxy`, `happ`, or routing-related
words.

This is a `shared` repository change because the redirector is a public entry
point for a generated profile already published by the repository.

## User experience

Opening:

```text
https://potato-link.<cloudflare-subdomain>.workers.dev/
```

returns `302 Found` with the current contents of `HAPP/RU-VPN.DEEPLINK` in the
`Location` header. A normal tap therefore hands the deeplink to HAPP without
requiring the user to copy it.

The custom-scheme destination necessarily starts with `happ://` after the HTTP
redirect, but the visible public URL and Worker name remain neutral.

Only `/` and `/open` redirect. Other paths return a plain-text `404`. This
provides one short canonical address plus an explicit path that can be useful
in clients that normalize a bare domain.

## Embedded destination

The Worker does not fetch GitHub at request time. A deterministic build script
reads `HAPP/RU-VPN.DEEPLINK`, validates it, JSON-escapes it, and embeds it into
the deployable Worker module.

Validation requires:

- a single non-empty line;
- a maximum length of 16 KiB;
- the prefix `happ://routing/onadd/`;
- a base64 payload containing only the expected base64 alphabet and padding.

An invalid input stops the build and deployment. The generated Worker module is
committed so repository checks can detect stale output before deployment.

## Worker behavior

For `GET` and `HEAD` requests to `/` or `/open`, the Worker returns:

- status `302`;
- `Location: <embedded deeplink>`;
- `Cache-Control: no-store`;
- `Referrer-Policy: no-referrer`;
- `X-Content-Type-Options: nosniff`.

Other methods return `405 Method Not Allowed` with `Allow: GET, HEAD`. Unknown
paths return `404 Not Found`. Error responses are short plain text and do not
expose the embedded deeplink.

The Worker has no runtime secrets, storage, analytics, external fetches, or
custom domain.

## Automatic deployment

A GitHub Actions workflow runs when `main` changes any of:

- `HAPP/RU-VPN.DEEPLINK`;
- the Worker source, generated output, tests, or configuration;
- the embedding build script.

The workflow:

1. checks out an immutable revision of the repository;
2. installs the exact reviewed Wrangler dependency from the committed lockfile
   with `npm ci --ignore-scripts`;
3. regenerates the embedded Worker;
4. fails if the committed generated module is stale;
5. runs the Worker tests;
6. deploys `potato-link` through Wrangler.

Third-party GitHub Actions are pinned to immutable commit SHAs. Wrangler is
pinned to exact version `4.114.0`; floating selectors such as `latest` are not
used.

Deployment needs two GitHub repository secrets:

- `CLOUDFLARE_API_TOKEN`, scoped to edit Workers Scripts for the target account;
- `CLOUDFLARE_ACCOUNT_ID`.

The workflow receives only read access to repository contents. Pull requests
run build and tests without receiving Cloudflare secrets or deploying.

## Local and CI verification

Dependency-free Node tests exercise the generated module with the built-in
`Request` and `Response` APIs:

- `/` returns `302` and the exact embedded destination;
- `/open` behaves identically;
- `HEAD` redirects without a response body;
- an unknown path returns `404`;
- a non-GET/HEAD request returns `405`;
- security and cache headers are present.

Python tests cover valid embedding and rejection of malformed, multiline, or
oversized input.

Before the first deployment:

```bash
npm ci --ignore-scripts
python3 scripts/build_potato_link_worker.py
npm test
npx --no-install wrangler deploy --dry-run
```

After deployment:

```bash
curl -I --max-redirs 0 \
  https://potato-link.<cloudflare-subdomain>.workers.dev/
```

Acceptance requires `302` and a `Location` header beginning with
`happ://routing/onadd/`. The final manual check is tapping the HTTPS URL on the
phone and confirming that HAPP opens the profile import.

## Rollout

The current local RU-profile commits must reach GitHub before enabling the
deployment workflow. The first real deployment may be performed locally after
Cloudflare browser authentication, or by manually dispatching the workflow
after its two repository secrets are configured.

The Worker deployment is tested before adding the public address to the
repository README. If the experiment is unsuccessful, the workflow and Worker
files can be removed without affecting profile generation.

## Non-goals

- Buying or configuring a custom domain.
- Fetching the destination from GitHub on every request.
- Selecting, provisioning, or exposing a VPN server.
- Adding a web UI, tracking, cookies, or a link-shortening service.
- Storing a Cloudflare API token in the repository.
