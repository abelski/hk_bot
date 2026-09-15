# facebook

Posts the latest post from a configured list of Facebook pages.
`src/commands/facebook_command.py`. Uses the shared [rewrite pipeline](rewrite-pipeline.md).

| | |
|---|---|
| Config key | `facebook_pages` — list of page names |
| State | `facebook_state.json` → `{page: post_id}` |
| Schedule | hourly (`config.json: mappings`) |

## Sources

Configured in `config.json: facebook_pages` (authoritative — this list is a snapshot).

- [dontpullthebar](https://www.facebook.com/dontpullthebar) — the only page currently configured

The same brand is also followed on [youtube](youtube.md#sources) (`@dontpullthebar`) and
[instagram](instagram.md#sources) (`dontpullthebar_official`), so one piece of their content can
reach the channel through three separate commands, each with its own state file and no
cross-command deduplication.

No fixed endpoint URL: `facebook_scraper` resolves the page itself.

## Fetch

Uses the third-party `facebook_scraper` package: `next(get_posts(page, pages=1), None)` — one
page of results, first post only.

Retries twice with escalating backoff (`10 × (attempt+1)` s), longer than the other sources
because scraping Facebook trips rate limiting readily. Pages are walked with a 3 s gap, and both
entry points return on the first match, so one invocation posts at most once.

Post text is read from `text`, falling back to `post_text`; `images` and `video` are URLs.

## Output

```
<rewritten post text>
```

Caption-only, no title line. Media in priority order: video (downloaded to bytes), else up to
**4** images, else text alone. Failed downloads are filtered out and the post still goes out.

## Text handling

```python
raw = strip_hashtags(text[:900])
text = rewrite_to_russian(page, raw) or raw or ""
```

Identical to [instagram](instagram.md#caption-handling): truncate to 900 characters, strip
hashtags, pass the page name as context, and **fall back to the original text** when the rewrite
fails — so untranslated source text can be posted by design.

## Gotchas

- `facebook_scraper` is the most fragile dependency in the project. It breaks whenever Facebook
  changes markup, and it is pinned (`0.2.59`) for that reason. Failures surface as the command
  simply finding no posts, not as errors.
- It transitively pulls an ancient `regex` wheel that current pip only warns about but **pip
  25.3 will reject outright**, which will break the CI dependency install when the runner's pip
  updates.
- Only one page is configured today (`dontpullthebar`), so "first match wins" iteration has no
  practical effect yet.
