# Feature: Group/Channel Mention Response with Leaderboard

## Context
The bot currently responds to **every** message in any chat with leaderboard data. This needs to change: in group chats and channels the bot should only respond when explicitly @mentioned, while private chat keeps the respond-to-everything behavior.

## Decisions & Clarifications
- Private chat: respond to all messages (unchanged)
- Groups/channels: respond only when bot is @mentioned
- Anyone can trigger the bot (no admin-only restriction)
- Target: both group chats and Telegram channels

## Scope

**In scope:**
- Rename `hello()` to `answer()` for private chats
- Add `answer_mention()` handler for group/channel @mention responses
- Replace the catch-all `MessageHandler(filters.ALL, hello)` with two targeted handlers

**Out of scope:**
- Slash command trigger in groups (e.g. `/leaderboard`)
- Admin-only restrictions
- Rate limiting
- BotFather configuration (documented as manual step, no code change)

## Acceptance Criteria
- Given a private chat, when any message is sent, bot replies with leaderboard
- Given a group chat, when a message contains @botname, bot replies with leaderboard
- Given a group chat, when a message does NOT mention the bot, bot stays silent
- Given a channel where bot is admin, when a post contains @botname, bot replies with leaderboard
- Given a channel post without @botname, bot stays silent

## Affected Files

| File | Lines | Change type | Reason |
|------|-------|-------------|--------|
| `src/bot.py` | 33 | modify | Rename `hello` → `answer` |
| `src/bot.py` | 33–38 | modify | Use `effective_message` instead of `message` (safe for channel posts) |
| `src/bot.py` | 39–51 (insert) | add | New `answer_mention()` handler |
| `src/bot.py` | 107 | modify | Replace single catch-all handler with two targeted handlers |

## Implementation Steps

### Step 1: Rename `hello()` to `answer()` and use `effective_message`

**Goal:** Rename the private-chat handler to `answer` and make it safe for all update types.

**File:** `src/bot.py`, lines 33–38

**Exact change** — replace:
```python
async def hello(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    entries = fetch_top3()
    if entries is None:
        await update.message.reply_text("Could not fetch leaderboard, please try again later.")
    else:
        await update.message.reply_text(format_top3(entries))
```
with:
```python
async def answer(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.effective_message
    entries = fetch_top3()
    if entries is None:
        await message.reply_text("Could not fetch leaderboard, please try again later.")
    else:
        await message.reply_text(format_top3(entries))
```

---

### Step 2: Add `answer_mention()` handler

**Goal:** Respond with leaderboard when bot is @mentioned in a group or channel.

**File:** `src/bot.py` — insert after line 38 (after `hello()` function), before `update_command`:

```python
async def answer_mention(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.effective_message
    if not message:
        return
    bot_username = context.bot.username
    for text in message.parse_entities(["mention"]).values():
        if text.lower() == f"@{bot_username}".lower():
            entries = fetch_top3()
            if entries is None:
                await message.reply_text("Could not fetch leaderboard, please try again later.")
            else:
                await message.reply_text(format_top3(entries))
            return
```

**How it works:**
- `message.parse_entities(["mention"])` returns `{MessageEntity: "@username"}` for every `@mention` in the message
- Comparing to `@{bot_username}` ensures only bot-directed mentions trigger a response
- Case-insensitive comparison handles Telegram's case-insensitive usernames
- Early `return` after responding avoids double-reply if bot is mentioned twice

---

### Step 3: Replace the catch-all handler with two targeted handlers

**File:** `src/bot.py`, line 107

**Exact change** — replace:
```python
app.add_handler(MessageHandler(filters.ALL, hello))
```
with:
```python
app.add_handler(MessageHandler(filters.ChatType.PRIVATE, answer))
app.add_handler(MessageHandler(
    (filters.ChatType.GROUPS | filters.ChatType.CHANNEL) & filters.Entity("mention"),
    answer_mention,
))
```

**Why `filters.Entity("mention")` as a pre-filter:**
- Avoids calling `answer_mention()` for every group message — only fires when the message already contains at least one mention entity
- `filters.ChatType.GROUPS` matches both GROUP and SUPERGROUP types
- `filters.ChatType.CHANNEL` matches channel posts (`channel_post` update type)
- `update.effective_message` in `answer_mention` handles both `message` and `channel_post` transparently

**Handler order matters:** `CommandHandler("update", ...)` is registered first (line 105), so `/update` in private chat is handled by it and never reaches the private `MessageHandler`.

---

## Manual Setup Steps (no code changes)

1. **BotFather — Group Privacy Mode (keep ON, it's the default):**
   - With privacy mode ON, the bot in groups only receives messages that @mention it or are commands
   - Verify: BotFather → `/mybots` → your bot → Bot Settings → Group Privacy → should be "ENABLED"

2. **For channels:** Add the bot as an **Admin** of the channel (read messages permission is enough)

3. **Restart the bot service** after deploying:
   ```bash
   systemctl restart hk-bot
   # or on Proxmox:
   pct exec 100 -- systemctl restart hk-bot
   ```

---

## Edge Cases & Risks

| Scenario | Expected behaviour | Risk |
|----------|--------------------|------|
| Bot mentioned twice in same message | Responds once (early return after first match) | low |
| Bot mentioned in channel comment thread | comment thread is a group → handled by GROUPS filter | low |
| `context.bot.username` is None (rare race on startup) | No response, no crash (comparison fails silently) | low |
| Leaderboard API down | Returns "Could not fetch leaderboard..." message | low |
| Privacy mode OFF in BotFather | Bot receives all group messages; `filters.Entity("mention")` still protects against unwanted responses | low |

## Verification

1. **Private chat:** Send any message → bot replies with leaderboard ✓
2. **Group — no mention:** Send a plain message → bot is silent ✓
3. **Group — mention bot:** Send any message containing `@botname` anywhere (e.g. `кто первый? @botname`) → bot replies with leaderboard ✓
4. **Group — mention someone else:** Send any message containing `@otherusername` anywhere (e.g. `кто первый? @otherusername`) → bot is silent ✓
5. **Channel — post without mention:** Post to channel → bot is silent ✓
6. **Channel — post with @botname:** Post `@botname` → bot replies in channel ✓

Manual test commands:
```bash
# Check bot is running
pct exec 100 -- systemctl status hk-bot

# Tail logs while testing
pct exec 100 -- journalctl -u hk-bot -f
```
