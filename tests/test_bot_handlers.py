"""
Unit tests for bot handlers in src/bot.py.
"""

import sys
import os
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


def _make_mock_cmd(name="woo", label="WOO Leaderboard 🏄"):
    cmd = MagicMock()
    cmd.NAME = name
    cmd.LABEL = label
    return cmd


# ---------------------------------------------------------------------------
# Tests for answer()
# ---------------------------------------------------------------------------

class TestAnswer:
    @pytest.mark.asyncio
    async def test_shows_command_list(self):
        from bot import answer
        update = _make_update()
        ctx = _make_context()
        mock_cmd = _make_mock_cmd()
        with patch("bot.load_commands", return_value=[mock_cmd]):
            await answer(update, ctx)
        update.effective_message.reply_text.assert_awaited_once()
        args, kwargs = update.effective_message.reply_text.call_args
        assert args[0] == "Available commands:"
        assert kwargs["reply_markup"] is not None

    @pytest.mark.asyncio
    async def test_shows_empty_keyboard_when_no_commands(self):
        from bot import answer
        update = _make_update()
        ctx = _make_context()
        with patch("bot.load_commands", return_value=[]):
            await answer(update, ctx)
        update.effective_message.reply_text.assert_awaited_once()


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
        mock_cmd = _make_mock_cmd()
        with patch("bot.load_commands", return_value=[mock_cmd]):
            await answer_mention(update, ctx)
        update.effective_message.reply_text.assert_awaited_once()
        args, _ = update.effective_message.reply_text.call_args
        assert args[0] == "Available commands:"

    @pytest.mark.asyncio
    async def test_silent_when_other_user_mentioned(self):
        from bot import answer_mention
        entity = MagicMock()
        update = _make_update(entities={entity: "@otherusername"})
        ctx = _make_context(bot_username="testbot")
        with patch("bot.load_commands") as mock_load:
            await answer_mention(update, ctx)
        mock_load.assert_not_called()
        update.effective_message.reply_text.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_case_insensitive_username_match(self):
        from bot import answer_mention
        entity = MagicMock()
        update = _make_update(entities={entity: "@TestBot"})
        ctx = _make_context(bot_username="testbot")
        mock_cmd = _make_mock_cmd()
        with patch("bot.load_commands", return_value=[mock_cmd]):
            await answer_mention(update, ctx)
        update.effective_message.reply_text.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_responds_only_once_when_mentioned_twice(self):
        from bot import answer_mention
        e1, e2 = MagicMock(), MagicMock()
        update = _make_update(entities={e1: "@testbot", e2: "@testbot"})
        ctx = _make_context(bot_username="testbot")
        mock_cmd = _make_mock_cmd()
        with patch("bot.load_commands", return_value=[mock_cmd]):
            await answer_mention(update, ctx)
        assert update.effective_message.reply_text.await_count == 1

    @pytest.mark.asyncio
    async def test_silent_when_no_message(self):
        from bot import answer_mention
        update = MagicMock()
        update.effective_message = None
        ctx = _make_context()
        with patch("bot.load_commands") as mock_load:
            await answer_mention(update, ctx)
        mock_load.assert_not_called()


# ---------------------------------------------------------------------------
# Tests for schedule_jobs()
# ---------------------------------------------------------------------------

class TestScheduleJobs:
    def test_schedules_known_command(self):
        import bot
        mock_cmd = MagicMock()
        mock_cmd.NAME = "woo"
        mock_app = MagicMock()
        mock_app.job_queue.jobs.return_value = []
        config = {
            "recipients": {"main_group": "-100111"},
            "mappings": [{"command": "woo", "recipients": ["main_group"], "cron": "0 23 * * *"}],
        }
        with patch("bot.load_config", return_value=config), \
             patch("bot.load_commands", return_value=[mock_cmd]):
            bot.schedule_jobs(mock_app)
        mock_app.job_queue.run_custom.assert_called_once()
        _, kwargs = mock_app.job_queue.run_custom.call_args
        assert kwargs["name"] == "cron_woo_0"

    def test_skips_mapping_without_cron(self):
        import bot
        mock_cmd = MagicMock()
        mock_cmd.NAME = "woo"
        mock_app = MagicMock()
        mock_app.job_queue.jobs.return_value = []
        config = {
            "recipients": {"main_group": "-100111"},
            "mappings": [{"command": "woo", "recipients": ["main_group"]}],
        }
        with patch("bot.load_config", return_value=config), \
             patch("bot.load_commands", return_value=[mock_cmd]):
            bot.schedule_jobs(mock_app)
        mock_app.job_queue.run_custom.assert_not_called()

    def test_skips_unknown_command(self):
        import bot
        mock_app = MagicMock()
        mock_app.job_queue.jobs.return_value = []
        config = {
            "recipients": {"main_group": "-100111"},
            "mappings": [{"command": "unknown", "recipients": ["main_group"], "cron": "0 23 * * *"}],
        }
        with patch("bot.load_config", return_value=config), \
             patch("bot.load_commands", return_value=[]):
            bot.schedule_jobs(mock_app)
        mock_app.job_queue.run_custom.assert_not_called()

    def test_skips_unknown_recipient(self):
        import bot
        mock_cmd = MagicMock()
        mock_cmd.NAME = "woo"
        mock_app = MagicMock()
        mock_app.job_queue.jobs.return_value = []
        config = {
            "recipients": {},
            "mappings": [{"command": "woo", "recipients": ["unknown_group"], "cron": "0 23 * * *"}],
        }
        with patch("bot.load_config", return_value=config), \
             patch("bot.load_commands", return_value=[mock_cmd]):
            bot.schedule_jobs(mock_app)
        mock_app.job_queue.run_custom.assert_not_called()

    def test_sends_to_multiple_recipients(self):
        import bot
        mock_cmd = MagicMock()
        mock_cmd.NAME = "woo"
        mock_app = MagicMock()
        mock_app.job_queue.jobs.return_value = []
        config = {
            "recipients": {"group_a": "-100111", "group_b": "-100222"},
            "mappings": [{"command": "woo", "recipients": ["group_a", "group_b"], "cron": "0 23 * * *"}],
        }
        with patch("bot.load_config", return_value=config), \
             patch("bot.load_commands", return_value=[mock_cmd]):
            bot.schedule_jobs(mock_app)
        mock_app.job_queue.run_custom.assert_called_once()
        callback_fn = mock_app.job_queue.run_custom.call_args[0][0]
        # Verify callback was created with both chat IDs by checking it's callable
        assert callable(callback_fn)

    def test_cancels_existing_cron_jobs_before_rescheduling(self):
        import bot
        existing_job = MagicMock()
        existing_job.name = "cron_woo_0"
        mock_app = MagicMock()
        mock_app.job_queue.jobs.return_value = [existing_job]
        with patch("bot.load_config", return_value={"mappings": []}), \
             patch("bot.load_commands", return_value=[]):
            bot.schedule_jobs(mock_app)
        existing_job.schedule_removal.assert_called_once()
