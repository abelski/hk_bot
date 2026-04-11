"""
Telegram bot — command dispatch via config.json.
Supports /update (with rollback) and /reload to apply config changes at runtime.
"""

import logging
import os
import subprocess
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InputMediaPhoto
from telegram.ext import Application, MessageHandler, CommandHandler, CallbackQueryHandler, filters, ContextTypes
from dotenv import load_dotenv
from apscheduler.triggers.cron import CronTrigger
from commands import load_commands
from config_loader import load_config

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

load_dotenv(".env")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
BOT_DIR = os.getenv("BOT_DIR", "/root/hk_bot")
BOT_SCRIPT = f"{BOT_DIR}/src/bot.py"
BOT_BACKUP = f"{BOT_DIR}/src/bot.py.bak"
BOT_SERVICE = "hk-bot"
BOT_REPO_URL = os.getenv("BOT_REPO_URL", "")

VERSION_FILE = f"{BOT_DIR}/deploy_version.txt"

UPDATE_YES = "update_yes"
UPDATE_NO = "update_no"
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))


def _split_at_paragraph(text: str, max_len: int = 1024):
    """Return (head, tail) split at a paragraph boundary within max_len chars."""
    if len(text) <= max_len:
        return text, ""
    split = text.rfind("\n\n", 0, max_len)
    if split != -1:
        return text[:split], text[split + 2:].strip()
    return text[:max_len], text[max_len:].strip()


def _build_media(photos: list, caption: str) -> list:
    from io import BytesIO
    media = [InputMediaPhoto(media=BytesIO(p)) for p in photos[:10]]
    media[0] = InputMediaPhoto(media=BytesIO(photos[0]), caption=caption, parse_mode="Markdown")
    return media


def _append_footer(text: str) -> str:
    footer = load_config().get("post_footer", "")
    if footer:
        return f"{text}\n\n{footer}"
    return text


async def _send_result(bot_or_query, result, *, is_query: bool = False) -> None:
    if isinstance(result, dict):
        from io import BytesIO
        text = _append_footer(result.get("text", ""))
        photos = result.get("photos", [])
        video = result.get("video")
        if photos:
            caption, overflow = _split_at_paragraph(text)
            media = _build_media(photos, caption)
            if is_query:
                await bot_or_query.edit_message_reply_markup(reply_markup=None)
                await bot_or_query.message.reply_media_group(media)
                if overflow:
                    await bot_or_query.message.reply_text(overflow, parse_mode="Markdown")
            else:
                bot, chat_id = bot_or_query
                await bot.send_media_group(chat_id=chat_id, media=media)
                if overflow:
                    await bot.send_message(chat_id=chat_id, text=overflow, parse_mode="Markdown")
        elif video:
            caption, overflow = _split_at_paragraph(text)
            if is_query:
                await bot_or_query.edit_message_reply_markup(reply_markup=None)
                await bot_or_query.message.reply_video(BytesIO(video), caption=caption, parse_mode="Markdown")
                if overflow:
                    await bot_or_query.message.reply_text(overflow, parse_mode="Markdown")
            else:
                bot, chat_id = bot_or_query
                await bot.send_video(chat_id=chat_id, video=BytesIO(video), caption=caption, parse_mode="Markdown")
                if overflow:
                    await bot.send_message(chat_id=chat_id, text=overflow, parse_mode="Markdown")
        else:
            if is_query:
                await bot_or_query.edit_message_text(text, parse_mode="Markdown")
            else:
                bot, chat_id = bot_or_query
                await bot.send_message(chat_id=chat_id, text=text, parse_mode="Markdown")
    else:
        result = _append_footer(result)
        if is_query:
            await bot_or_query.edit_message_text(result)
        else:
            bot, chat_id = bot_or_query
            await bot.send_message(chat_id=chat_id, text=result)


async def _whitelist_allowed(bot, user_id, chat_id) -> bool:
    config = load_config()
    if not config.get("checkwhitelist", False):
        return True
    whitelist_groups = config.get("whitelist_groups", [])
    # If the request comes from a whitelisted group itself, allow
    if str(chat_id) in whitelist_groups:
        return True
    # Otherwise check if the user is a member of any whitelisted group
    for group_id in whitelist_groups:
        try:
            member = await bot.get_chat_member(chat_id=int(group_id), user_id=user_id)
            if member.status in ("member", "administrator", "creator", "restricted"):
                return True
        except Exception:
            pass
    return False


