# hkr

Posts the latest gear review from Honest Kite Reviews.
`src/commands/hkr_command.py`. Uses the shared [rewrite pipeline](rewrite-pipeline.md).

| | |
|---|---|
| Source | `https://honestkitereviews.com/api/reviews` |
| State | `hkr_state.json` → `{"last_id": <review id>}` |
| Schedule | hourly (`config.json: mappings`) |

## Sources

Hardcoded in `hkr_command.py` (`_API_URL`), not configurable.

| Link | Use |
|---|---|
| [honestkitereviews.com/api/reviews](https://honestkitereviews.com/api/reviews) | JSON list of reviews, newest first |
| [honestkitereviews.com](https://honestkitereviews.com) | The site itself; not linked from posts |

Posts carry no link back to the review — readers get the full text inline.

A plain JSON API rather than scraping — the most reliable of the sources. Fetched with 2 retries
(1 s apart), taking `reviews[0]`. Single source, so no config list: `run()` always posts the
newest review, `run_if_new()` only when its `id` differs from stored state.

## Output

Unlike the other sources, the post is a **fixed template** and only one field is rewritten:

```
*<productName>*
Brand: <brand> | Type: <productType>

<rewritten writeUp>

Safety: <safetyStatus> | Reviewed by <firstName> <lastName>
```

Consequences worth knowing:

- The **structural labels stay in English** (`Brand`, `Type`, `Safety`, `Reviewed by`), so these
  posts are bilingual by design, unlike every other source.
- The **product name is never translated** — correct, since it's a model name.
- `safetyStatus` is prettified from a slug: `-` → space, then title-cased (`not-recommended` →
  `Not Recommended`). Defaults to `unknown`.
- Only `writeUp` passes through the rewrite, with `productName` supplied as context. It **falls
  back to the original English review text** when the rewrite fails, matching the caption-style
  sources rather than the title+body ones.

## Images

`review["images"]` holds base64 strings, optionally as data URIs — anything containing a comma is
split and only the part after it decoded. Individual decode failures are skipped silently, so a
malformed image costs that photo, not the post.

## Gotchas

- The rewrite is called **inline inside an f-string**, so its 30 s timeout sits on the post-
  assembly path with no way to distinguish a slow call from a failed one.
- No `\n\n` normalisation: if `writeUp` is empty and the rewrite returns nothing, the post ships
  with a visible gap between the header and the safety line.
- Review `id` is the state key; if the API ever reorders or reissues ids, the bot either re-posts
  or goes silent.
