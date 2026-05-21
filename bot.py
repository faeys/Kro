import logging
import secrets
import sqlite3
from datetime import datetime
from functools import wraps
import os

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    CallbackQueryHandler, ConversationHandler, ContextTypes, filters,
)

# ── Config ────────────────────────────────────────────────────────────────────
BOT_TOKEN = os.environ.get("BOT_TOKEN", "PON_TU_TOKEN_AQUI")
ADMIN_IDS  = set(map(int, os.environ.get("ADMIN_IDS", "0").split(",")))

logging.basicConfig(format="%(asctime)s | %(levelname)s | %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

WAITING_KEY = 1

# ══════════════════════════════════════════════════════════════════════════════
# BASE DE DATOS
# ══════════════════════════════════════════════════════════════════════════════
def init_db():
    con = sqlite3.connect("bot.db")
    con.execute("""CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY, username TEXT, full_name TEXT,
        registered TEXT, banned INTEGER DEFAULT 0)""")
    con.execute("""CREATE TABLE IF NOT EXISTS keys (
        key TEXT PRIMARY KEY, created_by INTEGER, created_at TEXT,
        used_by INTEGER DEFAULT NULL, used_at TEXT DEFAULT NULL)""")
    con.commit(); con.close()

def db():
    con = sqlite3.connect("bot.db"); con.row_factory = sqlite3.Row; return con

def user_exists(uid):
    with db() as c: return c.execute("SELECT 1 FROM users WHERE user_id=?", (uid,)).fetchone() is not None

def user_is_banned(uid):
    with db() as c:
        r = c.execute("SELECT banned FROM users WHERE user_id=?", (uid,)).fetchone()
        return bool(r and r["banned"])

def register_user(uid, username, full_name):
    with db() as c:
        c.execute("INSERT OR IGNORE INTO users (user_id,username,full_name,registered) VALUES (?,?,?,?)",
                  (uid, username or "sin_username", full_name, datetime.now().isoformat()))
        c.commit()

def key_is_valid(key):
    with db() as c: return c.execute("SELECT 1 FROM keys WHERE key=? AND used_by IS NULL", (key,)).fetchone() is not None

def use_key(key, uid):
    with db() as c:
        c.execute("UPDATE keys SET used_by=?, used_at=? WHERE key=?", (uid, datetime.now().isoformat(), key)); c.commit()

def create_key(created_by):
    k = secrets.token_urlsafe(10)
    with db() as c:
        c.execute("INSERT INTO keys (key,created_by,created_at) VALUES (?,?,?)", (k, created_by, datetime.now().isoformat())); c.commit()
    return k

def get_all_users():
    with db() as c: return c.execute("SELECT * FROM users ORDER BY registered DESC").fetchall()

def get_all_keys():
    with db() as c: return c.execute("SELECT * FROM keys ORDER BY created_at DESC").fetchall()

def ban_user(uid):
    with db() as c: c.execute("UPDATE users SET banned=1 WHERE user_id=?", (uid,)); c.commit()

def unban_user(uid):
    with db() as c: c.execute("UPDATE users SET banned=0 WHERE user_id=?", (uid,)); c.commit()

def delete_key(key):
    with db() as c: c.execute("DELETE FROM keys WHERE key=? AND used_by IS NULL", (key,)); c.commit()

# ══════════════════════════════════════════════════════════════════════════════
# DECORADORES
# ══════════════════════════════════════════════════════════════════════════════
def admin_only(func):
    @wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        if update.effective_user.id not in ADMIN_IDS:
            await update.message.reply_text("⛔ No tienes permiso.")
            return
        return await func(update, context)
    return wrapper

def registered_only(func):
    @wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        uid = update.effective_user.id
        if uid in ADMIN_IDS: return await func(update, context)
        if not user_exists(uid):
            await update.message.reply_text("🔒 Usa /start para registrarte."); return
        if user_is_banned(uid):
            await update.message.reply_text("🚫 Has sido baneado."); return
        return await func(update, context)
    return wrapper

# ══════════════════════════════════════════════════════════════════════════════
# HANDLERS — USUARIOS
# ══════════════════════════════════════════════════════════════════════════════
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid  = update.effective_user.id
    user = update.effective_user

    if uid in ADMIN_IDS:
        await update.message.reply_text(
            f"👑 Bienvenido Admin *{user.first_name}*\!\n\n"
            "Comandos de admin:\n"
            "/genkey — Generar 1 key\n"
            "/genkey 5 — Generar 5 keys\n"
            "/listkeys — Ver todas las keys\n"
            "/listusers — Ver usuarios\n"
            "/ban ID — Banear usuario\n"
            "/unban ID — Desbanear usuario\n"
            "/revokekey KEY — Eliminar key\n"
            "/stats — Estadísticas",
            parse_mode="MarkdownV2")
        return ConversationHandler.END

    if user_exists(uid):
        if user_is_banned(uid):
            await update.message.reply_text("🚫 Has sido baneado\.")
        else:
            await update.message.reply_text(
                f"✅ Hola *{user.first_name}*, ya estás registrado\.\nUsa /menu\.",
                parse_mode="MarkdownV2")
        return ConversationHandler.END

    await update.message.reply_text(
        "🔐 *Acceso restringido*\n\nEste bot requiere una clave de acceso\.\nIngresa tu key:",
        parse_mode="MarkdownV2")
    return WAITING_KEY

async def receive_key(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid  = update.effective_user.id
    user = update.effective_user
    key  = update.message.text.strip()

    if key_is_valid(key):
        use_key(key, uid)
        register_user(uid, user.username, user.full_name)
        for admin_id in ADMIN_IDS:
            try:
                await context.bot.send_message(admin_id,
                    f"🆕 Nuevo usuario registrado\!\n👤 *{user.full_name}*\n🆔 `{uid}`\n📎 @{user.username or 'sin\\_username'}\n🔑 Key: `{key}`",
                    parse_mode="MarkdownV2")
            except: pass
        await update.message.reply_text(
            f"✅ *¡Acceso concedido\!*\n\nBienvenido *{user.first_name}*\.\nUsa /menu\.",
            parse_mode="MarkdownV2")
    else:
        await update.message.reply_text("❌ *Key inválida o ya utilizada\.*\nContacta al administrador\.", parse_mode="MarkdownV2")
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Cancelado\.")
    return ConversationHandler.END

@registered_only
async def menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("👤 Mi perfil", callback_data="profile")],
        [InlineKeyboardButton("ℹ️ Ayuda",     callback_data="help")],
    ])
    await update.message.reply_text("📋 *Menú principal*\nElige una opción:", reply_markup=kb, parse_mode="MarkdownV2")

