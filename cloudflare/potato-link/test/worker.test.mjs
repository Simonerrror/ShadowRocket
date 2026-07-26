import assert from "node:assert/strict";
import test from "node:test";

import { DESTINATIONS } from "../dist/destinations.js";
import worker from "../src/worker.js";


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

test("HEAD redirects without a body", async () => {
  const response = await request("/ru", "HEAD");

  assert.equal(response.status, 302);
  assert.equal(await response.text(), "");
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

test("unsupported methods return 405 on a known path", async () => {
  const response = await request("/", "POST");

  assert.equal(response.status, 405);
  assert.equal(response.headers.get("allow"), "GET, HEAD");
});
