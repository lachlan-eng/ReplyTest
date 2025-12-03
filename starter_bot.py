# starter_bot.py
import random
import string
from datetime import datetime

from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
)

# ===============================
# HARDCODE YOUR STARTER BOT TOKEN
# ===============================

BOT_TOKEN = "8543150612:AAFRAmwZQPswuehffqyY0-EegykLTR3aHpM"  # <-- replace this with your real token


# ==========================================
# BOTS THAT WILL PARTICIPATE IN THE TEST
# ==========================================

PERSONA_BOTS = [
    "@JamesTestBot",
    "@EndiTestBot",
    "@LachlanTestBot",
    "@JaysonTestBot",
]

PERSONA_LINKS = [
    "https://t.me/JamesTestBot",
    "https://t.me/EndiTestBot",
    "https://t.me/LachlanTestBot",
    "https://t.me/JaysonTestBot",
]

# Simple in-memory test storage
tests = {}  # test_id -> {"user_id": int, "created_at": datetime}


def generate_test_id(length: int = 6) -> str:
    chars = string.ascii_uppercase + string.digits
    return "".join(random.choice(chars) for _ in range(length))


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Hey! I'm the Reply Test Starter.\n\n"
        "Use /newtest to create a new reply speed test."
    )


async def newtest(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    chat = update.effective_chat

    # Generate Test ID
    test_id = generate_test_id()
    tests[test_id] = {
        "user_id": user.id,
        "created_at": datetime.utcnow(),
    }

    # Build message
    lines = [
        "🆕 *Reply Speed Test Created!*",
        "",
        f"🧪 *Test ID:* `{test_id}`",
        "",
        "Use this ID with the other bots so they all log the same session.",
        "",
        "👉 Next steps:",
        "1️⃣ Open each bot:",
        "",
    ]

    for handle, link in zip(PERSONA_BOTS, PERSONA_LINKS):
        lines.append(f"• [{handle}]({link})")

    lines += [
        "",
        f"2️⃣ In *each* bot, send: `/start {test_id}`",
        "3️⃣ Then reply as fast as you can. We will consider the quality of your replies (Grammar, spelling, punctuation, expressiveness). The bots will handle the timing.",
        "",
        "Later, we can centralize stats from all bots using this Test ID.",
    ]

    text = "\n".join(lines)

    await context.bot.send_message(
        chat_id=chat.id,
        text=text,
        parse_mode="Markdown",
        disable_web_page_preview=True,
    )


def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("newtest", newtest))

    app.run_polling()


if __name__ == "__main__":
    main()
