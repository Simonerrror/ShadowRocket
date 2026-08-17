import { DESTINATIONS } from "../dist/destinations.js";


const PATHS = new Map([
  ["/", DESTINATIONS.default],
  ["/ru", DESTINATIONS.ru],
  ["/incy", DESTINATIONS.incyDefault],
  ["/incy/ru", DESTINATIONS.incyRu],
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
