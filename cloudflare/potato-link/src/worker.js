import { DESTINATIONS } from "../dist/destinations.js";


const PUBLIC_REPOSITORY = "https://raw.githubusercontent.com/Simonerrror/ShadowRocket/main";
const CONFIG_URL = `${PUBLIC_REPOSITORY}/shadowrocket.conf`;
const MODULES = Object.freeze({
  "dns-override": "dns_override.module",
  "google-ai": "google_ai_smart_dns_mobile.module",
  "openai-usa": "openai_usa.module",
  "twitch-poland": "twitch_poland.module",
  "anti-advertising": "anti_advertising.module",
  "gfn": "GFN-AM.module",
  "apple": "apple_proxy.module",
  "wechat": "wechat_direct.module",
  "tailscale-direct": "tailscale_direct.module",
  "tailscale-tailnet": "tailscale_tailnet.module",
});
const SHADOWROCKET_IMPORTS = new Map([
  ["/sr/config", `shadowrocket://config/add/${CONFIG_URL}`],
  ...Object.entries(MODULES).map(([slug, filename]) => [
    `/sr/modules/${slug}`,
    `shadowrocket://install?module=${encodeURIComponent(`${PUBLIC_REPOSITORY}/modules/${filename}`)}`,
  ]),
]);

const PATHS = new Map([
  ["/incy", DESTINATIONS.incyDefault],
  ["/incy/ru", DESTINATIONS.incyRu],
  ...SHADOWROCKET_IMPORTS,
]);

const TEXT_HEADERS = {
  "content-type": "text/plain; charset=utf-8",
  "x-content-type-options": "nosniff",
};


export default {
  fetch(request, env) {
    const pathname = new URL(request.url).pathname;
    if (pathname === "/links" || pathname === "/links/") {
      return new Response(null, {status: 302, headers: {location: "/"}});
    }
    if (env?.ASSETS && !PATHS.has(pathname) &&
        (request.method === "GET" || request.method === "HEAD")) {
      return env.ASSETS.fetch(request);
    }
    const destination = PATHS.get(new URL(request.url).pathname);
    if (destination === undefined) {
      return new Response("Not found\n", {
        status: 404,
        headers: TEXT_HEADERS,
      });
    }
    if (request.method !== "GET" && request.method !== "HEAD") {
      return new Response("Method not allowed\n", {
        status: 405,
        headers: {
          ...TEXT_HEADERS,
          allow: "GET, HEAD",
        },
      });
    }
    return new Response(null, {
      status: 302,
      headers: {
        location: destination,
        "cache-control": "no-store",
        "referrer-policy": "no-referrer",
        "x-content-type-options": "nosniff",
      },
    });
  },
};
