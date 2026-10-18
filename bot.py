#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════╗
║   ꧁༒☬  𝐀𝐏𝐍𝐞𝐱𝐮𝐬𝐇𝐨𝐬𝐭  ☬༒꧂                                     ║
║   𝘛𝘩𝘦 𝘋𝘢𝘳𝘬 𝘚𝘪𝘥𝘦 𝘰𝘧 𝘏𝘰𝘴𝘵𝘪𝘯𝘨                                    ║
╚══════════════════════════════════════════════════════════════╝

Owner: @ap_ultimate07
"""
import asyncio
import logging
import os
import re
import sqlite3
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path

from telegram import (
    Bot,
    ChatMember,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Update,
)
from telegram.constants import ParseMode
from telegram.error import TelegramError
from telegram.ext import (
    Application,
    ApplicationHandlerStop,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    TypeHandler,
    filters,
)

# ═══════════════════════════════════════════════════════════════
# 🔧 CONFIG — Apna fresh token yahan daalo
# ═══════════════════════════════════════════════════════════════
MAIN_BOT_TOKEN = os.environ.get("MAIN_BOT_TOKEN", "8886148679:AAFWJmsLWBTdMAFVNDRWnHihyKG9cn_y3e8")
ADMIN_ID = int(os.environ.get("ADMIN_ID", "7773066702"))

DB_PATH = os.environ.get("DB_PATH", "nexus.db")
HOSTED_DIR = Path(os.environ.get("HOSTED_DIR", "hosted_bots"))
HOSTED_DIR.mkdir(exist_ok=True)

# Force subscribe
FORCE_SUB_CHANNEL = os.environ.get("FORCE_SUB_CHANNEL", "@apnumxinfo")
FORCE_SUB_GROUP = os.environ.get("FORCE_SUB_GROUP", "@apnumxinfoofficial")
FORCE_SUB_CHANNEL_LINK = "https://t.me/apnumxinfo"
FORCE_SUB_GROUP_LINK = "https://t.me/apnumxinfoofficial"

OWNER_USERNAME = "ap_ultimate07"

# ═══════════════════════════════════════════════════════════════
# 🎨 BRANDING
# ═══════════════════════════════════════════════════════════════
BRAND = "꧁༒☬ 𝐀𝐏𝐍𝐞𝐱𝐮𝐬𝐇𝐨𝐬𝐭 ☬༒꧂"
BRAND_SHORT = "𝐀𝐏𝐍𝐞𝐱𝐮𝐬𝐇𝐨𝐬𝐭"
TAGLINE = "𝘛𝘩𝘦 𝘋𝘢𝘳𝘬 𝘚𝘪𝘥𝘦 𝘰𝘧 𝘏𝘰𝘴𝘵𝘪𝘯𝘨"

# ═══════════════════════════════════════════════════════════════
# 📝 LOGGING
# ═══════════════════════════════════════════════════════════════
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s │ %(levelname)-7s │ %(name)-14s │ %(message)s",
    datefmt="%H:%M:%S",
)
logging.getLogger("httpx").setLevel(logging.WARNING)
logger = logging.getLogger("nexushost")

# ═══════════════════════════════════════════════════════════════
# 🗄️ DATABASE
# ═══════════════════════════════════════════════════════════════
def init_db():
    conn = sqlite3.connect(DB_PATH)
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS hosted_bots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            bot_token TEXT NOT NULL UNIQUE,
            bot_name TEXT,
            bot_username TEXT,
            file_path TEXT,
            file_size INTEGER,
            group_chat_id INTEGER,
            group_title TEXT,
            status TEXT DEFAULT 'pending',
            reject_reason TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            approved_at TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            first_name TEXT,
            joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            is_banned INTEGER DEFAULT 0
        );
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT
        );
    """)
    conn.commit()
    conn.close()


def db_exec(query, params=()):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute(query, params)
    conn.commit()
    rid = cur.lastrowid or 0
    conn.close()
    return rid


def db_fetch(query, params=()):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute(query, params)
    rows = cur.fetchall()
    conn.close()
    return rows


def get_setting(key, default=None):
    rows = db_fetch("SELECT value FROM settings WHERE key=?", (key,))
    return rows[0][0] if rows else default


def set_setting(key, value):
    db_exec("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", (key, value))


def register_user(user):
    try:
        db_exec(
            "INSERT OR IGNORE INTO users (user_id, username, first_name) VALUES (?, ?, ?)",
            (user.id, user.username or "", user.first_name or ""),
        )
    except Exception:
        pass


# ═══════════════════════════════════════════════════════════════
# 🎬 ANIMATION HELPERS
# ═══════════════════════════════════════════════════════════════
async def edit_safe(bot, chat_id, msg_id, text, kb=None):
    try:
        await bot.edit_message_text(
            text,
            chat_id=chat_id,
            message_id=msg_id,
            parse_mode=ParseMode.HTML,
            reply_markup=kb,
            disable_web_page_preview=True,
        )
        return True
    except TelegramError as e:
        if "message is not modified" not in str(e).lower():
            logger.debug(f"edit failed: {e}")
        return False


def progress_bar(pct, length=20):
    filled = int(length * pct / 100)
    return "█" * filled + "░" * (length - filled) + f" {pct}%"


async def animate_progress(bot, chat_id, msg_id, prefix, delays=0.25):
    for pct in [8, 22, 41, 58, 76, 89, 96, 100]:
        await edit_safe(bot, chat_id, msg_id, f"{prefix}\n\n<pre>{progress_bar(pct)}</pre>")
        await asyncio.sleep(delays)


async def skull_spinner(bot, chat_id, msg_id, label, frames=6):
    skulls = ["💀", "☠️", "💀", "☠️", "🔥", "⚡"]
    for i in range(frames):
        await edit_safe(bot, chat_id, msg_id, f"<b>{skulls[i % len(skulls)]} {label}</b>")
        await asyncio.sleep(0.4)


