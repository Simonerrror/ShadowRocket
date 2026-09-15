import { DESTINATIONS } from "../dist/destinations.js";


const PUBLIC_REPOSITORY = "https://raw.githubusercontent.com/Simonerrror/ShadowRocket/main";
const CONFIG_URL = `${PUBLIC_REPOSITORY}/shadowrocket.conf`;
const MODULE_URLS = Object.freeze({
  tailscaleDirect: `${PUBLIC_REPOSITORY}/modules/tailscale_direct.module`,
  tailscaleTailnet: `${PUBLIC_REPOSITORY}/modules/tailscale_tailnet.module`,
  gfn: `${PUBLIC_REPOSITORY}/modules/GFN-AM.module`,
  wechat: `${PUBLIC_REPOSITORY}/modules/wechat_direct.module`,
  twitch: `${PUBLIC_REPOSITORY}/modules/twitch_video_direct.module`,
  antiAdvertising: `${PUBLIC_REPOSITORY}/modules/anti_advertising.module`,
});

const SHADOWROCKET_IMPORTS = new Map([
  ["/sr/config", `shadowrocket://config/add/${CONFIG_URL}`],
  [
    "/sr/modules/tailscale-direct",
    `shadowrocket://install?module=${encodeURIComponent(MODULE_URLS.tailscaleDirect)}`,
  ],
  [
    "/sr/modules/tailscale-tailnet",
    `shadowrocket://install?module=${encodeURIComponent(MODULE_URLS.tailscaleTailnet)}`,
  ],
  [
    "/sr/modules/gfn",
    `shadowrocket://install?module=${encodeURIComponent(MODULE_URLS.gfn)}`,
  ],
  [
    "/sr/modules/wechat",
    `shadowrocket://install?module=${encodeURIComponent(MODULE_URLS.wechat)}`,
  ],
  [
    "/sr/modules/twitch",
    `shadowrocket://install?module=${encodeURIComponent(MODULE_URLS.twitch)}`,
  ],
  [
    "/sr/modules/anti-advertising",
    `shadowrocket://install?module=${encodeURIComponent(MODULE_URLS.antiAdvertising)}`,
  ],
]);


const PATHS = new Map([
  ["/", DESTINATIONS.default],
  ["/ru", DESTINATIONS.ru],
  ["/incy", DESTINATIONS.incyDefault],
  ["/incy/ru", DESTINATIONS.incyRu],
  ...SHADOWROCKET_IMPORTS,
]);

const TEXT_HEADERS = {
  "content-type": "text/plain; charset=utf-8",
  "x-content-type-options": "nosniff",
};


export default {
  fetch(request) {
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
