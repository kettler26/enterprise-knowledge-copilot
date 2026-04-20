export default {
  async fetch(request, env) {
    const incoming = new URL(request.url);
    const target = new URL(env.COPILOT_API_BASE_URL + incoming.pathname + incoming.search);

    const headers = new Headers(request.headers);
    headers.set("x-forwarded-host", incoming.host);

    const forwarded = new Request(target.toString(), {
      method: request.method,
      headers,
      body: request.body,
      redirect: "follow",
    });
    return fetch(forwarded);
  },
};
export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    const target = new URL(env.COPILOT_API_BASE_URL + url.pathname + url.search);

    const headers = new Headers(request.headers);
    headers.set("x-forwarded-host", url.host);

    return fetch(new Request(target.toString(), {
      method: request.method,
      headers,
      body: request.body,
      redirect: "follow",
    }));
  },
};
