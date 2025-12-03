from datetime import datetime
import asyncio
import random
import os

from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

# ================================
# CONFIG FROM ENV VARS
# ================================

# Must be set in Render (or locally)
BOT_TOKEN = os.environ["BOT_TOKEN"]

# Optional, nice for display
BOTNAME = os.environ.get("BOTNAME", "TestBot")

# SCRIPT is a single string like: "Hi|How are you|What's up"
SCRIPT_RAW = os.environ.get(
    "SCRIPT",
    "Hey 😏|What are you doing right now?|Mmm okay… and what else?"
)
SCRIPT = [msg.strip() for msg in SCRIPT_RAW.split("|") if msg.strip()]

# Delays in seconds (min/max)
MIN_DELAY = float(os.environ.get("MIN_DELAY", "5"))
MAX_DELAY = float(os.environ.get("MAX_DELAY", "10"))

# user_id -> session dict
sessions: dict[int, dict] = {}


# ================================
# COMMAND HANDLERS
# ================================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    /start
    /start TESTID123
    """
    user_id = update.effective_user.id
    chat = update.effective_chat

    # Parse optional TestID from arguments
    test_id = None
    if context.args:
        test_id = context.args[0].strip()

    # Initialise session
    sessions[user_id] = {
        "test_id": test_id,
        "pending": list(SCRIPT),  # copy script
        "current": None,
        "log": [],
    }

    # Intro message
    if test_id:
        intro = (
            f"🔥 Hey! I'm {BOTNAME}.\n"
            f"This session is linked to *Test ID* `{test_id}`.\n\n"
            f"I'll send you a series of messages – reply as fast as you can."
        )
    else:
        intro = (
            f"🔥 Hey! I'm {BOTNAME}.\n"
            "I'll send you a series of messages – reply as fast as you can."
        )

    await context.bot.send_message(
        chat_id=chat.id,
        text=intro,
        parse_mode="Markdown",
    )

    # Send the very first question immediately (no delay),
    # then later ones will use MIN/MAX delay.
    await send_next_question(user_id, context, first=True)


# ================================
# SEND NEXT QUESTION
# ================================

async def send_next_question(
    user_id: int,
    context: ContextTypes.DEFAULT_TYPE,
    first: bool = False,
):
    """
    Sends the next scripted message.
    - If first == True -> no delay before sending.
    - Otherwise -> wait random delay between MIN_DELAY and MAX_DELAY.
    """
    session = sessions.get(user_id)
    if not session:
        return

    # No more questions left => finish
    if not session["pending"]:
        await finish_test(user_id, context)
        return

    # Delay only for non-first messages
    if not first:
        delay = random.uniform(MIN_DELAY, MAX_DELAY)
        await asyncio.sleep(delay)

    text = session["pending"].pop(0)

    msg = await context.bot.send_message(chat_id=user_id, text=text)

    # Track question + send time
    session["current"] = {
        "question": text,
        "sent_at": datetime.utcnow(),
        "message_id": msg.message_id,
    }


# ================================
# HANDLE USER REPLY
# ================================

async def handle_reply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    session = sessions.get(user_id)
    if not session or not session.get("current"):
        # Either no active test, or we’re between questions – ignore
        return

    now = datetime.utcnow()

    current_q = session["current"]
    current_q["replied_at"] = now
    session["log"].append(current_q)
    session["current"] = None

    # Immediately schedule next question (with delay inside function)
    await send_next_question(user_id, context, first=False)


# ================================
# FINISH TEST + SUMMARY
# ================================

async def finish_test(user_id: int, context: ContextTypes.DEFAULT_TYPE):
    session = sessions.get(user_id)
    if not session:
        return

    log = session["log"]
    test_id = session.get("test_id")

    if not log:
        await context.bot.send_message(
            chat_id=user_id,
            text="No replies received 🤔 – I’ve got nothing to grade."
        )
        del sessions[user_id]
        return

    total = 0.0
    max_diff = 0.0
    count = 0

    for entry in log:
        if "replied_at" not in entry or "sent_at" not in entry:
            continue
        diff = (entry["replied_at"] - entry["sent_at"]).total_seconds()
        total += diff
        max_diff = max(max_diff, diff)
        count += 1

    avg = total / count if count else 0.0

    # Build summary
    lines = [
        f"📊 *{BOTNAME} Reply Test Finished*",
        "",
        f"Questions answered: *{count}*",
        f"Average response time: *{avg:.1f} sec*",
        f"Slowest response: *{max_diff:.1f} sec*",
    ]

    if test_id:
        lines.append(f"Linked *Test ID:* `{test_id}`")

    text = "\n".join(lines)

    await context.bot.send_message(
        chat_id=user_id,
        text=text,
        parse_mode="Markdown",
    )

    # Clean up
    del sessions[user_id]


# ================================
# MAIN
# ================================

def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    # /start [TestID]
    app.add_handler(CommandHandler("start", start))

    # Any plain text (non-command) is treated as a reply
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_reply))

    app.run_polling()


if __name__ == "__main__":
    main()