async def hacker_entry(bot, chat_id, msg_id, name, uid):
    # Phase 1: Init
    for f in ["⚡", "💀", "⌨️", "🔐"]:
        await edit_safe(bot, chat_id, msg_id, f"<b>{f} initializing...</b>")
        await asyncio.sleep(0.3)

    # Phase 2: Matrix rain
    matrix_frames = [
        "<pre>░▒▓█ ░▒▓█ ░▒▓█\n▒▓█░ ▒▓█░ ▒▓█░\n▓█░▒ ▓█░▒ ▓█░▒</pre>",
        "<pre>▒▓█░ ▒▓█░ ▒▓█░\n▓█░▒ ▓█░▒ ▓█░▒\n█░▒▓ █░▒▓ █░▒▓</pre>",
        "<pre>▓█░▒ ▓█░▒ ▓█░▒\n█░▒▓ █░▒▓ █░▒▓\n░▒▓█ ░▒▓█ ░▒▓█</pre>",
    ]
    for f in matrix_frames:
        await edit_safe(bot, chat_id, msg_id, f)
        await asyncio.sleep(0.4)

    # Phase 3: Terminal lines
    lines = [
        "&gt; Establishing secure connection...",
        "&gt; Bypassing firewall ████████████ 100%",
        "&gt; Decrypting access keys... [OK]",
        "&gt; Tracing IP address... [LOCKED]",
        "&gt; Access granted.",
    ]
    buf = "<pre>"
    for line in lines:
        buf += line + "\n"
        await edit_safe(bot, chat_id, msg_id, buf + "</pre>")
        await asyncio.sleep(0.5)

    # Phase 4: Logo
    logo = (
        "<pre>"
        "╔══════════════════════════════════╗\n"
        "║                                  ║\n"
        "║   ▄▀█ █▀█  𝐍𝐄𝐗𝐔𝐒  𝐇𝐎𝐒𝐓         ║\n"
        "║   █▀█ █▀▀  ☬༒☬  ☬༒꧂            ║\n"
        "║                                  ║\n"
        "║   𝘛𝘩𝘦 𝘋𝘢𝘳𝘬 𝘚𝘪𝘥𝘦 𝘰𝘧 𝘏𝘰𝘴𝘵𝘪𝘯𝘨       ║\n"
        "║                                  ║\n"
        "╚══════════════════════════════════╝"
        "</pre>"
    )
    await edit_safe(bot, chat_id, msg_id, logo)
    await asyncio.sleep(0.8)

    # Phase 5: Final menu
    welcome = (
        f"<b>{BRAND}</b>\n\n"
        f"<b>🖥️ WELCOME, {name.upper()}</b>\n\n"
        f"<pre>"
        f"▸ User ID : {uid}\n"
        f"▸ Session : GRANTED ✓\n"
        f"▸ Access  : LEVEL-1\n"
        f"▸ Time    : {datetime.now().strftime('%H:%M:%S')}\n"
        f"</pre>\n\n"
        f"<b>☠️ SYSTEM READY</b>\n\n"
        f"╭─ COMMANDS ──────────╮\n"
        f"│ /host    ▸ Submit bot\n"
        f"│ /status  ▸ Your fleet\n"
        f"│ /mybots  ▸ Live bots\n"
        f"│ /help    ▸ Manual\n"
        f"│ /cancel  ▸ Abort\n"
        f"╰─────────────────────╯"
    )
    kb = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🚀 HOST BOT", callback_data="btn:host"),
            InlineKeyboardButton("📁 MY BOTS", callback_data="btn:mybots"),
        ],
        [
            InlineKeyboardButton("📊 STATUS", callback_data="btn:status"),
            InlineKeyboardButton("ℹ️ HELP", callback_data="btn:help"),
        ],
        [
            InlineKeyboardButton(
                "👑 OWNER", url=f"https://t.me/{OWNER_USERNAME}"
            )
        ],
    ])
    await edit_safe(bot, chat_id, msg_id, welcome, kb)


# ═══════════════════════════════════════════════════════════════
# 🔐 FORCE SUBSCRIBE
# ═══════════════════════════════════════════════════════════════
async def is_subscribed(bot, user_id):
    missing = []
    for chat_ref, label, link in [
        (FORCE_SUB_CHANNEL, "📢 Channel", FORCE_SUB_CHANNEL_LINK),
        (FORCE_SUB_GROUP, "👥 Group", FORCE_SUB_GROUP_LINK),
    ]:
        try:
            m = await bot.get_chat_member(chat_ref, user_id)
            if m.status in (ChatMember.LEFT, ChatMember.BANNED):
                missing.append((label, link))
        except TelegramError:
            missing.append((label, link))
    return len(missing) == 0, missing


def force_sub_message(missing, user_id):
    kb_rows = [[InlineKeyboardButton(label, url=link)] for label, link in missing]
    kb_rows.append([InlineKeyboardButton("🔄 VERIFY ACCESS", callback_data="verify_sub")])
    return (
        f"<b>⚠️ ACCESS DENIED</b>\n\n"
        f"<pre>"
        f"&gt; Intrusion detected\n"
        f"&gt; User ID: {user_id}\n"
        f"&gt; Reason: Missing credentials\n"
        f"&gt; Action: Join required first\n"
        f"</pre>\n\n"
        f"<b>👇 Join these to proceed:</b>",
        InlineKeyboardMarkup(kb_rows),
    )


