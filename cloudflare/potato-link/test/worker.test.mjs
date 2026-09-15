import assert from "node:assert/strict";
import test from "node:test";

import { DESTINATIONS } from "../dist/destinations.js";
import worker from "../src/worker.js";


const PUBLIC_REPOSITORY = "https://raw.githubusercontent.com/Simonerrror/ShadowRocket/main";
const SHADOWROCKET_MODULES = [
  ["/sr/modules/tailscale-direct", `${PUBLIC_REPOSITORY}/modules/tailscale_direct.module`],
  ["/sr/modules/tailscale-tailnet", `${PUBLIC_REPOSITORY}/modules/tailscale_tailnet.module`],
  ["/sr/modules/gfn", `${PUBLIC_REPOSITORY}/modules/GFN-AM.module`],
  ["/sr/modules/wechat", `${PUBLIC_REPOSITORY}/modules/wechat_direct.module`],
  ["/sr/modules/twitch", `${PUBLIC_REPOSITORY}/modules/twitch_video_direct.module`],
  [
    "/sr/modules/anti-advertising",
    `${PUBLIC_REPOSITORY}/modules/anti_advertising.module`,
  ],
];


async function request(path, method = "GET") {
  return worker.fetch(
    new Request(`https://potato-link.example${path}`, { method }),
  );
}


test("root redirects to the default profile", async () => {
  const response = await request("/");

  assert.equal(response.status, 302);
  assert.equal(response.headers.get("location"), DESTINATIONS.default);
});

test("/ru redirects to the RU profile", async () => {
  const response = await request("/ru");

  assert.equal(response.status, 302);
  assert.equal(response.headers.get("location"), DESTINATIONS.ru);
  assert.notEqual(DESTINATIONS.ru, DESTINATIONS.default);
});

test("/incy redirects to the INCY default profile", async () => {
  const response = await request("/incy");

  assert.equal(response.status, 302);
  assert.equal(response.headers.get("location"), DESTINATIONS.incyDefault);
  assert.match(DESTINATIONS.incyDefault, /^incy:\/\/routing\/(onadd|add)\//);
});

test("/incy/ru redirects to the INCY RU profile", async () => {
  const response = await request("/incy/ru");

  assert.equal(response.status, 302);
  assert.equal(response.headers.get("location"), DESTINATIONS.incyRu);
  assert.match(DESTINATIONS.incyRu, /^incy:\/\/routing\/(onadd|add)\//);
  assert.notEqual(DESTINATIONS.incyRu, DESTINATIONS.incyDefault);
});

test("HEAD redirects without a body", async () => {
  const response = await request("/ru", "HEAD");

  assert.equal(response.status, 302);
  assert.equal(await response.text(), "");
});

test("Shadowrocket config and module paths redirect to fixed imports", async () => {
  const configResponse = await request("/sr/config");

  assert.equal(configResponse.status, 302);
  assert.equal(
    configResponse.headers.get("location"),
    `shadowrocket://config/add/${PUBLIC_REPOSITORY}/shadowrocket.conf`,
  );

  for (const [path, moduleUrl] of SHADOWROCKET_MODULES) {
    const response = await request(path);

    assert.equal(response.status, 302, path);
    assert.equal(
      response.headers.get("location"),
      `shadowrocket://install?module=${encodeURIComponent(moduleUrl)}`,
      path,
    );
  }
});

test("Shadowrocket imports accept HEAD and ignore user-controlled query values", async () => {
  const configResponse = await request(
    "/sr/config?destination=https%3A%2F%2Fevil.example%2Fconfig",
    "HEAD",
  );

  assert.equal(configResponse.status, 302);
  assert.equal(await configResponse.text(), "");
  assert.equal(
    configResponse.headers.get("location"),
    `shadowrocket://config/add/${PUBLIC_REPOSITORY}/shadowrocket.conf`,
  );

  const moduleResponse = await request(
    "/sr/modules/gfn?module=https%3A%2F%2Fevil.example%2Fmodule",
  );

  assert.equal(moduleResponse.status, 302);
  assert.equal(
    moduleResponse.headers.get("location"),
    `shadowrocket://install?module=${encodeURIComponent(
      `${PUBLIC_REPOSITORY}/modules/GFN-AM.module`,
    )}`,
  );
});

test("unknown Shadowrocket imports return 404", async () => {
  const response = await request("/sr/modules/unknown");

  assert.equal(response.status, 404);
  assert.doesNotMatch(await response.text(), /shadowrocket:/);
});

test("redirects disable caching and referrers", async () => {
  const response = await request("/");

  assert.equal(response.headers.get("cache-control"), "no-store");
  assert.equal(response.headers.get("referrer-policy"), "no-referrer");
  assert.equal(response.headers.get("x-content-type-options"), "nosniff");
});

test("unknown paths return 404 without exposing a deeplink", async () => {
  const response = await request("/missing");

  assert.equal(response.status, 404);
  assert.doesNotMatch(await response.text(), /happ:/);
});

test("unknown INCY paths return 404 without exposing a deeplink", async () => {
  const response = await request("/incy/missing");

  assert.equal(response.status, 404);
  assert.doesNotMatch(await response.text(), /incy:/);
});

test("unsupported methods return 405 on a known path", async () => {
  const response = await request("/", "POST");

  assert.equal(response.status, 405);
  assert.equal(response.headers.get("allow"), "GET, HEAD");
});
