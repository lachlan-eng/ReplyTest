# multi_bot.py
import asyncio
import random
from datetime import datetime
from typing import Dict, Tuple, Any

from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

# ======================================================
# CONFIG: ALL YOUR BOTS LIVE HERE (ONE PROCESS)
# ======================================================
# ⚠️ Replace the TOKEN placeholders with your real tokens.
# Do NOT share tokens publicly.

BOTS = [
    {
        "name": "James",
        "handle": "@JamesTestBot",
        "token": "8278876847:AAEZwqFTZ7qOlkLWgOWtqQ84Pgo_EjO3tMg",
        "min_delay": 15,
        "max_delay": 24,
        "script": [
            "Hey, what are you doing right now? 😏",
            "Mmm alright… and what else are you thinking about?",
            "If I told you to talk to me nicer, how would you reply?",
        ],
        "type": "persona",
    },
    {
        "name": "Lachlan",
        "handle": "@LachlanTestBot",
        "token": "8588808709:AAH2wOpnkfWhUtcfmL7KaeOOqINL-xxSMXY",
        "min_delay": 12,
        "max_delay": 20,
        "script": [
            "Yo, you free for a quick test? 😈",
            "Don’t overthink it, just answer fast.",
            "Okay now flirt properly with me 👀",
        ],
        "type": "persona",
    },
    {
        "name": "Jayson",
        "handle": "@JaysonTestBot",
        "token": "8157527084:AAH7XkgQfxWWMawVUpqoqhCb-S7ApZI9Gj0",
        "min_delay": 10,
        "max_delay": 18,
        "script": [
            "Hey, I wanna see how fast you are.",
            "Reply instantly. No hesitation.",
            "Still with me? Prove it 😉",
        ],
        "type": "persona",
    },
    {
        "name": "Endi",
        "handle": "@EndiTestBot",
        "token": "8236314837:AAHozi2kHbzchRnsv6rK_SuHPbMjk_Foodw",
        "min_delay": 10,
        "max_delay": 18,
        "script": [
            "Let’s see how quick you really are.",
            "Imagine I’m watching your typing speed rn.",
            "Say the first thing that pops into your head.",
        ],
        "type": "persona",
    },
    {
        "name": "Starter",
        "handle": "@EnglishTestStarterBot",
        "token": "STARTER_BOT_TOKEN_HERE",
        "min_delay": 0,
        "max_delay": 0,
        "script": [],
        "type": "starter",
    },
]

# ======================================================
# STORAGE
# ======================================================

# (bot_id, user_id) -> session
SessionKey = Tuple[int, int]
Session = Dict[str, Any]
sessions: Dict[SessionKey, Session] = {}

# test_id -> metadata (for future centralisation if you want)
tests: Dict[str, Dict[str, Any]] = {}


# ======================================================
# UTILITIES
# ======================================================

def generate_test_id(length: int = 6) -> str:
    import string
    chars = string.ascii_uppercase + string.digits
    return "".join(random.choice(chars) for _ in range(length))


def get_persona_configs():
    return [cfg for cfg in BOTS if cfg["type"] == "persona"]


# ======================================================
# STARTER BOT HANDLERS
# ======================================================

async def starter_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "👋 Hey! I’m the Reply Test Starter.\n\n"
        "Use /newtest to create a new reply speed test.\n"
        "Then you’ll send a Test ID to the other bots so they all link to the same session."
    )
    await update.message.reply_text(text)


