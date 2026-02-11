from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes

from database import db
from handlers.common import require_owner_active
from ui import channel_settings_menu, invite_duration_menu


def _channels_of_owner(owner_id: int):
    return db.fetch(
        "SELECT id, chat_id, title, invite_minutes, notify_enabled, auto_remove_enabled, welcome_message "
        "FROM channels WHERE owner_id=%s ORDER BY id DESC",
        (owner_id,)
    )

def _channel_by_id(owner_id: int, channel_id: int):
    return db.fetch_one(
        "SELECT id, chat_id, title, invite_minutes, notify_enabled, auto_remove_enabled, welcome_message "
        "FROM channels WHERE owner_id=%s AND id=%s",
        (owner_id, channel_id)
    )

def _kb_pick_channel(channels, prefix_cb: str, back_cb: str):
    rows = []
    for c in channels:
        title = c["title"] or str(c["chat_id"])
        rows.append([InlineKeyboardButton(f"📌 {title}", callback_data=f"{prefix_cb}:{c['id']}")])
    rows.append([InlineKeyboardButton("🔙 رجوع", callback_data=back_cb)])
    return InlineKeyboardMarkup(rows)

def _set_selected_channel(context: ContextTypes.DEFAULT_TYPE, channel_id: int):
    context.user_data["settings_channel_id"] = int(channel_id)

def _get_selected_channel(context: ContextTypes.DEFAULT_TYPE):
    return context.user_data.get("settings_channel_id")

def _fmt_settings(ch):
    title = ch["title"] or str(ch["chat_id"])
    inv = int(ch["invite_minutes"] or 10)
    notify = "✅" if ch["notify_enabled"] else "❌"
    auto_rm = "✅" if ch["auto_remove_enabled"] else "❌"
    has_welcome = "✅" if (ch["welcome_message"] or "").strip() else "❌"
    return (
        "⚙️ إعدادات القناة\n\n"
        f"📌 القناة: {title}\n"
        f"⏱️ مدة الرابط: {inv} دقيقة\n"
        f"🔔 التنبيهات: {notify}\n"
        f"🧹 الحذف التلقائي: {auto_rm}\n"
        f"📩 رسالة الدخول: {has_welcome}\n"
    )


# =========================
# Open Settings
# =========================

