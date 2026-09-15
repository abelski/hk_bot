# kitegirl

Posts the latest post from a configured list of female-rider Instagram accounts.
`src/commands/kitegirl_command.py`. Uses the shared [rewrite pipeline](rewrite-pipeline.md).

| | |
|---|---|
| Config key | `kitegirl_accounts` — list of usernames |
| State | `kitegirl_state.json` → `{username: shortcode}` |
| Schedule | hourly (`config.json: mappings`) |

## Sources

Configured in `config.json: kitegirl_accounts` (authoritative — this list is a snapshot).
Order matters: iteration stops at the first account with a new post.

Riders: [gisela_pulido](https://www.instagram.com/gisela_pulido/) ·
[brunakajiya](https://www.instagram.com/brunakajiya/) ·
[moana_pasquini](https://www.instagram.com/moana_pasquini/) ·
[valekeisel](https://www.instagram.com/valekeisel/) ·
[jennyholms](https://www.instagram.com/jennyholms/) ·
[floryros](https://www.instagram.com/floryros/) ·
[francescabagnoli_kite](https://www.instagram.com/francescabagnoli_kite/) ·
[karo_winkowska](https://www.instagram.com/karo_winkowska/) ·
[annalottacaudrelier](https://www.instagram.com/annalottacaudrelier/) ·
[lizkruk_kite](https://www.instagram.com/lizkruk_kite/) ·
[susimai_kite](https://www.instagram.com/susimai_kite/) ·
[paulanovotna_kite](https://www.instagram.com/paulanovotna_kite/) ·
[mathilde_bakker](https://www.instagram.com/mathilde_bakker/) ·
[claudia.schulz](https://www.instagram.com/claudia.schulz/) ·
[alexiafrey_kite](https://www.instagram.com/alexiafrey_kite/) ·
[stephbridge_kite](https://www.instagram.com/stephbridge_kite/) ·
[flo_kaupert](https://www.instagram.com/flo_kaupert/) ·
[sarablixt](https://www.instagram.com/sarablixt/) ·
[feliciaeden1](https://www.instagram.com/feliciaeden1/)

Community accounts: [kitegirlsclub](https://www.instagram.com/kitegirlsclub/) ·
[kitegirls_worldwide](https://www.instagram.com/kitegirls_worldwide/) ·
[kitegirlsitalia](https://www.instagram.com/kitegirlsitalia/)

`gisela_pulido` here is a different handle from `giselapulido` in
[instagram](instagram.md#sources) — same rider, two accounts, so both commands may post her
content independently.

Endpoints are identical to [instagram](instagram.md#endpoints): same direct API, same optional
proxy, same `INSTAGRAM_PROXY_URL` / `INSTAGRAM_PROXY_TOKEN` environment variables.

## Relationship to `instagram`

This command is a **copy of [instagram](instagram.md)**. Fetch transport, status-code handling,
retry and backoff timings, non-pinned post selection, media extraction, caption truncation and
rewrite behaviour are all character-identical.

The only differences:

| | instagram | kitegirl |
|---|---|---|
| `NAME` / `LABEL` | `instagram` / `Instagram 📸` | `kitegirl` / `Kite Girl 🪁` |
| Config key | `instagram_accounts` | `kitegirl_accounts` |
| State file | `instagram_state.json` | `kitegirl_state.json` |
| Empty-result message | `Could not fetch Instagram posts, please try again later.` | `No kite girl posts found.` |

Separate state files mean the two lists track independently; an account appearing in both is
posted once per command.

**Any behavioural fix — rate limiting, auth handling, caption logic — must be applied to both
files.** They have already drifted apart once in formatting (this file has no blank line between
the module constants and the class declaration), and nothing enforces that they stay in sync.

For all behaviour, see [instagram](instagram.md); it is the reference description.
