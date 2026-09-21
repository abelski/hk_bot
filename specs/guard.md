# guard

Chat moderation for the community group: deletes and/or warns on rule matches (profanity, spam
links). `src/guard/bot.py` is the Telegram handler layer; `src/guard/moderation.py` is the pure
rule-matching logic (no Telegram dependency, unit-testable on its own).

| | |
|---|---|
| Config | `config.guard.json` → `moderation` key (deployed as that container's `config.json`) |
| Trigger | Every group text/caption message, via a `MessageHandler` |
| Container | Its own Proxmox LXC container and systemd service, entirely separate from the news bot |

## Rules

Each entry in `moderation.rules` has:

- `words` — stems matched with a Cyrillic-aware boundary (see below)
- `regex` — raw patterns matched case-insensitively against normalized text
- `action` — one of `warn`, `delete`, `delete_warn`
- `reason` — short label shown in the warning notice

A rule with an unknown `action`, or where every `words`/`regex` entry fails to compile to a
usable pattern (blank words, malformed regex), is dropped silently at compile time — logged as a
warning, never raised. The shipped `config.guard.json` carries two rules: a `delete_warn`
profanity rule keyed on a list of Russian obscenity stems, and a `delete` rule matching a handful
of spam-invite link shapes (`t.me/+…`, `t.me/joinchat/…`, shortened-link domains).

## Normalization

`normalize()` casefolds the text, folds `ё`→`е`, strips zero-width characters (a common filter
dodge), and collapses whitespace. This runs on the message text before matching, and is baked
into every compiled word pattern. Regex rules are matched against the same normalized haystack,
but the raw pattern itself is matched case-insensitively and only has `ё`/`Ё` folded to `е` at
compile time — not run through `normalize()` wholesale, since that would corrupt escapes like
`\S`.

## Word matching and Russian prefixes

`_word_pattern(word)` compiles `\b(?:<known prefix>)?<escaped stem>` for any word starting with
an alphanumeric or underscore character. Russian obscenity is prefix-productive — a prefix
("на-", "по-", "за-", "об-", …) glues directly onto the stem to form a new word ("нахуй",
"похуй", "заебал", "охуеть"), so a bare `\b` boundary only ever matches the bare stem and misses
the register that actually dominates casual Russian chat. Allowing one of a fixed list of known
prefixes between the boundary and the stem catches that whole family without opening the match up
to arbitrary text before the stem: "страхую" still doesn't match a "хую" stem, because "стра" is
not one of the listed prefixes, while "занихуярил"-style forms do.

Words whose first character isn't alnum/underscore (e.g. a `@handle`) skip the `\b` anchor
entirely, since a word boundary never matches before a non-word character and anchoring there
would make the pattern match nothing. Blank or whitespace-only word entries compile to `None` and
are dropped, rather than becoming a pattern that matches every message.

## Severity ladder and multiple matches

```
ACTIONS = {"warn": 1, "delete": 2, "delete_warn": 3}
```

When a message matches more than one rule, `find_action` keeps only the highest-ranked action —
`delete_warn` always beats `delete`, which always beats `warn` — and stops scanning early once
rank 3 is hit, since nothing outranks it. Rule order in the config never changes *which severity*
wins. It can, however, decide *which reason text* is shown: if two rules of the **same** rank
both match, the one that appears earlier in the config keeps its reason, since a later same-rank
match is skipped rather than overwriting the first.

## Exemptions

- The configured admin user id is always exempt, without a Telegram API call.
- Any chat administrator or creator is exempt, resolved via `bot.get_chat_member` on every
  matched message. If that lookup fails (bot lacks rights, transient Telegram error), the user is
  **not** treated as exempt — the message is still moderated. Both outcomes are logged, so an
  exempt-and-ignored message is distinguishable from the bot silently seeing nothing at all
  (which is what a Telegram privacy-mode misconfiguration looks like).
- Admins who post **anonymously as the group** (the `@GroupAnonymousBot` sender) carry a
  `sender_chat` instead of a resolvable personal id, so `get_chat_member` can't identify them.
  They're exempted whenever `sender_chat.id` equals the current chat's id — i.e. the anonymous
  post is this chat's own admin identity, not a `sender_chat` belonging to some other chat, which
  is still moderated normally.

## Scope

- Nothing runs unless `moderation.enabled` is true in config.
- `moderation.chats` is an allowlist of chat ids (as strings). An empty list means every chat the
  bot is a member of is moderated.
- Only group messages are handled (`filters.ChatType.GROUPS & (filters.TEXT | filters.CAPTION)`).
  Slash commands are deliberately not excluded from scanning, so a banned word inside a command
  (e.g. as an argument) is still caught rather than bypassing the rules.
- The scanned text is the message's visible text or caption, plus the `.url` of every text and
  caption entity — so a banned link hidden behind an innocuous-looking hyperlink label is still
  caught even though the displayed text is clean.

## Actions

- `delete` / `delete_warn`: the message is deleted. If the delete call fails (bot isn't an admin,
  message already gone), it's logged and handling stops there — no warning is sent for a message
  that's still visible.
- `warn` / `delete_warn`: a notice is sent to the chat naming the offender (`@username`, or their
  first name if they have none) and the reason. The wording differs by action ("нарушение" for a
  standalone warning, "сообщение удалено" when the message was also deleted). If
  `warn_ttl_seconds` (default 30) is nonzero and a job queue is available, the notice schedules
  its own deletion after that delay; a failure to delete it (already gone, etc.) is swallowed.

## Hot reload

There's no explicit reload step in the moderation path: `moderate()` reads the config file fresh
from disk on every single message, so an edit to the deployed config takes effect on the very
next message with no bot restart. What *is* cached is the compiled pattern list —
`compile_rules()` keeps a module-level cache keyed on a canonical JSON dump of the `moderation`
config block, so unchanged config isn't recompiled on every message, while any real edit produces
a different key and recompiles. The admin-only `/reload` command doesn't read or recompile
anything itself; since the reload already happens implicitly, it just replies with a confirmation
message.

## Startup notice

On startup, if an admin id is configured, the bot DMs it a summary: a deploy-version marker left
by the deploy script (read once, then deleted), whether moderation is enabled, how many rules
compiled, and which chats are covered. If Telegram reports the bot's privacy mode is still on
(it can't read all group messages), the notice appends a warning that group members' messages
won't be visible — and moderation will silently do nothing — anywhere the bot isn't an admin.

## Deployment

Deploys to its own container and its own systemd service via the repo's `deploy.sh`, entirely
separate from the news bot's container: its own `.env` (own bot token, own admin id), its own
small `requirements.guard.txt` (the container is memory-constrained), and `config.guard.json`
pushed as that container's `config.json`. The two bots share no runtime state and no poller —
only the `src/shared/` config-loading and path helpers are deployed as source alongside each.

## Testing

`tests/test_moderation.py` pins the rule-matching logic in isolation — normalization, prefix
handling, severity resolution, regex edge cases — and includes a check that runs the *actual*
shipped `config.guard.json` rules against lists of known profanity/spam phrases and known-innocent
everyday phrases, so an over-broad prefix or an unanchored stem is caught before it reaches
production. `tests/test_guard_bot_handlers.py` covers the handler layer (exemptions, scope,
deletion, warning text, notice cleanup) with `load_config` and the admin id patched, so it never
touches the real Telegram API or the real config file.
