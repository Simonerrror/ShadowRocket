import assert from "node:assert/strict";
import test from "node:test";

import worker from "../src/worker.js";


const primaryLinks = Array.from(
  { length: 5 },
  (_, index) => `wg://primary-${index}.example:443?privateKey=key${index}#P${index}`,
);
const secondaryLinks = Array.from(
  { length: 5 },
  (_, index) => `wg://secondary-${index}.example:443?privateKey=key${index + 5}#S${index}`,
);
const env = {
  PRIMARY_PATH: "/s/primary-token-12345678901234567890",
  SECONDARY_PATH: "/s/secondary-token-1234567890123456",
  ...Object.fromEntries(primaryLinks.map((link, index) => [`PRIMARY_LINK_${index + 1}`, link])),
  ...Object.fromEntries(secondaryLinks.map((link, index) => [`SECONDARY_LINK_${index + 1}`, link])),
};


function request(path, method = "GET", bindings = env) {
  return worker.fetch(
    new Request(`https://potato-box.example${path}`, { method }),
    bindings,
  );
}


test("each exact bearer path serves only its five-profile feed", async () => {
  const primary = await request(env.PRIMARY_PATH);
  const secondary = await request(env.SECONDARY_PATH);

  assert.equal(primary.status, 200);
  assert.equal(await primary.text(), `${primaryLinks.join("\n")}\n`);
  assert.equal(secondary.status, 200);
  assert.equal(await secondary.text(), `${secondaryLinks.join("\n")}\n`);
  assert.equal(primary.headers.get("content-type"), "text/plain; charset=utf-8");
  assert.equal(primary.headers.get("cache-control"), "private, no-store");
  assert.equal(primary.headers.get("referrer-policy"), "no-referrer");
  assert.equal(primary.headers.get("x-content-type-options"), "nosniff");
  assert.equal(primary.headers.get("x-robots-tag"), "noindex, nofollow, noarchive");
});

test("HEAD validates a known feed but returns no credentials", async () => {
  const response = await request(env.PRIMARY_PATH, "HEAD");

  assert.equal(response.status, 200);
  assert.equal(await response.text(), "");
  assert.equal(response.headers.get("content-length"), null);
});

test("unknown paths reveal neither routes nor feeds", async () => {
  for (const path of ["/", "/s", "/s/wrong", `${env.PRIMARY_PATH}/extra`]) {
    const response = await request(path);
    const body = await response.text();
    assert.equal(response.status, 404);
    assert.equal(body, "Not found\n");
    assert.doesNotMatch(body, /wg:|primary|secondary|token/i);
  }
});

test("unsupported methods are rejected only after an exact route match", async () => {
  const known = await request(env.SECONDARY_PATH, "POST");
  const unknown = await request("/missing", "POST");

  assert.equal(known.status, 405);
  assert.equal(known.headers.get("allow"), "GET, HEAD");
  assert.equal(unknown.status, 404);
});

test("missing or malformed feed fails closed without echoing bindings", async () => {
  const missing = await request(env.PRIMARY_PATH, "GET", {
    ...env,
    PRIMARY_LINK_3: undefined,
  });
  const malformed = await request(env.SECONDARY_PATH, "GET", {
    ...env,
    SECONDARY_LINK_4: "not-a-wg-link",
  });

  for (const response of [missing, malformed]) {
    const body = await response.text();
    assert.equal(response.status, 503);
    assert.equal(body, "Unavailable\n");
    assert.doesNotMatch(body, /wg:|primary|secondary|token/i);
  }
});
