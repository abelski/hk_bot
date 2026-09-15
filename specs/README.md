# Specs

Living descriptions of current behaviour, one file per component.

## News sources

Each command fetches from one kind of source, rewrites it through the shared
[rewrite pipeline](rewrite-pipeline.md), and posts to Telegram. All run hourly.

| Spec | Source | Configured in | State file |
|---|---|---|---|
| [youtube](youtube.md) | 6 YouTube channels | `youtube_channels` | `youtube_state.json` |
| [iksurfmag](iksurfmag.md) | [IKSurfMag news RSS](https://www.iksurfmag.com/kitesurfing-news/feed/) | hardcoded | `iksurfmag_state.json` |
| [instagram](instagram.md) | 26 rider/brand accounts | `instagram_accounts` | `instagram_state.json` |
| [kitegirl](kitegirl.md) | 22 female-rider accounts | `kitegirl_accounts` | `kitegirl_state.json` |
| [facebook](facebook.md) | 1 page | `facebook_pages` | `facebook_state.json` |
| [hkr](hkr.md) | [Honest Kite Reviews API](https://honestkitereviews.com/api/reviews) | hardcoded | `hkr_state.json` |

Not yet specced: `woo`, `surfr`, `windguru` — data/leaderboard commands that don't use the
rewrite pipeline.

## External services

| Service | Used by | Credential |
|---|---|---|
| [Groq chat completions](https://api.groq.com/openai/v1/chat/completions) | [rewrite pipeline](rewrite-pipeline.md) | `GROQ_API_KEY` |
| [MyMemory translation](https://api.mymemory.translated.net/get) | [rewrite pipeline](rewrite-pipeline.md) | none |
| [Instagram web profile API](https://i.instagram.com/api/v1/users/web_profile_info/) | [instagram](instagram.md), [kitegirl](kitegirl.md) | iPhone UA + app id |
| Instagram proxy worker ([cloudflare/](../cloudflare/)) | [instagram](instagram.md), [kitegirl](kitegirl.md) | `INSTAGRAM_PROXY_URL`, `INSTAGRAM_PROXY_TOKEN` |
| YouTube (via `yt_dlp`) | [youtube](youtube.md), [iksurfmag](iksurfmag.md) | none |
| Facebook (via `facebook_scraper`) | [facebook](facebook.md) | none |
| Telegram Bot API | delivery | `TELEGRAM_BOT_TOKEN` |

## Destination

Posts go to the recipients named in `config.json: mappings` — currently `main_group` for every
command. `_append_footer` in `src/bot.py` appends `config.json: post_footer` to every outgoing
post, currently a link to [HateKite](https://t.me/hatekite).

## Overlapping sources

`dontpullthebar` is followed on three platforms — [YouTube](youtube.md#sources),
[Instagram](instagram.md#sources) and [Facebook](facebook.md#sources) — and Gisela Pulido is
followed under two different handles across [instagram](instagram.md#sources) and
[kitegirl](kitegirl.md#sources). State is per-command, so the same content can post more than
once; there is no cross-command deduplication.