async def starter_newtest(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    chat = update.effective_chat

    test_id = generate_test_id()
    tests[test_id] = {
        "user_id": user.id,
        "created_at": datetime.utcnow(),
    }

    persona_cfgs = get_persona_configs()

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

    for cfg in persona_cfgs:
        handle = cfg.get("handle") or cfg["name"]
        lines.append(f"• {handle}")

    lines += [
        "",
        f"2️⃣ In *each* bot, send: `/start {test_id}`",
        "3️⃣ Then reply as fast as you can. Each bot measures your speed.",
    ]

    await context.bot.send_message(
        chat_id=chat.id,
        text="\n".join(lines),
        parse_mode="Markdown",
        disable_web_page_preview=True,
    )


# ======================================================
# PERSONA BOT HANDLERS
# ======================================================

async def persona_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    /start
    /start TESTID123
    """
    bot_id = context.bot.id
    user_id = update.effective_user.id
    key = (bot_id, user_id)

    cfg = context.application.bot_data["config"]
    args = context.args

    test_id = args[0].strip() if args else None

    sessions[key] = {
        "test_id": test_id,
        "pending": list(cfg["script"]),
        "current": None,
        "log": [],
    }

    intro_lines = [
        f"🔥 Hey! I’m {cfg['name']}.",
        "I’m going to test how fast you reply."
    ]
    if test_id:
        intro_lines.append(f"This session is linked to *Test ID* `{test_id}`.")

    await update.message.reply_text(
        "\n".join(intro_lines),
        parse_mode="Markdown",
    )

    # First question immediately
    await send_next_question(bot_id, user_id, context, first=True)


async def send_next_question(
    bot_id: int,
    user_id: int,
    context: ContextTypes.DEFAULT_TYPE,
    first: bool = False,
):
    key = (bot_id, user_id)
    session = sessions.get(key)
    if not session:
        return

    cfg = context.application.bot_data["config"]

    if not session["pending"]:
        await finish_test(bot_id, user_id, context)
        return

    if not first:
        delay = random.uniform(cfg["min_delay"], cfg["max_delay"])
        await asyncio.sleep(delay)

    text = session["pending"].pop(0)
    msg = await context.bot.send_message(chat_id=user_id, text=text)

    session["current"] = {
        "question": text,
        "sent_at": datetime.utcnow(),
        "message_id": msg.message_id,
    }


async def persona_handle_reply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    bot_id = context.bot.id
    user_id = update.effective_user.id
    key = (bot_id, user_id)

    session = sessions.get(key)
    if not session or not session.get("current"):
        return

    now = datetime.utcnow()
    current_q = session["current"]
    current_q["replied_at"] = now
    session["log"].append(current_q)
    session["current"] = None

    await send_next_question(bot_id, user_id, context, first=False)


async def finish_test(bot_id: int, user_id: int, context: ContextTypes.DEFAULT_TYPE):
    key = (bot_id, user_id)
    session = sessions.get(key)
    if not session:
        return

    cfg = context.application.bot_data["config"]
    log = session["log"]
    test_id = session.get("test_id")

    if not log:
        await context.bot.send_message(
            chat_id=user_id,
            text="No replies received 🤔 – nothing to grade."
        )
        del sessions[key]
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

    lines = [
        f"📊 *{cfg['name']} Reply Test Finished*",
        "",
        f"Questions answered: *{count}*",
        f"Average response time: *{avg:.1f} sec*",
        f"Slowest response: *{max_diff:.1f} sec*",
    ]
    if test_id:
        lines.append(f"Linked *Test ID:* `{test_id}`")

    await context.bot.send_message(
        chat_id=user_id,
        text="\n".join(lines),
        parse_mode="Markdown",
    )

    del sessions[key]


# ======================================================
# BOOTSTRAP: START ALL BOTS IN ONE PROCESS
# ======================================================

async def run_single_bot(cfg: dict):
    app: Application = ApplicationBuilder().token(cfg["token"]).build()
    app.bot_data["config"] = cfg

    if cfg["type"] == "starter":
        app.add_handler(CommandHandler("start", starter_start))
        app.add_handler(CommandHandler("newtest", starter_newtest))
    else:
        app.add_handler(CommandHandler("start", persona_start))
        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, persona_handle_reply))

    async with app:
        await app.start()
        await app.updater.start_polling()
        # Keep this bot alive forever
        await asyncio.Event().wait()


async def main():
    await asyncio.gather(*(run_single_bot(cfg) for cfg in BOTS))


if __name__ == "__main__":
    asyncio.run(main())
