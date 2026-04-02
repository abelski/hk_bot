"""
Simple Telegram bot — replies Hello to every message.
Supports /update command with inline confirmation and automatic rollback.
"""

import logging
import os
import subprocess
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, MessageHandler, CommandHandler, CallbackQueryHandler, filters, ContextTypes
from dotenv import load_dotenv

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

load_dotenv(".cred")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
BOT_DIR = os.getenv("BOT_DIR", "/root/hk_bot")
BOT_SCRIPT = f"{BOT_DIR}/src/bot.py"
BOT_BACKUP = f"{BOT_DIR}/src/bot.py.bak"
BOT_SERVICE = "hk-bot"
BOT_REPO_URL = os.getenv("BOT_REPO_URL", "")

UPDATE_YES = "update_yes"
UPDATE_NO = "update_no"


async def hello(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("Hello!")


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
    app.add_handler(CommandHandler("update", update_command))
    app.add_handler(CallbackQueryHandler(update_callback, pattern=f"^{UPDATE_YES}$|^{UPDATE_NO}$"))
    app.add_handler(MessageHandler(filters.ALL, hello))

    logger.info("Bot started")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