async def menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; await q.answer()
    uid = q.from_user.id
    if q.data == "profile":
        with db() as c: row = c.execute("SELECT * FROM users WHERE user_id=?", (uid,)).fetchone()
        if row:
            await q.edit_message_text(
                f"👤 *Tu perfil*\n\n🆔 ID: `{uid}`\n📎 @{row['username']}\n📅 Registrado: {row['registered'][:10]}",
                parse_mode="MarkdownV2")
    elif q.data == "help":
        await q.edit_message_text("ℹ️ *Ayuda*\n\n/start — Iniciar\n/menu — Menú\n\nContacta al administrador para obtener una key\.", parse_mode="MarkdownV2")

# ══════════════════════════════════════════════════════════════════════════════
# HANDLERS — ADMIN
# ══════════════════════════════════════════════════════════════════════════════
@admin_only
async def genkey(update: Update, context: ContextTypes.DEFAULT_TYPE):
    cantidad = 1
    if context.args:
        try: cantidad = min(int(context.args[0]), 20)
        except: await update.message.reply_text("❌ Uso: /genkey o /genkey 5"); return
    keys = [create_key(update.effective_user.id) for _ in range(cantidad)]
    texto = "\n".join(f"`{k}`" for k in keys)
    await update.message.reply_text(
        f"🔑 *{cantidad} key{'s' if cantidad>1 else ''} generada{'s' if cantidad>1 else ''}:*\n\n{texto}\n\n_Cada key es de un solo uso\._",
        parse_mode="MarkdownV2")