async def answer(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_user.id != ADMIN_ID:
        return
    if not await _whitelist_allowed(context.bot, update.effective_user.id, update.effective_chat.id):
        return
    dm_commands = load_config().get("dm_commands")
    await _show_commands(update.effective_message, allowed=dm_commands)


async def answer_mention(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.effective_message
    if not message:
        return
    if not await _whitelist_allowed(context.bot, update.effective_user.id, update.effective_chat.id):
        return
    bot_username = context.bot.username
    for text in message.parse_entities(["mention"]).values():
        if text.lower() == f"@{bot_username}".lower():
            await _show_commands(message)
            return


async def _show_commands(message, allowed: list | None = None) -> None:
    commands = load_commands()
    if allowed is not None:
        commands = [cmd for cmd in commands if cmd.NAME in allowed]
    buttons = [
        [InlineKeyboardButton(cmd.LABEL, callback_data=f"cmd_{cmd.NAME}")]
        for cmd in commands
    ]
    await message.reply_text(
        "Available commands:",
        reply_markup=InlineKeyboardMarkup(buttons),
    )


async def command_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    if not await _whitelist_allowed(context.bot, update.effective_user.id, update.effective_chat.id):
        return
    cmd_name = query.data[4:]  # strip "cmd_" prefix
    commands = {cmd.NAME: cmd for cmd in load_commands()}
    cmd = commands.get(cmd_name)
    if cmd is None:
        await query.edit_message_text("Unknown command.")
        return
    await query.message.chat.send_action("typing")
    try:
        result = await cmd.run()
        await _send_result(query, result, is_query=True)
    except Exception:
        logger.exception("Error running command %s", cmd_name)
        raise


async def reload_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_user.id != ADMIN_ID:
        return
    schedule_jobs(context.application)
    await update.message.reply_text("Config reloaded.")


def make_cron_callback(cmd_module, chat_ids: list):
    async def callback(context: ContextTypes.DEFAULT_TYPE) -> None:
        run_fn = getattr(cmd_module, "run_if_new", cmd_module.run)
        result = await run_fn()
        if result is None:
            return
        for chat_id in chat_ids:
            await _send_result((context.bot, chat_id), result)
    return callback


def schedule_jobs(app) -> None:
    for job in app.job_queue.jobs():
        if job.name and job.name.startswith("cron_"):
            job.schedule_removal()

    config = load_config()
    recipients = config.get("recipients", {})
    commands = {cmd.NAME: cmd for cmd in load_commands()}
    for i, mapping in enumerate(config.get("mappings", [])):
        cmd_name = mapping.get("command")
        recipient_names = mapping.get("recipients", [])
        cron = mapping.get("cron")
        if not (cmd_name and recipient_names and cron):
            continue
        cmd = commands.get(cmd_name)
        if cmd is None:
            logger.warning("Unknown command in config: %s", cmd_name)
            continue
        chat_ids = []
        for name in recipient_names:
            chat_id = recipients.get(name)
            if chat_id is None:
                logger.warning("Unknown recipient '%s' in mapping %d", name, i)
            else:
                chat_ids.append(chat_id)
        if not chat_ids:
            continue
        app.job_queue.run_custom(
            make_cron_callback(cmd, chat_ids),
            job_kwargs={"trigger": CronTrigger.from_crontab(cron)},
            name=f"cron_{cmd_name}_{i}",
        )
        logger.info("Scheduled %s for %s with cron '%s'", cmd_name, recipient_names, cron)


async def update_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_user.id != ADMIN_ID:
        return
    keyboard = [[
        InlineKeyboardButton("Yes ✓", callback_data=UPDATE_YES),
        InlineKeyboardButton("No ✗", callback_data=UPDATE_NO),
    ]]
    await update.message.reply_text(
        "Update bot on server?",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )


async def update_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    if query.data == UPDATE_NO:
        await query.edit_message_text("Update cancelled.")
        return

    await query.edit_message_text("Backing up current version...")

    try:
        # Backup
        subprocess.run(["cp", BOT_SCRIPT, BOT_BACKUP], check=True)

        await query.edit_message_text("Pulling latest code...")

        if BOT_REPO_URL:
            result = subprocess.run(
                ["git", "-C", BOT_DIR, "pull", BOT_REPO_URL, "main"],
                capture_output=True, text=True, timeout=60,
            )
            if result.returncode != 0:
                raise RuntimeError(result.stderr.strip() or result.stdout.strip())
        else:
            raise RuntimeError("BOT_REPO_URL not configured in .env")

        await query.edit_message_text("Restarting service...")
        subprocess.Popen(["systemctl", "restart", BOT_SERVICE])

    except Exception as e:
        logger.error(f"Update failed: {e}")
        await _rollback(query, str(e))


async def _rollback(query, reason: str) -> None:
    try:
        subprocess.run(["cp", BOT_BACKUP, BOT_SCRIPT], check=True)
        await query.edit_message_text(
            f"Update failed: {reason}\n\nRolled back to previous version. Restarting..."
        )
        subprocess.Popen(["systemctl", "restart", BOT_SERVICE])
    except Exception as re:
        logger.error(f"Rollback failed: {re}")
        await query.edit_message_text(
            f"Update failed: {reason}\nRollback also failed: {re}\n\nManual intervention required."
        )


async def on_startup(app) -> None:
    if not ADMIN_ID or not os.path.exists(VERSION_FILE):
        return
    try:
        version = open(VERSION_FILE).read().strip()
        os.remove(VERSION_FILE)
        await app.bot.send_message(chat_id=ADMIN_ID, text=f"Deployed: {version}")
    except Exception as e:
        logger.warning("Failed to send deploy notification: %s", e)


def main() -> None:
    if not TELEGRAM_BOT_TOKEN:
        raise ValueError("TELEGRAM_BOT_TOKEN not set in .env")

    app = Application.builder().token(TELEGRAM_BOT_TOKEN).post_init(on_startup).build()
    schedule_jobs(app)
    app.add_handler(CommandHandler("update", update_command))
    app.add_handler(CommandHandler("reload", reload_command))
    app.add_handler(CallbackQueryHandler(update_callback, pattern=f"^{UPDATE_YES}$|^{UPDATE_NO}$"))
    app.add_handler(CallbackQueryHandler(command_callback, pattern=r"^cmd_"))
    app.add_handler(MessageHandler(filters.ChatType.PRIVATE, answer))
    app.add_handler(MessageHandler(
        (filters.ChatType.GROUPS | filters.ChatType.CHANNEL) & filters.Entity("mention"),
        answer_mention,
    ))

    logger.info("Bot started")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
