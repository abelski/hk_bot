# iksurfmag

Posts the latest article from IKSurfMag's kitesurfing news RSS feed.
`src/commands/iksurfmag_command.py`. Uses the shared [rewrite pipeline](rewrite-pipeline.md).

| | |
|---|---|
| Source | `https://www.iksurfmag.com/kitesurfing-news/feed/` |
| State | `iksurfmag_state.json` → `{"last_url": <article url>}` |
| Schedule | hourly (`config.json: mappings`) |

## Sources

Hardcoded in `iksurfmag_command.py` (`_RSS_URL`), not configurable.

| Link | Use |
|---|---|
| [iksurfmag.com/kitesurfing-news/feed/](https://www.iksurfmag.com/kitesurfing-news/feed/) | RSS feed — titles, links, media, fallback body |
| [iksurfmag.com](https://www.iksurfmag.com) | Article pages, scraped for full body text and video embeds |
| `https://www.youtube.com/watch?v=<id>` | Recovered from page embeds or feed thumbnails |

Single source, so no config list and no per-account iteration: `run()` always posts the newest
article, `run_if_new()` posts it only when its URL differs from stored state.

## Fetch

RSS is fetched with 2 retries (1 s apart) and the **first `<item>`** is taken. Everything else
is scraped from the article page itself, because the feed's own content is truncated and
wrapped in promotional boilerplate.

### Article body

Fetch the page, then from `.single-post` remove `.share-floater`, `section`, `.row`,
`.solo-bleed`, `.sharedaddy`, `script`, `style` — these carry related-article lists, the
subscribe promo and like counts. From what remains, collect **classless `<p>` tags only**;
styled paragraphs are captions and callouts, not article prose.

If that yields nothing, fall back to the feed's `content:encoded` (else `description`),
dropping paragraphs containing `first appeared` or `full article` — IKSurfMag's syndication
footer.

### Video

YouTube embeds on the page are **lazy-loaded via `data-src`, not `src`** — matching on `src`
finds nothing. The embed URL is converted to a watch URL.

If no embed is found, two feed fallbacks: `media:content` with `medium="video"`, or a
`ytimg.com/vi/<id>/` thumbnail, from which the video id is recovered by regex. The thumbnail
case exists because IKSurfMag labels YouTube thumbnails as `medium="image"`.

### Image

Only used when there is **no video** and the media URL isn't a `ytimg.com` thumbnail. Downloaded
to bytes; failure is swallowed and the post goes out text-only.

## Output

```
*<title translated literally>*

<rewritten body>          # omitted entirely when unavailable
```

Plus, in priority order: the downloaded video; or the video URL appended to the text if the
download failed; or a single photo; or nothing.

## Body degradation ladder

Identical to [youtube](youtube.md#body-degradation-ladder): rewrite → literal translation of the
first 500 characters → body omitted. The same rule applies — never fall back to emitting
source-language text.

This duplication is intentional but unguarded: `_format` here and in `youtube_command.py` are
near-identical, and a fix to one needs applying to the other.

## Gotchas

- Scraping is coupled to IKSurfMag's markup. A site redesign breaks body extraction silently —
  the feed fallback then supplies short, boilerplate-stripped text, so posts get shorter rather
  than failing loudly.
- A custom `User-Agent` (`kitesurf-bot/1.0`) is sent on all requests.