async def force_sub_check(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not user or user.id == ADMIN_ID:
        return
    # Allow verify button to re-run
    if update.callback_query and update.callback_query.data == "verify_sub":
        return
    ok, missing = await is_subscribed(context.bot, user.id)
    if ok:
        return
    text, kb = force_sub_message(missing, user.id)
    if update.callback_query:
        try:
            await update.callback_query.answer("Join first!", show_alert=True)
            await update.callback_query.message.edit_text(
                text, parse_mode=ParseMode.HTML, reply_markup=kb
            )
        except Exception:
            pass
    elif update.message:
        try:
            await update.message.reply_text(
                text, parse_mode=ParseMode.HTML, reply_markup=kb
            )
        except Exception:
            pass
    raise ApplicationHandlerStop


async def verify_sub_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    user = q.from_user
    ok, missing = await is_subscribed(context.bot, user.id)
    if not ok:
        await q.answer("❌ Still not joined!", show_alert=True)
        return
    await q.answer("✅ Access granted!")
    try:
        await q.message.edit_text(
            "<b>✅ ACCESS GRANTED</b>\n\n<pre>&gt; Verification complete\n&gt; Welcome back.</pre>",
            parse_mode=ParseMode.HTML,
        )
    except Exception:
        pass
    m = await q.message.reply_text("⚡")
    await hacker_entry(context.bot, m.chat_id, m.message_id, user.first_name or "Hacker", user.id)


# ═══════════════════════════════════════════════════════════════
# 🚀 SUB-BOT MANAGER
# ═══════════════════════════════════════════════════════════════
running_bots: dict[int, subprocess.Popen] = {}


def launch_subbot(sid, token, file_path, group_chat_id=None, group_title=None):
    work_dir = Path(file_path).parent
    log_path = work_dir / "output.log"
    log_file = open(log_path, "a", encoding="utf-8", buffering=1)

    env = {
        "BOT_TOKEN": token,
        "TELEGRAM_BOT_TOKEN": token,
        "PYTHONUNBUFFERED": "1",
        "PATH": os.environ.get("PATH", ""),
        "HOME": os.environ.get("HOME", "/tmp"),
    }
    if group_chat_id:
        env["GROUP_CHAT_ID"] = str(group_chat_id)
        env["GROUP_TITLE"] = group_title or ""

    proc = subprocess.Popen(
        [sys.executable, "-u", "bot.py"],
        cwd=str(work_dir),
        env=env,
        stdout=log_file,
        stderr=subprocess.STDOUT,
    )
    running_bots[sid] = proc
    logger.info(f"🚀 Sub-bot #{sid} launched (PID {proc.pid})")
    return proc


def stop_subbot(sid):
    proc = running_bots.pop(sid, None)
    if not proc:
        return False
    try:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait(timeout=2)
        logger.info(f"🛑 Sub-bot #{sid} stopped")
        return True
    except Exception as e:
        logger.error(f"Stop #{sid} failed: {e}")
        return False


async def monitor_loop(app):
    while True:
        await asyncio.sleep(25)
        for sid, proc in list(running_bots.items()):
            code = proc.poll()
            if code is not None:
                running_bots.pop(sid, None)
                try:
                    await app.bot.send_message(
                        ADMIN_ID,
                        f"<b>⚠️ ALERT</b>\n\n"
                        f"<pre>"
                        f"Bot #{sid} crashed\n"
                        f"Exit code: {code}\n"
                        f"</pre>\n"
                        f"<code>/logs {sid}</code> · <code>/restart {sid}</code>",
                        parse_mode=ParseMode.HTML,
                    )
                except Exception:
                    pass


# ═══════════════════════════════════════════════════════════════
# 👤 USER COMMANDS
# ═══════════════════════════════════════════════════════════════
async def start_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    register_user(user)
    m = await update.message.reply_text("⚡", parse_mode=ParseMode.HTML)
    await hacker_entry(
        context.bot, m.chat_id, m.message_id,
        user.first_name or "Hacker", user.id
    )


async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        f"<b>📖 {BRAND} — MANUAL</b>\n\n"
        f"<b>🚀 HOST A BOT</b>\n"
        f"<pre>"
        f"1. Get token from @BotFather\n"
        f"2. Write your bot.py (sample below)\n"
        f"3. Send /host\n"
        f"4. Upload bot.py\n"
        f"5. Send token\n"
        f"6. Provide group/channel link (optional)\n"
        f"7. Wait for admin approval"
        f"</pre>\n\n"
        f"<b>📝 YOUR BOT.PY MUST USE</b> <code>BOT_TOKEN</code> <b>env var:</b>\n"
        f"<pre>"
        f"import os\n"
        f"from telegram.ext import Application, CommandHandler\n\n"
        f"async def start(u, c):\n"
        f"    await u.message.reply_text('Hi!')\n\n"
        f"app = Application.builder() \\\n"
        f"    .token(os.environ['BOT_TOKEN']) \\\n"
        f"    .build()\n"
        f"app.add_handler(CommandHandler('start', start))\n"
        f"app.run_polling()"
        f"</pre>\n\n"
        f"<b>👥 GROUP/CHANNEL SUPPORT</b>\n"
        f"Your bot.py can read <code>GROUP_CHAT_ID</code> env var "
        f"if user provided a group during submission.\n\n"
        f"<b>⚠️ LIMITS</b>\n"
        f"<pre>"
        f"▸ Only python-telegram-bot installed\n"
        f"▸ Max file: 20 MB\n"
        f"▸ Max 3 submissions/day per user\n"
        f"▸ One token = one instance"
        f"</pre>\n\n"
        f"<b>👑 Owner:</b> @{OWNER_USERNAME}"
    )
    await update.message.reply_text(text, parse_mode=ParseMode.HTML)


# ═══════════════════════════════════════════════════════════════
# 📤 /host — CONVERSATION FLOW
# ═══════════════════════════════════════════════════════════════
WAITING_FOR_FILE = 1
WAITING_FOR_TOKEN = 2
WAITING_FOR_GROUP = 3


async def host_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.callback_query:
        await update.callback_query.answer()
        send = update.callback_query.message.reply_text
    else:
        send = update.message.reply_text

    # Maintenance check
    if get_setting("maintenance") == "on" and update.effective_user.id != ADMIN_ID:
        await send(
            "<b>⚠️ SYSTEM UNDER MAINTENANCE</b>\n\n"
            "<pre>&gt; Submissions temporarily paused\n"
            "&gt; Try again later</pre>",
            parse_mode=ParseMode.HTML,
        )
        return ConversationHandler.END

    # Rate limit
    user_id = update.effective_user.id
    recent = db_fetch(
        "SELECT COUNT(*) FROM hosted_bots WHERE user_id=? AND created_at > datetime('now', '-1 day')",
        (user_id,),
    )[0][0]
    if recent >= 3:
        await send(
            "<b>⛔ RATE LIMIT</b>\n\n"
            "<pre>&gt; Max 3 submissions per 24 hours\n"
            "&gt; Try tomorrow</pre>",
            parse_mode=ParseMode.HTML,
        )
        return ConversationHandler.END

    context.user_data.clear()
    intro = (
        f"<b>💻 SECURE CHANNEL ESTABLISHED</b>\n\n"
        f"<pre>"
        f"╔══════════════════════════════════╗\n"
        f"║  📎 STEP 1 OF 3 — UPLOAD FILE    ║\n"
        f"╚══════════════════════════════════╝\n\n"
        f"&gt; Send your bot.py file\n"
        f"&gt; Max size: 20 MB\n"
        f"&gt; Filename must be .py\n"
        f"</pre>\n\n"
        f"<b>❌ /cancel to abort</b>"
    )
    await send(intro, parse_mode=ParseMode.HTML)
    return WAITING_FOR_FILE


