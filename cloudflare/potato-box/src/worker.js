const TEXT_HEADERS = {
  "content-type": "text/plain; charset=utf-8",
  "cache-control": "private, no-store",
  "referrer-policy": "no-referrer",
  "x-content-type-options": "nosniff",
  "x-robots-tag": "noindex, nofollow, noarchive",
};


function validPath(value) {
  return typeof value === "string" && /^\/s\/[A-Za-z0-9_-]{32,128}$/.test(value);
}


function feedFor(prefix, env) {
  const links = Array.from(
    { length: 5 },
    (_, index) => env[`${prefix}_LINK_${index + 1}`],
  );
  if (links.some((link) => (
    typeof link !== "string"
    || !link.startsWith("wg://")
    || link.includes("\n")
    || link.includes("\r")
  ))) {
    return null;
  }
  return `${links.join("\n")}\n`;
}


function route(pathname, env) {
  if (validPath(env.PRIMARY_PATH) && pathname === env.PRIMARY_PATH) {
    return "PRIMARY";
  }
  if (validPath(env.SECONDARY_PATH) && pathname === env.SECONDARY_PATH) {
    return "SECONDARY";
  }
  return null;
}


function textResponse(body, status, extraHeaders = {}) {
  return new Response(body, {
    status,
    headers: {
      ...TEXT_HEADERS,
      ...extraHeaders,
    },
  });
}


export default {
  fetch(request, env) {
    const owner = route(new URL(request.url).pathname, env);
    if (owner === null) {
      return textResponse("Not found\n", 404);
    }
    if (request.method !== "GET" && request.method !== "HEAD") {
      return textResponse("Method not allowed\n", 405, { allow: "GET, HEAD" });
    }
    const feed = feedFor(owner, env);
    if (feed === null) {
      return textResponse("Unavailable\n", 503);
    }
    return new Response(request.method === "HEAD" ? null : feed, {
      status: 200,
      headers: TEXT_HEADERS,
    });
  },
};
