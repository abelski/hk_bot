export default {
  async fetch(request, env) {
    const token = request.headers.get("X-Proxy-Token");
    if (!env.PROXY_TOKEN || token !== env.PROXY_TOKEN) {
      return new Response("Unauthorized", { status: 401 });
    }

    const url = new URL(request.url);
    const username = url.searchParams.get("username");
    if (!username) {
      return new Response("Missing username", { status: 400 });
    }

    const igUrl =
      "https://i.instagram.com/api/v1/users/web_profile_info/?username=" +
      encodeURIComponent(username);

    const igResponse = await fetch(igUrl, {
      headers: {
        "User-Agent":
          "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1",
        Accept: "*/*",
        "Accept-Language": "en-US,en;q=0.9",
        "X-IG-App-ID": "936619743392459",
      },
    });

    const body = await igResponse.text();
    return new Response(body, {
      status: igResponse.status,
      headers: { "Content-Type": "application/json" },
    });
  },
};