async def receive_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    doc = update.message.document
    if not doc:
        await update.message.reply_text(
            "<b>❌ INVALID</b>\n\n<pre>&gt; Send a .py file, not text</pre>",
            parse_mode=ParseMode.HTML,
        )
        return WAITING_FOR_FILE
    if not (doc.file_name or "").lower().endswith(".py"):
        await update.message.reply_text(
            "<b>❌ INVALID</b>\n\n<pre>&gt; File must end with .py</pre>",
            parse_mode=ParseMode.HTML,
        )
        return WAITING_FOR_FILE
    if doc.file_size and doc.file_size > 20 * 1024 * 1024:
        await update.message.reply_text(
            "<b>❌ TOO LARGE</b>\n\n<pre>&gt; Max 20 MB allowed</pre>",
            parse_mode=ParseMode.HTML,
        )
        return WAITING_FOR_FILE

    status = await update.message.reply_text(
        "📥 <b>DOWNLOADING...</b>", parse_mode=ParseMode.HTML
    )
    try:
        anim = asyncio.create_task(
            animate_progress(
                context.bot, status.chat_id, status.message_id,
                "📥 <b>DOWNLOADING...</b>", delays=0.15,
            )
        )
        tmp_path = HOSTED_DIR / f"tmp_{update.effective_user.id}_{int(datetime.now().timestamp())}.py"
        tg_file = await doc.get_file()
        await tg_file.download_to_drive(str(tmp_path))
        try:
            await anim
        except Exception:
            pass

        context.user_data["file_path"] = str(tmp_path)
        context.user_data["file_size"] = tmp_path.stat().st_size

        # Syntax check
        try:
            compile(tmp_path.read_text(encoding="utf-8"), str(tmp_path), "exec")
        except SyntaxError as e:
            tmp_path.unlink(missing_ok=True)
            await status.edit_text(
                f"<b>❌ SYNTAX ERROR</b>\n\n"
                f"<pre>Line {e.lineno}: {e.msg}</pre>\n\n"
                f"Fix and try /host again.",
                parse_mode=ParseMode.HTML,
            )
            return ConversationHandler.END

        await status.edit_text(
            f"<b>✅ FILE RECEIVED</b>\n\n"
            f"<pre>"
            f"&gt; Size: {context.user_data['file_size']:,} bytes\n"
            f"&gt; Syntax: VALID ✓\n"
            f"</pre>\n\n"
            f"<b>🔐 STEP 2 OF 3 — TOKEN</b>\n\n"
            f"<pre>"
            f"Send your BOT TOKEN\n"
            f"Format: 123456789:ABCdef...\n"
            f"</pre>\n\n"
            f"<b>❌ /cancel to abort</b>",
            parse_mode=ParseMode.HTML,
        )
        return WAITING_FOR_TOKEN
    except Exception as e:
        logger.error(f"Download error: {e}")
        try:
            await status.edit_text(
                f"<b>❌ DOWNLOAD FAILED</b>\n\n<pre>{str(e)[:120]}</pre>",
                parse_mode=ParseMode.HTML,
            )
        except Exception:
            pass
        return ConversationHandler.END


async def receive_token(update: Update, context: ContextTypes.DEFAULT_TYPE):
    token = (update.message.text or "").strip()
    user_id = update.effective_user.id
    file_path = context.user_data.get("file_path")

    if not file_path or not Path(file_path).exists():
        await update.message.reply_text(
            "<b>❌ SESSION EXPIRED</b>\n\nStart over with /host.",
            parse_mode=ParseMode.HTML,
        )
        return ConversationHandler.END

    if ":" not in token or len(token) < 20:
        await update.message.reply_text(
            "<b>❌ INVALID TOKEN FORMAT</b>\n\n"
            "<pre>Example: 123456789:ABCdef...</pre>",
            parse_mode=ParseMode.HTML,
        )
        return WAITING_FOR_TOKEN

    status = await update.message.reply_text(
        "🔍 <b>VALIDATING...</b>", parse_mode=ParseMode.HTML
    )
    try:
        temp = Bot(token=token)
        me = await temp.get_me()
        bot_username = me.username or "unknown"
        bot_name = me.first_name or "Unknown Bot"
    except Exception as e:
        try:
            await status.edit_text(
                f"<b>❌ TOKEN REJECTED</b>\n\n"
                f"<pre>{str(e)[:150]}</pre>\n\n"
                f"Try again or /cancel.",
                parse_mode=ParseMode.HTML,
            )
        except Exception:
            pass
        return WAITING_FOR_TOKEN

    # Duplicate check
    existing = db_fetch("SELECT id, status FROM hosted_bots WHERE bot_token=?", (token,))
    if existing:
        sid, st = existing[0]
        Path(file_path).unlink(missing_ok=True)
        await status.edit_text(
            f"<b>⚠️ ALREADY SUBMITTED</b>\n\n"
            f"<pre>ID: #{sid}\nStatus: {st.upper()}</pre>\n\n"
            f"Use /status to track.",
            parse_mode=ParseMode.HTML,
        )
        return ConversationHandler.END

    # Store for later
    context.user_data["token"] = token
    context.user_data["bot_username"] = bot_username
    context.user_data["bot_name"] = bot_name

    await status.edit_text(
        f"<b>✅ TOKEN VERIFIED</b>\n\n"
        f"<pre>"
        f"&gt; Bot: @{bot_username}\n"
        f"&gt; Name: {bot_name}\n"
        f"</pre>\n\n"
        f"<b>👥 STEP 3 OF 3 — GROUP/CHANNEL</b>\n\n"
        f"<pre>"
        f"Send group/channel link where bot\n"
        f"should be added (optional)\n\n"
        f"Examples:\n"
        f"  https://t.me/mychannel\n"
        f"  @mygroup\n"
        f"</pre>\n\n"
        f"Skip this step:",
        parse_mode=ParseMode.HTML,
        reply_markup=InlineKeyboardMarkup(
            [[InlineKeyboardButton("⏭️ SKIP", callback_data="skip:group")]]
        ),
    )
    return WAITING_FOR_GROUP


