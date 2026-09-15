# youtube

Posts the latest video from a configured list of kitesurfing YouTube channels.
`src/commands/youtube_command.py`. Uses the shared [rewrite pipeline](rewrite-pipeline.md).

| | |
|---|---|
| Config key | `youtube_channels` — list of channel URLs |
| State | `youtube_state.json` → `{"last_urls": {channel_url: video_url}}` |
| Schedule | hourly (`config.json: mappings`) |

## Sources

Configured in `config.json: youtube_channels` (authoritative — this list is a snapshot).
Order matters: iteration stops at the first channel with a new video.

1. [@gethighwithmike](https://www.youtube.com/@gethighwithmike)
2. [@dontpullthebar](https://www.youtube.com/@dontpullthebar)
3. [@antonchernyshov8759](https://www.youtube.com/@antonchernyshov8759)
4. [@New_Generation_KiteContent](https://www.youtube.com/@New_Generation_KiteContent)
5. [@stevenakkersdijk](https://www.youtube.com/@stevenakkersdijk)
6. [@Prydeclub](https://www.youtube.com/@Prydeclub)

`@dontpullthebar` also publishes to [instagram](instagram.md) and [facebook](facebook.md), so the
same content can reach the channel up to three times through different commands.

Endpoints used: `<channel>/videos` for the listing and
`https://www.youtube.com/watch?v=<id>` for full metadata, both via `yt_dlp`.

## Fetch

Two `yt_dlp` calls per channel, by necessity:

1. `<channel_url>/videos` with `extract_flat` and `playlist_items: "1"` — cheap, returns the
   newest video's id but **omits the description**.
2. The resulting watch URL with full extraction, to get `description` and the canonical title.

If the second call fails, the video is still posted with `description: ""` and the title from
the flat entry — which means the body falls through the whole degradation ladder to nothing.

Any exception returns `None` and the channel is skipped.

## Selection

Both entry points iterate channels **in config order and return on the first match**, so one
invocation yields at most one post:

- `run()` (manual `/youtube`) — first channel that responds at all, regardless of whether that
  video was already posted.
- `run_if_new()` (cron) — first channel whose newest video differs from stored state.

Consequence: this is "first new video found in list order", not "newest video across all
channels". Channels early in the list are effectively higher priority.

## Output

```
*<title translated literally>*

<rewritten body>          # omitted entirely when unavailable
```

Then the video itself: `download_youtube_video(url)` returns bytes (best progressive MP4 up to
720p, for Telegram's 50 MB limit). **If the download fails, the watch URL is appended to the
text instead** — so a post is always produced, just as a link.

## Body degradation ladder

1. Groq rewrite of title + description.
2. On `None` — literal translation of the first 500 characters of the description.
3. If translation returned its input unchanged (i.e. it failed too) — **body omitted**.

Stage 3 exists because the previous fallback inserted the raw English title as the body,
producing posts with the Russian title followed by the same title in English. Never reintroduce
a fallback that emits source-language text; dropping the body is the correct degradation.

The title is always translated by `translate_to_russian`, never by the rewrite, so a post can
legitimately have a literal title above a voiced body.

## Gotchas

- The title is wrapped in `*...*` Telegram markdown. Titles containing `*` or `_` can break
  formatting; nothing escapes them.
- State is keyed by channel URL. Editing a URL in config (even adding a trailing slash) orphans
  its old entry and re-posts that channel's latest video once.
