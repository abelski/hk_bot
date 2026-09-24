"""
Telegram bot — chat moderation via config.json.
Supports /reload to apply config changes at runtime.
"""

import logging
import os
from telegram import Update
from telegram.error import TelegramError
from telegram.ext import Application, MessageHandler, CommandHandler, filters, ContextTypes
from dotenv import load_dotenv
from src.shared.config_loader import load_config
from src.guard.moderation import compile_rules, find_action

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
# httpx logs full request URLs, which embed the bot token — keep it out of journalctl.
logging.getLogger("httpx").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)

load_dotenv(".env")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
BOT_DIR = os.getenv("BOT_DIR", "/root/hk_guard")

VERSION_FILE = f"{BOT_DIR}/deploy_version.txt"

ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))


def _is_anonymous_admin(message) -> bool:
    """Admins posting 'as the group' arrive as @GroupAnonymousBot with sender_chat set.

    Their real user id is hidden, so get_chat_member cannot resolve them and they would
    otherwise be moderated as ordinary members. Only genuine admins can post this way.
    """
    sender_chat = getattr(message, "sender_chat", None)
    return bool(sender_chat and sender_chat.id == message.chat_id)


async def _is_exempt(bot, chat_id, user_id) -> bool:
    if user_id == ADMIN_ID:
        return True
    try:
        member = await bot.get_chat_member(chat_id=chat_id, user_id=user_id)
        return member.status in ("administrator", "creator")
    except TelegramError as e:
        logger.warning("Admin check failed for user %s in chat %s: %s", user_id, chat_id, e)
        return False


async def _delete_notice(context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id, message_id = context.job.data
    try:
        await context.bot.delete_message(chat_id=chat_id, message_id=message_id)
    except TelegramError:
        pass


def _scannable_text(message) -> str:
    """Visible text plus any URL hidden behind a hyperlink label."""
    parts = [message.text or message.caption or ""]
    entities = list(message.entities or []) + list(message.caption_entities or [])
    parts.extend(e.url for e in entities if e.url)
    return "\n".join(p for p in parts if p)


async def moderate(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.effective_message
    user = update.effective_user
    if not message or not user:
        return
    text = _scannable_text(message)
    if not text:
        return

    config = load_config().get("moderation", {})
    if not config.get("enabled", False):
        return
    chats = config.get("chats", [])
    if chats and str(message.chat_id) not in [str(c) for c in chats]:
        return

    hit = find_action(text, compile_rules(config))
    if not hit:
        return
    action, reason = hit

    if _is_anonymous_admin(message) or await _is_exempt(context.bot, message.chat_id, user.id):
        # Logged because it is otherwise indistinguishable from the bot not seeing the
        # message at all — which is what a privacy-mode misconfiguration looks like.
        logger.info("Rule matched (%s) but user %s is exempt in chat %s",
                    reason, user.id, message.chat_id)
        return

    if action in ("delete", "delete_warn", "delete_ban"):
        try:
            await message.delete()
        except TelegramError as e:
            logger.warning("Cannot delete message in chat %s: %s", message.chat_id, e)
            return
        logger.info("Deleted message from %s in %s (%s)", user.id, message.chat_id, reason)

    if action == "delete_ban":
        # revoke_messages wipes the spammer's other messages too — the rule only saw one.
        try:
            await context.bot.ban_chat_member(
                chat_id=message.chat_id, user_id=user.id, revoke_messages=True
            )
            logger.info("Banned %s in %s (%s)", user.id, message.chat_id, reason)
        except TelegramError as e:
            logger.warning("Cannot ban user %s in chat %s: %s", user.id, message.chat_id, e)

    if action in ("warn", "delete_warn", "delete_ban"):
        who = f"@{user.username}" if user.username else user.first_name
        verb = {"delete_warn": "сообщение удалено", "delete_ban": "забанен"}.get(action, "нарушение")
        notice = await context.bot.send_message(
            chat_id=message.chat_id, text=f"{who}, {verb}: {reason}"
        )
        ttl = config.get("warn_ttl_seconds", 30)
        if ttl and context.job_queue:
            context.job_queue.run_once(
                _delete_notice, ttl, data=(message.chat_id, notice.message_id)
            )


async def reload_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_user.id != ADMIN_ID:
        return
    await update.message.reply_text("Config reloaded.")


async def on_startup(app) -> None:
    if not ADMIN_ID:
        return
    lines = ["hk-guard запущен"]
    if os.path.exists(VERSION_FILE):
        try:
            lines.append(f"Версия: {open(VERSION_FILE).read().strip()}")
            os.remove(VERSION_FILE)
        except OSError:
            pass

    config = load_config().get("moderation", {})
    state = "включена" if config.get("enabled") else "выключена"
    lines.append(f"Модерация: {state}, правил: {len(compile_rules(config))}")
    lines.append(f"Чаты: {', '.join(map(str, config.get('chats', []))) or 'все'}")

    try:
        me = await app.bot.get_me()
        if not me.can_read_all_group_messages:
            lines.append(
                "\n⚠️ Privacy mode включён. Это не страшно там, где бот — администратор "
                "(админу приходят все сообщения), но в чате без админки он не увидит "
                "сообщения участников и молча ничего не сделает.\n"
                "Снять: BotFather → /setprivacy → Disable."
            )
        await app.bot.send_message(chat_id=ADMIN_ID, text="\n".join(lines))
    except TelegramError as e:
        logger.warning("Failed to send startup notification: %s", e)


def main() -> None:
    if not TELEGRAM_BOT_TOKEN:
        raise ValueError("TELEGRAM_BOT_TOKEN not set in .env")
    if not load_config().get("moderation"):
        raise ValueError("config.json has no 'moderation' key — refusing to start silently empty")

    app = Application.builder().token(TELEGRAM_BOT_TOKEN).post_init(on_startup).build()
    app.add_handler(CommandHandler("reload", reload_command))
    # Own group so moderation runs regardless of which group-0 handler claims the update.
    # Commands are deliberately not excluded — "/start <slur>" would otherwise bypass the rules.
    app.add_handler(MessageHandler(
        filters.ChatType.GROUPS & (filters.TEXT | filters.CAPTION),
        moderate,
    ), group=1)

    logger.info("Bot started: hk-guard")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