async def receive_group(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (update.message.text or "").strip()
    if text.lower() in ("/skip", "skip"):
        return await finalize_submission(update, context, None, None)

    # Parse chat ref
    chat_ref = text
    if "t.me/" in text:
        chat_ref = "@" + text.split("t.me/")[-1].split("/")[0].split("?")[0]
    elif not text.startswith("@"):
        if text.startswith("-100") or text.startswith("-"):
            chat_ref = text
        else:
            chat_ref = "@" + text

    try:
        chat = await context.bot.get_chat(chat_ref)
        return await finalize_submission(update, context, chat.id, chat.title or "")
    except Exception as e:
        await update.message.reply_text(
            f"<b>❌ CANNOT VERIFY</b>\n\n"
            f"<pre>{str(e)[:120]}</pre>\n\n"
            f"Try again, or /skip to continue without group.",
            parse_mode=ParseMode.HTML,
        )
        return WAITING_FOR_GROUP


async def skip_group_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    return await finalize_submission(update, context, None, None, from_cb=True)


async def finalize_submission(update, context, group_id, group_title, from_cb=False):
    user_id = update.effective_user.id
    uname = update.effective_user.username or "N/A"
    data = context.user_data

    if from_cb:
        chat_id = update.callback_query.message.chat_id
        msg_id = update.callback_query.message.message_id
        send = update.callback_query.message.reply_text
    else:
        chat_id = update.message.chat_id
        msg_id = update.message.message_id
        send = update.message.reply_text

    status = await send("🔄 <b>FINALIZING...</b>", parse_mode=ParseMode.HTML)
    await edit_safe(
        context.bot, status.chat_id, status.message_id,
        "🔄 <b>FINALIZING...</b>\n\n<pre>░▒▓█ ░▒▓█ ░▒▓█</pre>",
    )
    await asyncio.sleep(0.4)
    await edit_safe(
        context.bot, status.chat_id, status.message_id,
        "🔄 <b>FINALIZING...</b>\n\n<pre>▒▓█░ ▒▓█░ ▒▓█░</pre>",
    )
    await asyncio.sleep(0.4)

    try:
        sub_id = db_exec(
            "INSERT INTO hosted_bots "
            "(user_id, bot_token, bot_name, bot_username, file_path, file_size, "
            "group_chat_id, group_title, status) "
            "VALUES (?, ?, ?, ?, 'pending', ?, ?, ?, 'pending')",
            (
                user_id, data["token"], data["bot_name"], data["bot_username"],
                data["file_size"], group_id, group_title,
            ),
        )
        final_dir = HOSTED_DIR / str(sub_id)
        final_dir.mkdir(exist_ok=True)
        final_file = final_dir / "bot.py"
        Path(data["file_path"]).replace(final_file)
        db_exec("UPDATE hosted_bots SET file_path=? WHERE id=?", (str(final_file), sub_id))
    except Exception as e:
        logger.error(f"DB error: {e}")
        await edit_safe(
            context.bot, status.chat_id, status.message_id,
            f"<b>❌ SUBMISSION FAILED</b>\n\n<pre>{str(e)[:150]}</pre>",
        )
        return ConversationHandler.END

    group_line = f"&gt; Group: {group_title}\n" if group_id else "&gt; Group: (none)\n"
    success = (
        f"<b>✅ SUBMISSION COMPLETE</b>\n\n"
        f"<pre>"
        f"╔══════════════════════════════════╗\n"
        f"║  🎉 SUCCESSFULLY SUBMITTED       ║\n"
        f"╚══════════════════════════════════╝\n\n"
        f"&gt; ID: #{sub_id}\n"
        f"&gt; Bot: @{data['bot_username']}\n"
        f"&gt; Name: {data['bot_name']}\n"
        f"&gt; Size: {data['file_size']:,} bytes\n"
        f"{group_line}"
        f"&gt; Status: ⏳ PENDING\n"
        f"</pre>\n\n"
        f"<b>⏰ Awaiting admin approval...</b>\n"
        f"Track with /status"
    )
    await edit_safe(context.bot, status.chat_id, status.message_id, success)

    # Notify admin
    admin_card = (
        f"<b>🔔 NEW SUBMISSION</b>\n\n"
        f"<pre>"
        f"╔══════════════════════════════════╗\n"
        f"║  🎯 TARGET DETECTED              ║\n"
        f"╚══════════════════════════════════╝\n\n"
        f"&gt; ID: #{sub_id}\n"
        f"&gt; Bot: @{data['bot_username']}\n"
        f"&gt; Name: {data['bot_name']}\n"
        f"&gt; User: @{uname} ({user_id})\n"
        f"&gt; Size: {data['file_size']:,} bytes\n"
        f"{group_line}"
        f"&gt; Token: {data['token'][:12]}...{data['token'][-4:]}\n"
        f"</pre>\n\n"
        f"<b>⚠️ Review carefully</b>"
    )
    kb = InlineKeyboardMarkup([[
        InlineKeyboardButton("✅ DEPLOY", callback_data=f"approve:{sub_id}"),
        InlineKeyboardButton("❌ TERMINATE", callback_data=f"reject:{sub_id}"),
    ]])
    try:
        await context.bot.send_message(
            ADMIN_ID, admin_card,
            parse_mode=ParseMode.HTML, reply_markup=kb,
        )
    except Exception as e:
        logger.error(f"Admin notify failed: {e}")

    context.user_data.clear()
    return ConversationHandler.END


async def cancel_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    fp = context.user_data.get("file_path")
    if fp and Path(fp).exists() and "tmp_" in Path(fp).name:
        Path(fp).unlink(missing_ok=True)
    context.user_data.clear()
    await update.message.reply_text(
        "<b>❌ CANCELLED</b>\n\n<pre>&gt; Operation aborted</pre>",
        parse_mode=ParseMode.HTML,
    )
    return ConversationHandler.END


# ═══════════════════════════════════════════════════════════════
# 📁 /status, /mybots
# ═══════════════════════════════════════════════════════════════
STATUS_EMOJI = {"pending": "⏳", "approved": "✅", "rejected": "❌"}


async def status_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.callback_query:
        await update.callback_query.answer()
        send = update.callback_query.message.reply_text
    else:
        send = update.message.reply_text

    user_id = update.effective_user.id
    rows = db_fetch(
        "SELECT id, bot_username, status, created_at FROM hosted_bots "
        "WHERE user_id=? ORDER BY id DESC LIMIT 10",
        (user_id,),
    )
    if not rows:
        await send(
            "<b>📭 NO SUBMISSIONS</b>\n\nStart with /host",
            parse_mode=ParseMode.HTML,
        )
        return

    text = f"<b>📁 YOUR FLEET</b>\n\n<pre>"
    for sid, uname, st, created in rows:
        emoji = STATUS_EMOJI.get(st, "❓")
        live = " 🟢" if sid in running_bots else ""
        text += f"{emoji} #{sid} · @{uname or 'unknown'}{live}\n"
        text += f"   └ {st.upper()} · {created}\n"
    text += "</pre>"
    await send(text, parse_mode=ParseMode.HTML)


async def mybots_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.callback_query:
        await update.callback_query.answer()
        send = update.callback_query.message.reply_text
    else:
        send = update.message.reply_text

    user_id = update.effective_user.id
    rows = db_fetch(
        "SELECT id, bot_username, status FROM hosted_bots "
        "WHERE user_id=? AND status='approved'",
        (user_id,),
    )
    if not rows:
        await send(
            "<b>🤖 NO LIVE BOTS</b>\n\nGet approved first with /host",
            parse_mode=ParseMode.HTML,
        )
        return

    text = "<b>🤖 LIVE BOTS</b>\n\n<pre>"
    for sid, uname, _ in rows:
        live = "🟢 RUNNING" if sid in running_bots else "🔴 OFFLINE"
        text += f"#{sid} · @{uname} · {live}\n"
    text += "</pre>"
    await send(text, parse_mode=ParseMode.HTML)


# ═══════════════════════════════════════════════════════════════
# 🎛️ ADMIN — APPROVAL CALLBACKS
# ═══════════════════════════════════════════════════════════════
async def approval_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()

    if q.from_user.id != ADMIN_ID:
        await q.answer("⛔ Unauthorized.", show_alert=True)
        return

    try:
        action, sid_str = q.data.split(":", 1)
        sid = int(sid_str)
    except Exception:
        return

    row = db_fetch(
        "SELECT user_id, bot_token, bot_username, status, file_path, group_chat_id, group_title "
        "FROM hosted_bots WHERE id=?",
        (sid,),
    )
    if not row:
        await q.edit_message_text(f"❌ #{sid} not found.", parse_mode=ParseMode.HTML)
        return

    user_id, token, username, status, file_path, gcid, gtitle = row[0]

    if status != "pending":
        await q.edit_message_text(
            f"<b>⚠️ #{sid} already {status.upper()}</b>",
            parse_mode=ParseMode.HTML,
        )
        return

    if action == "approve":
        await q.edit_message_text(
            f"<b>🚀 DEPLOYING #{sid}</b>\n\n<pre>{progress_bar(0)}</pre>",
            parse_mode=ParseMode.HTML,
        )
        await animate_progress(
            context.bot, q.message.chat_id, q.message.message_id,
            f"🚀 <b>DEPLOYING #{sid}</b>", delays=0.2,
        )

        proc = launch_subbot(sid, token, file_path, gcid, gtitle)
        await asyncio.sleep(3.5)

        if proc.poll() is None:
            db_exec(
                "UPDATE hosted_bots SET status='approved', approved_at=CURRENT_TIMESTAMP WHERE id=?",
                (sid,),
            )
            await q.edit_message_text(
                f"<b>✅ DEPLOYED #{sid}</b>\n\n"
                f"<pre>"
                f"&gt; Bot: @{username}\n"
                f"&gt; PID: {proc.pid}\n"
                f"&gt; Status: LIVE 🟢\n"
                f"</pre>",
                parse_mode=ParseMode.HTML,
            )
            try:
                await context.bot.send_message(
                    user_id,
                    f"<b>🎉 BOT LIVE</b>\n\n"
                    f"<pre>"
                    f"&gt; @{username} is now LIVE!\n"
                    f"&gt; ID: #{sid}\n"
                    f"</pre>",
                    parse_mode=ParseMode.HTML,
                )
            except Exception:
                pass
        else:
            log_path = Path(file_path).parent / "output.log"
            tail = ""
            if log_path.exists():
                tail = "\n".join(log_path.read_text(errors="ignore").split("\n")[-5:])
            db_exec("UPDATE hosted_bots SET status='rejected' WHERE id=?", (sid,))
            await q.edit_message_text(
                f"<b>❌ DEPLOY FAILED #{sid}</b>\n\n"
                f"<pre>{tail[:400]}</pre>",
                parse_mode=ParseMode.HTML,
            )

    elif action == "reject":
        db_exec("UPDATE hosted_bots SET status='rejected' WHERE id=?", (sid,))
        try:
            Path(file_path).unlink(missing_ok=True)
        except Exception:
            pass
        await q.edit_message_text(
            f"<b>❌ REJECTED #{sid} (@{username})</b>",
            parse_mode=ParseMode.HTML,
        )
        try:
            await context.bot.send_message(
                user_id,
                f"<b>❌ BOT REJECTED</b>\n\n"
                f"<pre>&gt; @{username} was rejected\n"
                f"&gt; Contact admin</pre>",
                parse_mode=ParseMode.HTML,
            )
        except Exception:
            pass


# ═══════════════════════════════════════════════════════════════
# 🎛️ ADMIN — COMMANDS
# ═══════════════════════════════════════════════════════════════
def _is_admin(update):
    return update.effective_user and update.effective_user.id == ADMIN_ID


async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not _is_admin(update):
        return
    total = db_fetch("SELECT COUNT(*) FROM hosted_bots")[0][0]
    pend = db_fetch("SELECT COUNT(*) FROM hosted_bots WHERE status='pending'")[0][0]
    appr = db_fetch("SELECT COUNT(*) FROM hosted_bots WHERE status='approved'")[0][0]
    rej = db_fetch("SELECT COUNT(*) FROM hosted_bots WHERE status='rejected'")[0][0]
    users = db_fetch("SELECT COUNT(*) FROM users")[0][0]
    maint = get_setting("maintenance", "off")

    text = (
        f"<b>⌨️ ADMIN PANEL</b>\n"
        f"<b>{BRAND}</b>\n\n"
        f"<pre>"
        f"╔══════════════════════════════════╗\n"
        f"║  🖥️ SYSTEM STATUS: ONLINE 🟢     ║\n"
        f"╠══════════════════════════════════╣\n"
        f"║  📊 STATISTICS                   ║\n"
        f"║  ├─ Users     : {users:<17}║\n"
        f"║  ├─ Total     : {total:<17}║\n"
        f"║  ├─ Pending   : {pend:<17}║\n"
        f"║  ├─ Approved  : {appr:<17}║\n"
        f"║  ├─ Rejected  : {rej:<17}║\n"
        f"║  └─ Running   : {len(running_bots):<17}║\n"
        f"╠══════════════════════════════════╣\n"
        f"║  🔧 MAINTENANCE: {maint.upper():<17}║\n"
        f"╚══════════════════════════════════╝"
        f"</pre>"
    )
    kb = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("📋 PENDING", callback_data="adm:pending"),
            InlineKeyboardButton("📊 STATS", callback_data="adm:stats"),
        ],
        [
            InlineKeyboardButton("👥 USERS", callback_data="adm:users"),
            InlineKeyboardButton("📢 BROADCAST", callback_data="adm:broadcast"),
        ],
        [
            InlineKeyboardButton(
                f"🔧 MAINT {'OFF' if maint=='off' else 'ON'}",
                callback_data="adm:maint"
            ),
        ],
    ])
    await update.message.reply_text(text, parse_mode=ParseMode.HTML, reply_markup=kb)


