"""
Telegram bot — command dispatch via config.json.
Supports /update (with rollback) and /reload to apply config changes at runtime.
"""

import logging
import os
import subprocess
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
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

UPDATE_YES = "update_yes"
UPDATE_NO = "update_no"


async def answer(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await _show_commands(update.effective_message)


async def answer_mention(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.effective_message
    if not message:
        return
    bot_username = context.bot.username
    for text in message.parse_entities(["mention"]).values():
        if text.lower() == f"@{bot_username}".lower():
            await _show_commands(message)
            return


async def _show_commands(message) -> None:
    commands = load_commands()
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
    cmd_name = query.data[4:]  # strip "cmd_" prefix
    commands = {cmd.NAME: cmd for cmd in load_commands()}
    cmd = commands.get(cmd_name)
    if cmd is None:
        await query.edit_message_text("Unknown command.")
        return
    result = await cmd.run()
    await query.edit_message_text(result)


async def reload_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    schedule_jobs(context.application)
    await update.message.reply_text("Config reloaded.")


def make_cron_callback(cmd_module, chat_ids: list):
    async def callback(context: ContextTypes.DEFAULT_TYPE) -> None:
        result = await cmd_module.run()
        for chat_id in chat_ids:
            await context.bot.send_message(chat_id=chat_id, text=result)
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
            raise RuntimeError("BOT_REPO_URL not configured in .cred")

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


def main() -> None:
    if not TELEGRAM_BOT_TOKEN:
        raise ValueError("TELEGRAM_BOT_TOKEN not set in .cred")

    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
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
