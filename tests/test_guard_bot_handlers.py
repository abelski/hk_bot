"""Unit tests for the moderation handler in src/guard/bot.py."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from telegram.error import TelegramError

CHAT_ID = -4570601504

MODERATION = {
    "enabled": True,
    "chats": [str(CHAT_ID)],
    "warn_ttl_seconds": 30,
    "rules": [
        {"name": "profanity", "words": ["хуй"], "action": "delete_warn", "reason": "мат"},
        {"name": "caps", "regex": ["!{3,}"], "action": "warn", "reason": "капс"},
    ],
}


def _make_entity(url):
    entity = MagicMock()
    entity.url = url
    return entity


def _make_update(text="привет", caption=None, user_id=7, username="vasya", chat_id=CHAT_ID,
                 entity_urls=(), sender_chat_id=None):
    message = MagicMock()
    message.text = text
    message.caption = caption
    message.chat_id = chat_id
    if sender_chat_id is None:
        message.sender_chat = None
    else:
        message.sender_chat = MagicMock()
        message.sender_chat.id = sender_chat_id
    message.entities = [_make_entity(u) for u in entity_urls]
    message.caption_entities = []
    message.delete = AsyncMock()
    update = MagicMock()
    update.effective_message = message
    update.effective_user.id = user_id
    update.effective_user.username = username
    update.effective_user.first_name = "Вася"
    return update


def _make_context(status="member"):
    ctx = MagicMock()
    member = MagicMock()
    member.status = status
    ctx.bot.get_chat_member = AsyncMock(return_value=member)
    notice = MagicMock()
    notice.message_id = 999
    ctx.bot.send_message = AsyncMock(return_value=notice)
    ctx.job_queue.run_once = MagicMock()
    return ctx


def _config(**overrides):
    moderation = {**MODERATION, **overrides}
    return {"moderation": moderation}


class TestModerateDeletes:
    @pytest.mark.asyncio
    async def test_clean_message_is_left_alone(self):
        from src.guard.bot import moderate
        update, ctx = _make_update("привет всем"), _make_context()
        with patch("src.guard.bot.load_config", return_value=_config()), patch("src.guard.bot.ADMIN_ID", 1):
            await moderate(update, ctx)
        update.effective_message.delete.assert_not_awaited()
        ctx.bot.send_message.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_banned_word_is_deleted(self):
        from src.guard.bot import moderate
        update, ctx = _make_update("ты хуй"), _make_context()
        with patch("src.guard.bot.load_config", return_value=_config()), patch("src.guard.bot.ADMIN_ID", 1):
            await moderate(update, ctx)
        update.effective_message.delete.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_caption_is_moderated(self):
        from src.guard.bot import moderate
        update, ctx = _make_update(text=None, caption="ты хуй"), _make_context()
        with patch("src.guard.bot.load_config", return_value=_config()), patch("src.guard.bot.ADMIN_ID", 1):
            await moderate(update, ctx)
        update.effective_message.delete.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_url_hidden_behind_link_label_is_caught(self):
        """A hyperlink shows a clean label; the banned URL only exists in the entity."""
        from src.guard.bot import moderate
        config = _config(rules=[
            {"name": "spam", "regex": [r"t\.me/\+"], "action": "delete", "reason": "спам"}
        ])
        update = _make_update("тут", entity_urls=["https://t.me/+secretinvite"])
        ctx = _make_context()
        with patch("src.guard.bot.load_config", return_value=config), patch("src.guard.bot.ADMIN_ID", 1):
            await moderate(update, ctx)
        update.effective_message.delete.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_delete_failure_does_not_raise(self):
        from src.guard.bot import moderate
        update, ctx = _make_update("ты хуй"), _make_context()
        update.effective_message.delete = AsyncMock(side_effect=TelegramError("no rights"))
        with patch("src.guard.bot.load_config", return_value=_config()), patch("src.guard.bot.ADMIN_ID", 1):
            await moderate(update, ctx)
        ctx.bot.send_message.assert_not_awaited()


class TestModerateExemptions:
    @pytest.mark.asyncio
    async def test_chat_admin_is_exempt(self):
        from src.guard.bot import moderate
        update, ctx = _make_update("ты хуй"), _make_context(status="administrator")
        with patch("src.guard.bot.load_config", return_value=_config()), patch("src.guard.bot.ADMIN_ID", 1):
            await moderate(update, ctx)
        update.effective_message.delete.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_owner_is_exempt(self):
        from src.guard.bot import moderate
        update, ctx = _make_update("ты хуй", user_id=42), _make_context()
        with patch("src.guard.bot.load_config", return_value=_config()), patch("src.guard.bot.ADMIN_ID", 42):
            await moderate(update, ctx)
        update.effective_message.delete.assert_not_awaited()
        ctx.bot.get_chat_member.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_anonymous_admin_is_exempt(self):
        """Admins posting as the group arrive as @GroupAnonymousBot, whose id is not a member."""
        from src.guard.bot import moderate
        update = _make_update("ты хуй", user_id=1087968824, sender_chat_id=CHAT_ID)
        ctx = _make_context()
        ctx.bot.get_chat_member = AsyncMock(side_effect=TelegramError("user not found"))
        with patch("src.guard.bot.load_config", return_value=_config()), patch("src.guard.bot.ADMIN_ID", 1):
            await moderate(update, ctx)
        update.effective_message.delete.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_sender_chat_from_another_chat_is_not_exempt(self):
        """Only the group itself means 'anonymous admin here' — a foreign sender_chat does not."""
        from src.guard.bot import moderate
        update = _make_update("ты хуй", sender_chat_id=-1009999999)
        ctx = _make_context()
        with patch("src.guard.bot.load_config", return_value=_config()), patch("src.guard.bot.ADMIN_ID", 1):
            await moderate(update, ctx)
        update.effective_message.delete.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_failed_admin_check_still_moderates(self):
        from src.guard.bot import moderate
        update, ctx = _make_update("ты хуй"), _make_context()
        ctx.bot.get_chat_member = AsyncMock(side_effect=TelegramError("boom"))
        with patch("src.guard.bot.load_config", return_value=_config()), patch("src.guard.bot.ADMIN_ID", 1):
            await moderate(update, ctx)
        update.effective_message.delete.assert_awaited_once()


class TestModerateScope:
    @pytest.mark.asyncio
    async def test_disabled_moderation_does_nothing(self):
        from src.guard.bot import moderate
        update, ctx = _make_update("ты хуй"), _make_context()
        with patch("src.guard.bot.load_config", return_value=_config(enabled=False)), patch("src.guard.bot.ADMIN_ID", 1):
            await moderate(update, ctx)
        update.effective_message.delete.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_other_chat_is_ignored(self):
        from src.guard.bot import moderate
        update, ctx = _make_update("ты хуй", chat_id=-111), _make_context()
        with patch("src.guard.bot.load_config", return_value=_config()), patch("src.guard.bot.ADMIN_ID", 1):
            await moderate(update, ctx)
        update.effective_message.delete.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_empty_chats_list_moderates_everywhere(self):
        from src.guard.bot import moderate
        update, ctx = _make_update("ты хуй", chat_id=-999), _make_context()
        with patch("src.guard.bot.load_config", return_value=_config(chats=[])), patch("src.guard.bot.ADMIN_ID", 1):
            await moderate(update, ctx)
        update.effective_message.delete.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_missing_moderation_block_does_nothing(self):
        from src.guard.bot import moderate
        update, ctx = _make_update("ты хуй"), _make_context()
        with patch("src.guard.bot.load_config", return_value={}), patch("src.guard.bot.ADMIN_ID", 1):
            await moderate(update, ctx)
        update.effective_message.delete.assert_not_awaited()


class TestModerateWarnings:
    @pytest.mark.asyncio
    async def test_warn_action_keeps_message_and_notifies(self):
        from src.guard.bot import moderate
        update, ctx = _make_update("что!!!"), _make_context()
        with patch("src.guard.bot.load_config", return_value=_config()), patch("src.guard.bot.ADMIN_ID", 1):
            await moderate(update, ctx)
        update.effective_message.delete.assert_not_awaited()
        ctx.bot.send_message.assert_awaited_once()
        assert "капс" in ctx.bot.send_message.call_args.kwargs["text"]

    @pytest.mark.asyncio
    async def test_delete_warn_sends_notice_mentioning_user(self):
        from src.guard.bot import moderate
        update, ctx = _make_update("ты хуй"), _make_context()
        with patch("src.guard.bot.load_config", return_value=_config()), patch("src.guard.bot.ADMIN_ID", 1):
            await moderate(update, ctx)
        text = ctx.bot.send_message.call_args.kwargs["text"]
        assert "@vasya" in text and "мат" in text

    @pytest.mark.asyncio
    async def test_notice_is_scheduled_for_removal(self):
        from src.guard.bot import moderate
        update, ctx = _make_update("ты хуй"), _make_context()
        with patch("src.guard.bot.load_config", return_value=_config()), patch("src.guard.bot.ADMIN_ID", 1):
            await moderate(update, ctx)
        ctx.job_queue.run_once.assert_called_once()
        assert ctx.job_queue.run_once.call_args.args[1] == 30

    @pytest.mark.asyncio
    async def test_zero_ttl_leaves_notice_in_place(self):
        from src.guard.bot import moderate
        update, ctx = _make_update("ты хуй"), _make_context()
        with patch("src.guard.bot.load_config", return_value=_config(warn_ttl_seconds=0)), patch("src.guard.bot.ADMIN_ID", 1):
            await moderate(update, ctx)
        ctx.job_queue.run_once.assert_not_called()

    @pytest.mark.asyncio
    async def test_user_without_username_is_named_by_first_name(self):
        from src.guard.bot import moderate
        update, ctx = _make_update("ты хуй", username=None), _make_context()
        with patch("src.guard.bot.load_config", return_value=_config()), patch("src.guard.bot.ADMIN_ID", 1):
            await moderate(update, ctx)
        assert "Вася" in ctx.bot.send_message.call_args.kwargs["text"]