async def open_settings(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()

    owner_id = q.from_user.id
    allowed, msg = require_owner_active(owner_id)
    if not allowed:
        await q.edit_message_text(msg)
        return

    channels = _channels_of_owner(owner_id)
    if not channels:
        await q.edit_message_text("⚠️ اربط قناة أولاً من زر (🔗 ربط قناة).")
        return

    # إن كان عنده قناة واحدة نختارها مباشرة
    if len(channels) == 1:
        _set_selected_channel(context, int(channels[0]["id"]))
        ch = channels[0]
        await q.edit_message_text(_fmt_settings(ch), reply_markup=channel_settings_menu)
        return

    context.user_data["flow"] = "settings_pick_channel"
    await q.edit_message_text(
        "📌 اختر القناة لفتح الإعدادات:",
        reply_markup=_kb_pick_channel(channels, "settings_ch", "back_main")
    )


async def pick_settings_channel(update: Update, context: ContextTypes.DEFAULT_TYPE, channel_id: int):
    q = update.callback_query
    await q.answer()

    owner_id = q.from_user.id
    allowed, msg = require_owner_active(owner_id)
    if not allowed:
        await q.edit_message_text(msg)
        return

    _set_selected_channel(context, int(channel_id))
    ch = _channel_by_id(owner_id, int(channel_id))
    if not ch:
        await q.edit_message_text("⚠️ القناة غير موجودة.")
        return

    await q.edit_message_text(_fmt_settings(ch), reply_markup=channel_settings_menu)


# =========================
# Toggle Notify / AutoRemove
# =========================

async def toggle_notify(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()

    owner_id = q.from_user.id
    allowed, msg = require_owner_active(owner_id)
    if not allowed:
        await q.edit_message_text(msg)
        return

    channel_id = _get_selected_channel(context)
    if not channel_id:
        await q.edit_message_text("⚠️ اختر القناة أولاً من (⚙️ إعدادات القناة).")
        return

    ch = _channel_by_id(owner_id, int(channel_id))
    if not ch:
        await q.edit_message_text("⚠️ القناة غير موجودة.")
        return

    new_val = not bool(ch["notify_enabled"])
    db.execute(
        "UPDATE channels SET notify_enabled=%s, updated_at=CURRENT_TIMESTAMP WHERE owner_id=%s AND id=%s",
        (new_val, owner_id, int(channel_id))
    )
    db.execute(
        "INSERT INTO logs(owner_id, channel_id, action, details) VALUES(%s,%s,%s,%s)",
        (owner_id, int(channel_id), "toggle_notify", str(new_val))
    )

    ch2 = _channel_by_id(owner_id, int(channel_id))
    await q.edit_message_text(_fmt_settings(ch2), reply_markup=channel_settings_menu)


async def toggle_autoremove(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()

    owner_id = q.from_user.id
    allowed, msg = require_owner_active(owner_id)
    if not allowed:
        await q.edit_message_text(msg)
        return

    channel_id = _get_selected_channel(context)
    if not channel_id:
        await q.edit_message_text("⚠️ اختر القناة أولاً من (⚙️ إعدادات القناة).")
        return

    ch = _channel_by_id(owner_id, int(channel_id))
    if not ch:
        await q.edit_message_text("⚠️ القناة غير موجودة.")
        return

    new_val = not bool(ch["auto_remove_enabled"])
    db.execute(
        "UPDATE channels SET auto_remove_enabled=%s, updated_at=CURRENT_TIMESTAMP WHERE owner_id=%s AND id=%s",
        (new_val, owner_id, int(channel_id))
    )
    db.execute(
        "INSERT INTO logs(owner_id, channel_id, action, details) VALUES(%s,%s,%s,%s)",
        (owner_id, int(channel_id), "toggle_autoremove", str(new_val))
    )

    ch2 = _channel_by_id(owner_id, int(channel_id))
    await q.edit_message_text(_fmt_settings(ch2), reply_markup=channel_settings_menu)


# =========================
# Invite duration (5/10/30/60)
# =========================

async def open_invite_duration(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()

    owner_id = q.from_user.id
    allowed, msg = require_owner_active(owner_id)
    if not allowed:
        await q.edit_message_text(msg)
        return

    channel_id = _get_selected_channel(context)
    if not channel_id:
        await q.edit_message_text("⚠️ اختر القناة أولاً من (⚙️ إعدادات القناة).")
        return

    await q.edit_message_text(
        "⏱️ اختر مدة صلاحية رابط الدعوة:",
        reply_markup=invite_duration_menu
    )

async def set_invite_minutes(update: Update, context: ContextTypes.DEFAULT_TYPE, minutes: int):
    q = update.callback_query
    await q.answer()

    owner_id = q.from_user.id
    allowed, msg = require_owner_active(owner_id)
    if not allowed:
        await q.edit_message_text(msg)
        return

    channel_id = _get_selected_channel(context)
    if not channel_id:
        await q.edit_message_text("⚠️ اختر القناة أولاً من (⚙️ إعدادات القناة).")
        return

    if minutes not in (5, 10, 30, 60):
        await q.edit_message_text("⚠️ قيمة غير صحيحة.")
        return

    db.execute(
        "UPDATE channels SET invite_minutes=%s, updated_at=CURRENT_TIMESTAMP WHERE owner_id=%s AND id=%s",
        (minutes, owner_id, int(channel_id))
    )
    db.execute(
        "INSERT INTO logs(owner_id, channel_id, action, details) VALUES(%s,%s,%s,%s)",
        (owner_id, int(channel_id), "set_invite_minutes", str(minutes))
    )

    ch2 = _channel_by_id(owner_id, int(channel_id))
    await q.edit_message_text(
        f"✅ تم تحديث مدة الرابط إلى {minutes} دقيقة.\n\n" + _fmt_settings(ch2),
        reply_markup=channel_settings_menu
    )


# =========================
# Welcome message
# =========================

def _kb_welcome():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✍️ تعيين رسالة جديدة", callback_data="set_welcome_msg")],
        [InlineKeyboardButton("🗑️ حذف الرسالة", callback_data="clear_welcome_msg")],
        [InlineKeyboardButton("🔙 رجوع", callback_data="channel_settings")]
    ])

async def open_welcome_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()

    owner_id = q.from_user.id
    allowed, msg = require_owner_active(owner_id)
    if not allowed:
        await q.edit_message_text(msg)
        return

    channel_id = _get_selected_channel(context)
    if not channel_id:
        await q.edit_message_text("⚠️ اختر القناة أولاً.")
        return

    ch = _channel_by_id(owner_id, int(channel_id))
    if not ch:
        await q.edit_message_text("⚠️ القناة غير موجودة.")
        return

    current = (ch["welcome_message"] or "").strip()
    if current:
        txt = "📩 رسالة الدخول الحالية:\n\n" + current
    else:
        txt = "📩 لا توجد رسالة دخول حالياً."

    await q.edit_message_text(txt, reply_markup=_kb_welcome())

async def set_welcome_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()

    owner_id = q.from_user.id
    allowed, msg = require_owner_active(owner_id)
    if not allowed:
        await q.edit_message_text(msg)
        return

    channel_id = _get_selected_channel(context)
    if not channel_id:
        await q.edit_message_text("⚠️ اختر القناة أولاً.")
        return

    context.user_data["flow"] = "set_welcome"
    await q.edit_message_text("✍️ أرسل الآن رسالة الدخول الجديدة:")

async def receive_welcome_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.user_data.get("flow") != "set_welcome":
        return

    owner_id = update.effective_user.id
    allowed, msg = require_owner_active(owner_id)
    if not allowed:
        await update.message.reply_text(msg)
        context.user_data.clear()
        return

    channel_id = _get_selected_channel(context)
    if not channel_id:
        await update.message.reply_text("⚠️ اختر القناة أولاً.")
        context.user_data.clear()
        return

    text = (update.message.text or "").strip()
    if len(text) < 2:
        await update.message.reply_text("⚠️ اكتب رسالة أطول.")
        return

    db.execute(
        "UPDATE channels SET welcome_message=%s, updated_at=CURRENT_TIMESTAMP WHERE owner_id=%s AND id=%s",
        (text, owner_id, int(channel_id))
    )
    db.execute(
        "INSERT INTO logs(owner_id, channel_id, action, details) VALUES(%s,%s,%s,%s)",
        (owner_id, int(channel_id), "set_welcome_message", f"len={len(text)}")
    )

    context.user_data.clear()
    await update.message.reply_text("✅ تم حفظ رسالة الدخول بنجاح.")

async def clear_welcome_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()

    owner_id = q.from_user.id
    allowed, msg = require_owner_active(owner_id)
    if not allowed:
        await q.edit_message_text(msg)
        return

    channel_id = _get_selected_channel(context)
    if not channel_id:
        await q.edit_message_text("⚠️ اختر القناة أولاً.")
        return

    db.execute(
        "UPDATE channels SET welcome_message='', updated_at=CURRENT_TIMESTAMP WHERE owner_id=%s AND id=%s",
        (owner_id, int(channel_id))
    )
    db.execute(
        "INSERT INTO logs(owner_id, channel_id, action, details) VALUES(%s,%s,%s,%s)",
        (owner_id, int(channel_id), "clear_welcome_message", "")
    )

    await q.edit_message_text("🗑️ تم حذف رسالة الدخول.")
