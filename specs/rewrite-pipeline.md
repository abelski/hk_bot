# Rewrite pipeline

Shared machinery that turns foreign-language source material into Russian Telegram posts in
the channel's voice. Every news source depends on this; each source's own spec describes how
it fetches content and what it does when a rewrite is unavailable.

Per-source specs: [youtube](youtube.md) · [iksurfmag](iksurfmag.md) ·
[instagram](instagram.md) · [kitegirl](kitegirl.md) · [facebook](facebook.md) · [hkr](hkr.md)

## Components

| File | Role |
|---|---|
| `src/helpers/rewrite_helper.py` | Stylised rewrite into Russian via Groq |
| `src/helpers/rewrite_prompt.txt` | System prompt defining the channel's voice |
| `src/helpers/translation_helper.py` | Literal fallback translation via MyMemory |

## External services

| Link | Use | Credential |
|---|---|---|
| [api.groq.com/openai/v1/chat/completions](https://api.groq.com/openai/v1/chat/completions) | Stylised rewrite | `GROQ_API_KEY` |
| [api.groq.com/openai/v1/models](https://api.groq.com/openai/v1/models) | Check which models still exist — first thing to hit when quality drops | `GROQ_API_KEY` |
| [api.mymemory.translated.net/get](https://api.mymemory.translated.net/get) | Literal en→ru fallback | none |

## Destination

Posts go to the recipients in `config.json: mappings` — currently `main_group` for every
command, on an hourly cron (`woo` daily at 20:00). Each post gets `config.json: post_footer`
appended by the bot, currently a link to [HateKite](https://t.me/hatekite); the prompt forbids
the model from adding its own signature so this isn't duplicated.

Two independent services with deliberately opposite failure contracts. Confusing them is the
single most common source of bugs here.

## `rewrite_to_russian(title, text) -> str | None`

Posts `f"{title}\n\n{text}"` (or just `text` when title is empty), truncated to 4000
characters, to Groq's chat-completions endpoint.

Parameters, all load-bearing:

- `model: "openai/gpt-oss-120b"`
- `max_tokens: 600`
- `reasoning_effort: "low"` — gpt-oss is a reasoning model. Without this it spends the whole
  budget on hidden reasoning and returns `content: ""` with `finish_reason: "length"`. An
  empty string is *not* `None`, so callers treat it as a successful rewrite and post a blank
  body. Removing this parameter silently empties posts.
- `timeout: 30`

**Returns `None` on any failure** — missing `GROQ_API_KEY`, HTTP error, timeout, malformed
response. All exceptions are swallowed and nothing is logged, so an outage is invisible except
as a drop in post quality.

The system prompt is read **once at import time**. Changing `rewrite_prompt.txt` requires a bot
restart; pushing the file alone has no effect.

`strip_hashtags(text)` removes `#hashtag` tokens; used by the caption-based sources.

### Prompt contract

Rules that exist specifically because the model violated them in production:

- **Russian only.** Any surviving English — especially the source title — invalidates output.
- **No bare title translation.** Input arrives as `title\n\ntext`; the model must fuse it into
  one voiced post instead of echoing the two-part structure back.
- **No invented claims.** Opinion must react to what the source actually says. The model once
  fabricated a reliability complaint about a harness from neutral marketing copy.
- **No signature.** The channel footer is appended separately by the bot from
  `config.json: post_footer`; a model-added one duplicates it.

`## ANTI-EXAMPLES` holds concrete bad outputs for the first and third rules.

## `translate_to_russian(text) -> str`

Literal en→ru translation via MyMemory. Splits into ≤500-character chunks on paragraph then
sentence boundaries, translates each with one retry, joins with blank lines.

**Returns its input unchanged on failure.** This is the documented contract, and comparing
output to input is the only way callers can detect that translation failed.

## Two consumer shapes

**Title + body** — [youtube](youtube.md), [iksurfmag](iksurfmag.md). Title is translated
*separately* and always literally; only the body is rewritten, and the body is dropped
entirely rather than emitting source-language text. Full degradation ladder in those specs.

**Caption** — [instagram](instagram.md), [kitegirl](kitegirl.md), [facebook](facebook.md),
[hkr](hkr.md). `rewrite_to_russian(...) or <original text>` — these fall back to the **untouched
source text**, so they can and do post English by design.

## Operational notes

- **Groq retires models without notice.** `llama-3.3-70b-versatile` was removed and every
  rewrite silently failed until the model was swapped. If quality drops suddenly, check
  `GET https://api.groq.com/openai/v1/models` before anything else.
- **Cloudflare fronts the Groq API** and rejects urllib's default User-Agent with
  `403 error code: 1010`. `requests` works; ad-hoc scripts need an explicit UA header.
- **Free-tier rate limits** bite quickly on reasoning models; space out batch calls.

## Testing

Never assert on exact rewritten text — output varies per run and exact-match assertions break
on harmless rewording. Patch `rewrite_to_russian` / `translate_to_russian` and assert on the
composed result. Fallback behaviour is covered in `tests/test_commands.py`.
