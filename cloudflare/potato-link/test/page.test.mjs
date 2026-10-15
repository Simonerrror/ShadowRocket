import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";
import worker from "../src/worker.js";

test("page offers working Worker imports for both clients and no empty links", async () => {
  const html = readFileSync(new URL("../public/index.html", import.meta.url), "utf8");
  const links = [...html.matchAll(/href="([^"]+)"/g)].map(match => match[1]);
  assert.ok(links.includes("https://t.me/AIDHDaily"));
  assert.ok(links.includes("https://t.me/eofvpnbot?start=nOnbIJq3"));
  assert.ok(links.includes("https://e0f.cx/login?ref=nOnbIJq3"));
  const imports = links.filter(link => link.startsWith("https://potato-link.motivato-potato.workers.dev/"));
  assert.ok(imports.some(link => link.endsWith("/sr/config")));
  assert.ok(imports.some(link => link.endsWith("/incy")));
  assert.ok(imports.some(link => link.endsWith("/incy/ru")));
  assert.equal(imports.filter(link => link.includes("/sr/modules/")).length, 5);
  assert.ok(links.some(link => link.endsWith("/sr/modules/dns-override")));
  assert.ok(links.some(link => link.endsWith("/sr/modules/google-ai")));
  assert.ok(!links.some(link => /whitelist|apple_proxy|wechat|tailscale|twitch/.test(link)));
  assert.ok(html.indexOf("Добавить в Shadowrocket") < html.indexOf("Блог ↗"));
  for (const link of imports) {
    const response = worker.fetch(new Request(link));
    assert.equal(response.status, 302, link);
    assert.match(response.headers.get("location"), /^(shadowrocket|incy):\/\//);
  }
  assert.ok(!links.some(link => !link || link === "#" || link.includes("YOUR_")));
  assert.match(html, /<html lang="ru">/);
  assert.match(html, /name="viewport"/);
});
