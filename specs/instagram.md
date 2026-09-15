# instagram

Posts the latest post from a configured list of pro-rider Instagram accounts.
`src/commands/instagram_command.py`. Uses the shared [rewrite pipeline](rewrite-pipeline.md).

| | |
|---|---|
| Config key | `instagram_accounts` — list of usernames |
| State | `instagram_state.json` → `{username: shortcode}` |
| Schedule | hourly (`config.json: mappings`) |

[kitegirl](kitegirl.md) is a byte-for-byte clone of this command with a different account list.
Any change here must be mirrored there.

## Sources

Configured in `config.json: instagram_accounts` (authoritative — this list is a snapshot).
Order matters: iteration stops at the first account with a new post, so accounts near the top
dominate the feed.

Brands and media: [dontpullthebar_official](https://www.instagram.com/dontpullthebar_official/) ·
[kitereels](https://www.instagram.com/kitereels/) ·
[the.quickrelease](https://www.instagram.com/the.quickrelease/)

Riders: [aaronhadlow](https://www.instagram.com/aaronhadlow/) ·
[kevinlangeree](https://www.instagram.com/kevinlangeree/) ·
[liamwhaley](https://www.instagram.com/liamwhaley/) ·
[airtoncozzolino](https://www.instagram.com/airtoncozzolino/) ·
[nick_jacobsen](https://www.instagram.com/nick_jacobsen/) ·
[giselapulido](https://www.instagram.com/giselapulido/) ·
[alexpastorkite](https://www.instagram.com/alexpastorkite/) ·
[nicoprl01](https://www.instagram.com/nicoprl01/) ·
[jesserichman](https://www.instagram.com/jesserichman/) ·
[marcjacobskite](https://www.instagram.com/marcjacobskite/) ·
[lorenzo__casati](https://www.instagram.com/lorenzo__casati/) ·
[andrea_principi04](https://www.instagram.com/andrea_principi04/) ·
[mikaili_sol](https://www.instagram.com/mikaili_sol/) ·
[capucine_delannoy](https://www.instagram.com/capucine_delannoy/) ·
[charlesbrodel](https://www.instagram.com/charlesbrodel/) ·
[jamesscarew](https://www.instagram.com/jamesscarew/) ·
[camille_losserand](https://www.instagram.com/camille_losserand/) ·
[cescamaini](https://www.instagram.com/cescamaini/) ·
[jeremyburlandokiter](https://www.instagram.com/jeremyburlandokiter/) ·
[zarahoogenraad](https://www.instagram.com/zarahoogenraad/) ·
[andrea_zust](https://www.instagram.com/andrea_zust/) ·
[nathalie_lambrecht](https://www.instagram.com/nathalie_lambrecht/) ·
[hugo.wigglesworth](https://www.instagram.com/hugo.wigglesworth/)

Note `giselapulido` here versus `gisela_pulido` in [kitegirl](kitegirl.md) — two different
handles for the same rider, so both lists may fire on the same content.

### Endpoints

| Link | Use |
|---|---|
| `https://i.instagram.com/api/v1/users/web_profile_info/` | Direct transport (no proxy configured) |
| `$INSTAGRAM_PROXY_URL/?username=<name>` | Proxy transport — the worker in [cloudflare/](../cloudflare/) |
| `https://www.instagram.com/p/<shortcode>/` | Canonical post URL, built but not currently posted |

## Fetch

Two transports, chosen at import time:

- **Proxy** — when `INSTAGRAM_PROXY_URL` is set: `GET <proxy>/?username=<name>` with an
  `X-Proxy-Token` header. This is the Cloudflare worker in `cloudflare/`, which holds the
  session cookie.
- **Direct** — otherwise `https://i.instagram.com/api/v1/users/web_profile_info/` with an
  iPhone User-Agent and the public web `X-IG-App-ID`.

Status handling is deliberately asymmetric, because Instagram's responses mean different things:

| Response | Behaviour |
|---|---|
| 401 / 403 | **Return `None` immediately, no retry** — auth is broken; retrying wastes the rate budget and deepens the block |
| 429 | Sleep `10 × (attempt+1)` s and retry, up to 2 retries |
| other errors | Sleep 5 s and retry, up to 2 retries |

Accounts are walked with a **3 s gap between them** to stay under rate limits. Both entry points
return on the first match, so one invocation posts at most once and early accounts in the list
are effectively higher priority.

## Post selection

Takes the **first non-pinned** post from the timeline, falling back to the first post if all are
pinned. Without this, a pinned post would be re-posted as "latest" forever.

Media extraction:
- **Video** — `video_url` when `is_video`.
- **Photos** — sidecar (carousel) children, **max 4**, video children skipped; otherwise the
  single `display_url`. Failed downloads are filtered out.

## Output

```
<rewritten caption>
```

No title line — unlike the title+body sources, this is caption-only. Attached media in priority
order: video, else photos, else text alone.

## Caption handling

```python
raw = strip_hashtags(caption[:900])
text = rewrite_to_russian(username, raw) or raw or ""
```

The caption is truncated to 900 characters **before** rewriting and hashtags are stripped, since
they add nothing once the text is in Russian. The account username is passed as the `title`
argument, giving the model the rider's name as context.

**Falls back to the original caption** when the rewrite fails — so this source posts untranslated
English (or Portuguese, Spanish…) by design, rather than dropping the text. That differs from
[youtube](youtube.md) / [iksurfmag](iksurfmag.md), where source-language text is never emitted;
here there is no translated title above it to contradict.

## Gotchas

- `_PROXY_URL` / `_PROXY_TOKEN` are read at **import time**, so changing them needs a restart.
- State is keyed by username; renaming an account in config re-posts its latest post once.