async def admin_pending(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not _is_admin(update):
        return
    rows = db_fetch(
        "SELECT id, user_id, bot_username, created_at FROM hosted_bots "
        "WHERE status='pending' ORDER BY id DESC"
    )
    if not rows:
        await update.message.reply_text(
            "<b>✅ No pending submissions</b>", parse_mode=ParseMode.HTML
        )
        return
    await update.message.reply_text(
        f"<b>📋 {len(rows)} PENDING</b>", parse_mode=ParseMode.HTML
    )
    for sid, uid, uname, created in rows:
        kb = InlineKeyboardMarkup([[
            InlineKeyboardButton("✅ DEPLOY", callback_data=f"approve:{sid}"),
            InlineKeyboardButton("❌ REJECT", callback_data=f"reject:{sid}"),
        ]])
        await update.message.reply_text(
            f"<pre>#{sid} · @{uname}\nUser: {uid}\n{created}</pre>",
            reply_markup=kb, parse_mode=ParseMode.HTML,
        )


async def admin_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not _is_admin(update):
        return
    total = db_fetch("SELECT COUNT(*) FROM hosted_bots")[0][0]
    pend = db_fetch("SELECT COUNT(*) FROM hosted_bots WHERE status='pending'")[0][0]
    appr = db_fetch("SELECT COUNT(*) FROM hosted_bots WHERE status='approved'")[0][0]
    rej = db_fetch("SELECT COUNT(*) FROM hosted_bots WHERE status='rejected'")[0][0]
    users = db_fetch("SELECT COUNT(*) FROM users")[0][0]
    await update.message.reply_text(
        f"<b>📊 SYSTEM STATS</b>\n\n<pre>"
        f"Users    : {users}\n"
        f"Total    : {total}\n"
        f"Pending  : {pend}\n"
        f"Approved : {appr}\n"
        f"Rejected : {rej}\n"
        f"Running  : {len(running_bots)}\n"
        f"</pre>",
        parse_mode=ParseMode.HTML,
    )


async def admin_users(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not _is_admin(update):
        return
    rows = db_fetch("SELECT user_id, username, first_name, joined_at FROM users ORDER BY joined_at DESC LIMIT 50")
    if not rows:
        await update.message.reply_text("<b>No users yet.</b>", parse_mode=ParseMode.HTML)
        return
    text = f"<b>👥 USERS (last 50)</b>\n\n<pre>"
    for uid, uname, fname, joined in rows:
        text += f"{uid} · @{uname or '-'} · {fname or '-'}\n"
    text += "</pre>"
    await update.message.reply_text(text, parse_mode=ParseMode.HTML)


async def admin_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not _is_admin(update):
        return
    if not context.args:
        await update.message.reply_text(
            "<b>Usage:</b> <code>/broadcast your message here</code>",
            parse_mode=ParseMode.HTML,
        )
        return
    msg = " ".join(context.args)
    users = db_fetch("SELECT user_id FROM users")
    sent = 0
    failed = 0
    for (uid,) in users:
        try:
            await context.bot.send_message(
                uid,
                f"<b>📢 ANNOUNCEMENT</b>\n\n{msg}",
                parse_mode=ParseMode.HTML,
            )
            sent += 1
            await asyncio.sleep(0.05)
        except Exception:
            failed += 1
    await update.message.reply_text(
        f"<pre>✅ Sent: {sent}\n❌ Failed: {failed}</pre>",
        parse_mode=ParseMode.HTML,
    )


async def admin_maintenance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not _is_admin(update):
        return
    if not context.args or context.args[0].lower() not in ("on", "off"):
        await update.message.reply_text(
            "<b>Usage:</b> <code>/maintenance on</code> or <code>/maintenance off</code>",
            parse_mode=ParseMode.HTML,
        )
        return
    val = context.args[0].lower()
    set_setting("maintenance", val)
    await update.message.reply_text(
        f"<b>🔧 Maintenance: {val.upper()}</b>",
        parse_mode=ParseMode.HTML,
    )


async def admin_stop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not _is_admin(update) or not context.args:
        return
    try:
        sid = int(context.args[0])
    except ValueError:
        return
    ok = stop_subbot(sid)
    await update.message.reply_text(
        f"<pre>{'🛑 Stopped' if ok else '⚠️ Not running'} #{sid}</pre>",
        parse_mode=ParseMode.HTML,
    )


async def admin_restart(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not _is_admin(update) or not context.args:
        return
    try:
        sid = int(context.args[0])
    except ValueError:
        return
    row = db_fetch(
        "SELECT bot_token, file_path, status, group_chat_id, group_title FROM hosted_bots WHERE id=?",
        (sid,),
    )
    if not row or row[0][2] != "approved":
        await update.message.reply_text(
            f"<pre>⚠️ #{sid} is not approved</pre>", parse_mode=ParseMode.HTML
        )
        return
    stop_subbot(sid)
    await asyncio.sleep(1)
    token, fp, _, gcid, gtitle = row[0]
    proc = launch_subbot(sid, token, fp, gcid, gtitle)
    await asyncio.sleep(2.5)
    if proc.poll() is None:
        await update.message.reply_text(
            f"<pre>🔁 Restarted #{sid} (PID {proc.pid})</pre>",
            parse_mode=ParseMode.HTML,
        )
    else:
        await update.message.reply_text(
            f"<pre>❌ Restart failed. Check /logs {sid}</pre>",
            parse_mode=ParseMode.HTML,
        )


async def admin_delete(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not _is_admin(update) or not context.args:
        return
    try:
        sid = int(context.args[0])
    except ValueError:
        return
    stop_subbot(sid)
    row = db_fetch("SELECT file_path FROM hosted_bots WHERE id=?", (sid,))
    if row and row[0][0]:
        try:
            import shutil
            shutil.rmtree(Path(row[0][0]).parent, ignore_errors=True)
        except Exception:
            pass
    db_exec("DELETE FROM hosted_bots WHERE id=?", (sid,))
    await update.message.reply_text(
        f"<pre>🗑 Deleted #{sid}</pre>", parse_mode=ParseMode.HTML
    )


async def admin_logs(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not _is_admin(update) or not context.args:
        return
    try:
        sid = int(context.args[0])
    except ValueError:
        return
    log_path = HOSTED_DIR / str(sid) / "output.log"
    if not log_path.exists():
        await update.message.reply_text(
            f"<pre>No logs for #{sid}</pre>", parse_mode=ParseMode.HTML
        )
        return
    tail = "\n".join(log_path.read_text(errors="ignore").split("\n")[-30:])
    await update.message.reply_text(
        f"<b>📄 LOGS #{sid}</b>\n<pre>{tail[:3500]}</pre>",
        parse_mode=ParseMode.HTML,
    )


# ═══════════════════════════════════════════════════════════════
# 🎛️ ADMIN BUTTON CALLBACKS
# ═══════════════════════════════════════════════════════════════
async def admin_button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    if q.from_user.id != ADMIN_ID:
        return
    data = q.data

    if data == "adm:maint":
        cur = get_setting("maintenance", "off")
        new = "on" if cur == "off" else "off"
        set_setting("maintenance", new)
        await q.answer(f"Maintenance: {new.upper()}", show_alert=True)
        return

    if data == "adm:broadcast":
        await q.message.reply_text(
            "<b>📢 BROADCAST</b>\n\n<pre>Usage: /broadcast your message</pre>",
            parse_mode=ParseMode.HTML,
        )
        return

    # Delegate to existing commands
    class FakeUpdate:
        pass
    fake = FakeUpdate()
    fake.message = q.message
    fake.effective_user = q.from_user
    fake.callback_query = None

    if data == "adm:pending":
        await admin_pending(fake, context)
    elif data == "adm:stats":
        await admin_stats(fake, context)
    elif data == "adm:users":
        await admin_users(fake, context)


# ═══════════════════════════════════════════════════════════════
# 🎯 BUTTON REDIRECTS (user menu)
# ═══════════════════════════════════════════════════════════════
async def menu_button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    data = q.data

    if data == "btn:status":
        await q.answer()
        fake = type("U", (), {})()
        fake.message = q.message
        fake.effective_user = q.from_user
        fake.callback_query = q
        await status_cmd(fake, context)
    elif data == "btn:mybots":
        await q.answer()
        fake = type("U", (), {})()
        fake.message = q.message
        fake.effective_user = q.from_user
        fake.callback_query = q
        await mybots_cmd(fake, context)
    elif data == "btn:help":
        await q.answer()
        fake = type("U", (), {})()
        fake.message = q.message
        fake.effective_user = q.from_user
        fake.callback_query = None
        await help_cmd(fake, context)


# ═══════════════════════════════════════════════════════════════
# 🔄 STARTUP / SHUTDOWN
# ═══════════════════════════════════════════════════════════════
async def post_init(app):
    rows = db_fetch(
        "SELECT id, bot_token, file_path, group_chat_id, group_title "
        "FROM hosted_bots WHERE status='approved'"
    )
    logger.info(f"🔄 Auto-starting {len(rows)} approved bots...")
    for sid, token, fp, gcid, gtitle in rows:
        if fp and Path(fp).exists():
            try:
                launch_subbot(sid, token, fp, gcid, gtitle)
                await asyncio.sleep(0.6)
            except Exception as e:
                logger.error(f"Failed to start #{sid}: {e}")
    asyncio.create_task(monitor_loop(app))


async def post_shutdown(app):
    logger.info("🛑 Shutting down...")
    for sid in list(running_bots.keys()):
        stop_subbot(sid)


# ═══════════════════════════════════════════════════════════════
# 🚀 MAIN
# ═══════════════════════════════════════════════════════════════
def main():
    if not MAIN_BOT_TOKEN or MAIN_BOT_TOKEN == "PASTE_YOUR_NEW_TOKEN_HERE":
        print("❌ MAIN_BOT_TOKEN set karo (fresh token)!")
        sys.exit(1)
    if not ADMIN_ID:
        print("❌ ADMIN_ID required!")
        sys.exit(1)

    init_db()
    logger.info("📁 Database ready")

    app = (
        Application.builder()
        .token(MAIN_BOT_TOKEN)
        .post_init(post_init)
        .post_shutdown(post_shutdown)
        .build()
    )

    # Force subscribe — MUST be group -1 (runs first)
    app.add_handler(TypeHandler(Update, force_sub_check), group=-1)

    # Host conversation
    conv = ConversationHandler(
        entry_points=[
            CommandHandler("host", host_start),
            CallbackQueryHandler(host_start, pattern="^btn:host$"),
        ],
        states={
            WAITING_FOR_FILE: [MessageHandler(filters.Document.ALL, receive_file)],
            WAITING_FOR_TOKEN: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, receive_token)
            ],
            WAITING_FOR_GROUP: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, receive_group),
                CallbackQueryHandler(skip_group_callback, pattern="^skip:group$"),
            ],
        },
        fallbacks=[CommandHandler("cancel", cancel_cmd)],
        allow_reentry=True,
    )

    # User commands
    app.add_handler(CommandHandler("start", start_cmd))
    app.add_handler(CommandHandler("help", help_cmd))
    app.add_handler(CommandHandler("status", status_cmd))
    app.add_handler(CommandHandler("mybots", mybots_cmd))
    app.add_handler(CommandHandler("cancel", cancel_cmd))
    app.add_handler(conv)

    # Menu buttons
    app.add_handler(CallbackQueryHandler(
        menu_button_callback, pattern="^btn:(status|mybots|help)$"
    ))

    # Verify subscription button
    app.add_handler(CallbackQueryHandler(verify_sub_callback, pattern="^verify_sub$"))

    # Approval
    app.add_handler(CallbackQueryHandler(
        approval_callback, pattern=r"^(approve|reject):\d+$"
    ))

    # Admin commands
    app.add_handler(CommandHandler("panel", admin_panel))
    app.add_handler(CommandHandler("pending", admin_pending))
    app.add_handler(CommandHandler("stats", admin_stats))
    app.add_handler(CommandHandler("users", admin_users))
    app.add_handler(CommandHandler("broadcast", admin_broadcast))
    app.add_handler(CommandHandler("maintenance", admin_maintenance))
    app.add_handler(CommandHandler("stop", admin_stop))
    app.add_handler(CommandHandler("restart", admin_restart))
    app.add_handler(CommandHandler("delete", admin_delete))
    app.add_handler(CommandHandler("logs", admin_logs))

    # Admin buttons
    app.add_handler(CallbackQueryHandler(admin_button_callback, pattern="^adm:"))

    logger.info(f"🚀 {BRAND_SHORT} starting...")
    app.run_polling(
        allowed_updates=Update.ALL_TYPES,
        drop_pending_updates=True,
    )


if __name__ == "__main__":
    main()