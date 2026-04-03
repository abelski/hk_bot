"""
Unit tests for answer() and answer_mention() handlers in src/bot.py.
"""

import sys
import os
import types
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

# ---------------------------------------------------------------------------
# Minimal stubs so bot.py can be imported without real credentials or
# the telegram package initialising network connections.
# ---------------------------------------------------------------------------

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_update(text="hello", chat_type="private", entities=None):
    """Build a minimal mock Update with an effective_message."""
    message = MagicMock()
    message.reply_text = AsyncMock()
    message.parse_entities = MagicMock(return_value=entities or {})
    update = MagicMock()
    update.effective_message = message
    return update


def _make_context(bot_username="testbot"):
    ctx = MagicMock()
    ctx.bot.username = bot_username
    return ctx


# ---------------------------------------------------------------------------
# Tests for answer()
# ---------------------------------------------------------------------------

class TestAnswer:
    @pytest.mark.asyncio
    async def test_replies_with_leaderboard(self):
        from bot import answer
        update = _make_update()
        ctx = _make_context()
        entries = [{"rank": 1, "user": {"first_name": "A", "last_name": "B"}, "score": 10}]
        with patch("bot.fetch_top3", return_value=entries), \
             patch("bot.format_top3", return_value="leaderboard text"):
            await answer(update, ctx)
        update.effective_message.reply_text.assert_awaited_once_with("leaderboard text")

    @pytest.mark.asyncio
    async def test_replies_error_when_fetch_fails(self):
        from bot import answer
        update = _make_update()
        ctx = _make_context()
        with patch("bot.fetch_top3", return_value=None):
            await answer(update, ctx)
        update.effective_message.reply_text.assert_awaited_once_with(
            "Could not fetch leaderboard, please try again later."
        )


# ---------------------------------------------------------------------------
# Tests for answer_mention()
# ---------------------------------------------------------------------------

class TestAnswerMention:
    @pytest.mark.asyncio
    async def test_responds_when_bot_is_mentioned(self):
        from bot import answer_mention
        entity = MagicMock()
        update = _make_update(entities={entity: "@testbot"})
        ctx = _make_context(bot_username="testbot")
        entries = [{"rank": 1, "user": {"first_name": "A", "last_name": "B"}, "score": 10}]
        with patch("bot.fetch_top3", return_value=entries), \
             patch("bot.format_top3", return_value="leaderboard text"):
            await answer_mention(update, ctx)
        update.effective_message.reply_text.assert_awaited_once_with("leaderboard text")

    @pytest.mark.asyncio
    async def test_silent_when_other_user_mentioned(self):
        from bot import answer_mention
        entity = MagicMock()
        update = _make_update(entities={entity: "@otherusername"})
        ctx = _make_context(bot_username="testbot")
        with patch("bot.fetch_top3") as mock_fetch:
            await answer_mention(update, ctx)
        mock_fetch.assert_not_called()
        update.effective_message.reply_text.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_case_insensitive_username_match(self):
        from bot import answer_mention
        entity = MagicMock()
        update = _make_update(entities={entity: "@TestBot"})
        ctx = _make_context(bot_username="testbot")
        entries = [{"rank": 1, "user": {"first_name": "A", "last_name": "B"}, "score": 10}]
        with patch("bot.fetch_top3", return_value=entries), \
             patch("bot.format_top3", return_value="leaderboard text"):
            await answer_mention(update, ctx)
        update.effective_message.reply_text.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_replies_error_when_fetch_fails(self):
        from bot import answer_mention
        entity = MagicMock()
        update = _make_update(entities={entity: "@testbot"})
        ctx = _make_context(bot_username="testbot")
        with patch("bot.fetch_top3", return_value=None):
            await answer_mention(update, ctx)
        update.effective_message.reply_text.assert_awaited_once_with(
            "Could not fetch leaderboard, please try again later."
        )

    @pytest.mark.asyncio
    async def test_responds_only_once_when_mentioned_twice(self):
        from bot import answer_mention
        e1, e2 = MagicMock(), MagicMock()
        update = _make_update(entities={e1: "@testbot", e2: "@testbot"})
        ctx = _make_context(bot_username="testbot")
        entries = [{"rank": 1, "user": {"first_name": "A", "last_name": "B"}, "score": 10}]
        with patch("bot.fetch_top3", return_value=entries), \
             patch("bot.format_top3", return_value="leaderboard text"):
            await answer_mention(update, ctx)
        assert update.effective_message.reply_text.await_count == 1

    @pytest.mark.asyncio
    async def test_silent_when_no_message(self):
        from bot import answer_mention
        update = MagicMock()
        update.effective_message = None
        ctx = _make_context()
        with patch("bot.fetch_top3") as mock_fetch:
            await answer_mention(update, ctx)
        mock_fetch.assert_not_called()