@admin_only
async def listkeys(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keys = get_all_keys()
    if not keys: await update.message.reply_text("📭 No hay keys\."); return
    disp  = [k for k in keys if k["used_by"] is None]
    usadas = [k for k in keys if k["used_by"] is not None]
    texto  = f"🔑 *Keys — Total: {len(keys)}*\n\n✅ Disponibles: {len(disp)}\n✔️ Usadas: {len(usadas)}\n\n"
    if disp:
        texto += "*Keys disponibles:*\n"
        for k in disp[:10]: texto += f"• `{k['key']}`\n"
        if len(disp) > 10: texto += f"_\.\.\.y {len(disp)-10} más_"
    await update.message.reply_text(texto, parse_mode="MarkdownV2")

@admin_only
async def listusers(update: Update, context: ContextTypes.DEFAULT_TYPE):
    users = get_all_users()
    if not users: await update.message.reply_text("📭 Sin usuarios\."); return
    texto = f"👥 *Usuarios: {len(users)}*\n\n"
    for u in users[:15]:
        estado = "🚫" if u["banned"] else "✅"
        texto += f"{estado} `{u['user_id']}` — @{u['username']} — {u['registered'][:10]}\n"
    if len(users) > 15: texto += f"\n_\.\.\.y {len(users)-15} más_"
    await update.message.reply_text(texto, parse_mode="MarkdownV2")

@admin_only
async def ban_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args: await update.message.reply_text("❌ Uso: /ban ID"); return
    try: target = int(context.args[0])
    except: await update.message.reply_text("❌ El ID debe ser un número\."); return
    if target in ADMIN_IDS: await update.message.reply_text("⛔ No puedes banear a un admin\."); return
    ban_user(target)
    await update.message.reply_text(f"🚫 Usuario `{target}` baneado\.", parse_mode="MarkdownV2")
    try: await context.bot.send_message(target, "🚫 Has sido baneado de este bot\.", parse_mode="MarkdownV2")
    except: pass

@admin_only
async def unban_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args: await update.message.reply_text("❌ Uso: /unban ID"); return
    try: target = int(context.args[0])
    except: await update.message.reply_text("❌ El ID debe ser un número\."); return
    unban_user(target)
    await update.message.reply_text(f"✅ Usuario `{target}` desbaneado\.", parse_mode="MarkdownV2")
    try: await context.bot.send_message(target, "✅ Tu acceso fue restaurado\.", parse_mode="MarkdownV2")
    except: pass

@admin_only
async def revokekey_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args: await update.message.reply_text("❌ Uso: /revokekey LA\_KEY", parse_mode="MarkdownV2"); return
    key = context.args[0].strip()
    delete_key(key)
    await update.message.reply_text(f"🗑️ Key `{key}` eliminada\.", parse_mode="MarkdownV2")

@admin_only
async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    users = get_all_users(); keys = get_all_keys()
    total = len(users); banned = sum(1 for u in users if u["banned"])
    tkeys = len(keys); disp = sum(1 for k in keys if k["used_by"] is None)
    await update.message.reply_text(
        f"📊 *Estadísticas*\n\n"
        f"👥 Usuarios totales: `{total}`\n✅ Activos: `{total-banned}`\n🚫 Baneados: `{banned}`\n\n"
        f"🔑 Keys totales: `{tkeys}`\n🟢 Disponibles: `{disp}`\n🔴 Usadas: `{tkeys-disp}`",
        parse_mode="MarkdownV2")

# ══════════════════════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════════════════════
def main():
    init_db()
    app = Application.builder().token(BOT_TOKEN).build()

    conv = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={WAITING_KEY: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_key)]},
        fallbacks=[CommandHandler("cancel", cancel)],
    )
    app.add_handler(conv)
    app.add_handler(CommandHandler("menu",       menu))
    app.add_handler(CallbackQueryHandler(menu_callback))
    app.add_handler(CommandHandler("genkey",     genkey))
    app.add_handler(CommandHandler("listkeys",   listkeys))
    app.add_handler(CommandHandler("listusers",  listusers))
    app.add_handler(CommandHandler("ban",        ban_cmd))
    app.add_handler(CommandHandler("unban",      unban_cmd))
    app.add_handler(CommandHandler("revokekey",  revokekey_cmd))
    app.add_handler(CommandHandler("stats",      stats))

    logger.info("✅ Bot iniciado")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
