from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes

from database import db
from handlers.common import is_superadmin
from ui import admin_panel_menu, manage_owners_menu


def _kb_back_admin():
    return InlineKeyboardMarkup([[InlineKeyboardButton("🔙 رجوع", callback_data="admin_panel")]])


def _fmt_owner_row(o):
    exp = o["sub_expires_at"]
    exp_txt = exp.strftime("%Y-%m-%d %H:%M") + " UTC" if exp else "غير محدد"
    status = "✅ فعال" if o["active"] else "⛔ موقوف"
    return f"👤 Owner: `{o['owner_id']}`\n📅 انتهاء: {exp_txt}\n📌 الحالة: {status}\n📝 ملاحظة: {o['note'] or '-'}"


def _kb_owner_actions(owner_id: int):
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("♻️ تمديد +30 يوم", callback_data=f"owner_extend30:{owner_id}"),
            InlineKeyboardButton("♻️ تمديد +سنة", callback_data=f"owner_extend365:{owner_id}")
        ],
        [
            InlineKeyboardButton("✅ تفعيل", callback_data=f"owner_enable:{owner_id}"),
            InlineKeyboardButton("⛔ إيقاف", callback_data=f"owner_disable:{owner_id}")
        ],
        [InlineKeyboardButton("📝 تعديل ملاحظة", callback_data=f"owner_note:{owner_id}")],
        [InlineKeyboardButton("🔙 رجوع", callback_data="manage_owners")]
    ])


async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()

    if not is_superadmin(q.from_user.id):
        await q.message.reply_text("⛔ غير مسموح.")
        return

    await q.message.reply_text("🛠️ لوحة تحكم الأدمن", reply_markup=admin_panel_menu)


async def manage_owners(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()

    if not is_superadmin(q.from_user.id):
        await q.message.reply_text("⛔ غير مسموح.")
        return

    await q.message.reply_text("🏷️ إدارة أصحاب القنوات", reply_markup=manage_owners_menu)


# =========================
# ADD OWNER
# =========================

async def add_owner_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()

    if not is_superadmin(q.from_user.id):
        await q.message.reply_text("⛔ غير مسموح.")
        return

    context.user_data.clear()
    context.user_data["flow"] = "add_owner"
    context.user_data["step"] = "wait_owner_id"

    await q.message.reply_text("➕ أرسل الآن ID صاحب القناة (رقم فقط):", reply_markup=_kb_back_admin())


# =========================
# EXTEND / ENABLE / DISABLE / SEARCH
# =========================

async def extend_owner_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()

    if not is_superadmin(q.from_user.id):
        await q.message.reply_text("⛔ غير مسموح.")
        return

    context.user_data.clear()
    context.user_data["flow"] = "extend_owner"
    context.user_data["step"] = "wait_owner_id"

    await q.message.reply_text("♻️ أرسل ID الـ Owner لتمديد اشتراكه:", reply_markup=_kb_back_admin())


async def disable_owner_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()

    if not is_superadmin(q.from_user.id):
        await q.message.reply_text("⛔ غير مسموح.")
        return

    context.user_data.clear()
    context.user_data["flow"] = "disable_owner"
    context.user_data["step"] = "wait_owner_id"

    await q.message.reply_text("⛔ أرسل ID الـ Owner لإيقافه:", reply_markup=_kb_back_admin())


async def search_owner_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()

    if not is_superadmin(q.from_user.id):
        await q.message.reply_text("⛔ غير مسموح.")
        return

    context.user_data.clear()
    context.user_data["flow"] = "search_owner"
    context.user_data["step"] = "wait_owner_id"

    await q.message.reply_text("🔍 أرسل ID الـ Owner للبحث:", reply_markup=_kb_back_admin())


async def owners_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()

    if not is_superadmin(q.from_user.id):
        await q.message.reply_text("⛔ غير مسموح.")
        return

    rows = db.fetch("""
        SELECT owner_id, active, sub_expires_at, note
        FROM owners
        ORDER BY created_at DESC
        LIMIT 20
    """)

    if not rows:
        await q.message.reply_text("لا يوجد Owners حالياً.", reply_markup=_kb_back_admin())
        return

    txt = "📋 قائمة آخر 20 Owner:\n\n"
    for r in rows:
        exp = r["sub_expires_at"]
        exp_txt = exp.strftime("%Y-%m-%d") if exp else "غير محدد"
        status = "✅" if r["active"] else "⛔"
        txt += f"{status} `{r['owner_id']}` — {exp_txt}\n"

    await q.message.reply_text(txt, reply_markup=_kb_back_admin(), parse_mode="Markdown")


async def system_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()

    if not is_superadmin(q.from_user.id):
        await q.message.reply_text("⛔ غير مسموح.")
        return

    owners_total = db.fetch_one("SELECT COUNT(*) AS c FROM owners")["c"]
    owners_active = db.fetch_one("SELECT COUNT(*) AS c FROM owners WHERE active=TRUE")["c"]
    channels_total = db.fetch_one("SELECT COUNT(*) AS c FROM channels")["c"]
    subs_active = db.fetch_one("SELECT COUNT(*) AS c FROM subscribers WHERE status='active'")["c"]
    subs_expired = db.fetch_one("SELECT COUNT(*) AS c FROM subscribers WHERE status='expired'")["c"]

    txt = (
        "📊 إحصائيات النظام\n\n"
        f"👤 Owners: {owners_total} (✅ فعال: {owners_active})\n"
        f"📌 Channels: {channels_total}\n"
        f"🟢 Subscribers Active: {subs_active}\n"
        f"🔴 Subscribers Expired: {subs_expired}\n"
    )

    await q.message.reply_text(txt, reply_markup=_kb_back_admin())


# =========================
# BROADCAST
# =========================

async def broadcast_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()

    if not is_superadmin(q.from_user.id):
        await q.message.reply_text("⛔ غير مسموح.")
        return

    context.user_data.clear()
    context.user_data["flow"] = "broadcast"
    context.user_data["step"] = "wait_text"

    await q.message.reply_text(
        "📨 أرسل نص الرسالة الآن لإرسالها لكل الـ Owners (سيتم الإرسال للأشخاص المسجلين في owners):",
        reply_markup=_kb_back_admin()
    )


# =========================
# CALLBACK: OWNER ACTIONS
# =========================

async def owner_action_callback(update: Update, context: ContextTypes.DEFAULT_TYPE, action: str, owner_id: int):
    q = update.callback_query
    await q.answer()

    if not is_superadmin(q.from_user.id):
        await q.message.reply_text("⛔ غير مسموح.")
        return

    row = db.fetch_one("SELECT owner_id, active, sub_expires_at, note FROM owners WHERE owner_id=%s", (owner_id,))
    if not row:
        await q.message.reply_text("❌ Owner غير موجود.")
        return

    if action == "extend30":
        base = row["sub_expires_at"]
        if base is None or base < datetime.utcnow():
            base = datetime.utcnow()
        new_exp = base + timedelta(days=30)
        db.execute("UPDATE owners SET sub_expires_at=%s, active=TRUE, updated_at=CURRENT_TIMESTAMP WHERE owner_id=%s",
                   (new_exp, owner_id))
        db.execute("INSERT INTO logs(owner_id, action, details) VALUES(%s,%s,%s)",
                   (owner_id, "owner_extend", "30 days"))
    elif action == "extend365":
        base = row["sub_expires_at"]
        if base is None or base < datetime.utcnow():
            base = datetime.utcnow()
        new_exp = base + timedelta(days=365)
        db.execute("UPDATE owners SET sub_expires_at=%s, active=TRUE, updated_at=CURRENT_TIMESTAMP WHERE owner_id=%s",
                   (new_exp, owner_id))
        db.execute("INSERT INTO logs(owner_id, action, details) VALUES(%s,%s,%s)",
                   (owner_id, "owner_extend", "365 days"))
    elif action == "enable":
        db.execute("UPDATE owners SET active=TRUE, updated_at=CURRENT_TIMESTAMP WHERE owner_id=%s", (owner_id,))
        db.execute("INSERT INTO logs(owner_id, action, details) VALUES(%s,%s,%s)",
                   (owner_id, "owner_enabled", ""))
    elif action == "disable":
        db.execute("UPDATE owners SET active=FALSE, updated_at=CURRENT_TIMESTAMP WHERE owner_id=%s", (owner_id,))
        db.execute("INSERT INTO logs(owner_id, action, details) VALUES(%s,%s,%s)",
                   (owner_id, "owner_disabled", ""))
    elif action == "note":
        context.user_data.clear()
        context.user_data["flow"] = "owner_note"
        context.user_data["owner_id"] = owner_id
        await q.message.reply_text("📝 أرسل الملاحظة الجديدة الآن:")
        return

    row2 = db.fetch_one("SELECT owner_id, active, sub_expires_at, note FROM owners WHERE owner_id=%s", (owner_id,))
    await q.message.reply_text(_fmt_owner_row(row2), reply_markup=_kb_owner_actions(owner_id), parse_mode="Markdown")


# =========================
# TEXT RECEIVER (ADMIN FLOWS)
# =========================

async def admin_text_receiver(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if not is_superadmin(uid):
        return

    flow = context.user_data.get("flow")
    step = context.user_data.get("step")

    # --- Add owner ---
    if flow == "add_owner" and step == "wait_owner_id":
        text = (update.message.text or "").strip()
        if not text.isdigit():
            await update.message.reply_text("⚠️ أرسل رقم ID صحيح فقط.")
            return
        owner_id = int(text)

        db.execute("""
            INSERT INTO owners(owner_id, active, sub_expires_at, note)
            VALUES(%s, TRUE, NULL, '')
            ON CONFLICT(owner_id) DO NOTHING
        """, (owner_id,))
        db.execute("INSERT INTO logs(owner_id, action, details) VALUES(%s,%s,%s)",
                   (owner_id, "owner_added", ""))

        context.user_data.clear()
        row = db.fetch_one("SELECT owner_id, active, sub_expires_at, note FROM owners WHERE owner_id=%s", (owner_id,))
        await update.message.reply_text("✅ تم إضافة Owner.\n\n" + _fmt_owner_row(row),
                                        reply_markup=_kb_owner_actions(owner_id),
                                        parse_mode="Markdown")
        return

    # --- Extend owner flow: ask for ID then days ---
    if flow == "extend_owner" and step == "wait_owner_id":
        text = (update.message.text or "").strip()
        if not text.isdigit():
            await update.message.reply_text("⚠️ أرسل رقم ID صحيح.")
            return
        owner_id = int(text)
        exists = db.fetch_one("SELECT owner_id FROM owners WHERE owner_id=%s", (owner_id,))
        if not exists:
            await update.message.reply_text("❌ Owner غير موجود.")
            context.user_data.clear()
            return

        context.user_data["owner_id"] = owner_id
        context.user_data["step"] = "wait_days"
        await update.message.reply_text("✍️ اكتب عدد الأيام للتمديد (مثال 30):")
        return

    if flow == "extend_owner" and step == "wait_days":
        text = (update.message.text or "").strip()
        if not text.isdigit():
            await update.message.reply_text("⚠️ اكتب رقم أيام صحيح.")
            return
        days = int(text)
        if days <= 0 or days > 3650:
            await update.message.reply_text("⚠️ اكتب مدة بين 1 و 3650.")
            return

        owner_id = int(context.user_data["owner_id"])
        row = db.fetch_one("SELECT sub_expires_at FROM owners WHERE owner_id=%s", (owner_id,))
        base = row["sub_expires_at"]
        if base is None or base < datetime.utcnow():
            base = datetime.utcnow()
        new_exp = base + timedelta(days=days)

        db.execute("UPDATE owners SET sub_expires_at=%s, active=TRUE, updated_at=CURRENT_TIMESTAMP WHERE owner_id=%s",
                   (new_exp, owner_id))
        db.execute("INSERT INTO logs(owner_id, action, details) VALUES(%s,%s,%s)",
                   (owner_id, "owner_extend", f"{days} days"))

        context.user_data.clear()
        row2 = db.fetch_one("SELECT owner_id, active, sub_expires_at, note FROM owners WHERE owner_id=%s", (owner_id,))
        await update.message.reply_text("✅ تم التمديد.\n\n" + _fmt_owner_row(row2),
                                        reply_markup=_kb_owner_actions(owner_id),
                                        parse_mode="Markdown")
        return

    # --- Disable owner ---
    if flow == "disable_owner" and step == "wait_owner_id":
        text = (update.message.text or "").strip()
        if not text.isdigit():
            await update.message.reply_text("⚠️ أرسل رقم ID صحيح.")
            return
        owner_id = int(text)
        db.execute("UPDATE owners SET active=FALSE, updated_at=CURRENT_TIMESTAMP WHERE owner_id=%s", (owner_id,))
        db.execute("INSERT INTO logs(owner_id, action, details) VALUES(%s,%s,%s)",
                   (owner_id, "owner_disabled", "manual"))

        context.user_data.clear()
        await update.message.reply_text("⛔ تم إيقاف الـ Owner.")
        return

    # --- Search owner ---
    if flow == "search_owner" and step == "wait_owner_id":
        text = (update.message.text or "").strip()
        if not text.isdigit():
            await update.message.reply_text("⚠️ أرسل رقم ID صحيح.")
            return
        owner_id = int(text)
        row = db.fetch_one("SELECT owner_id, active, sub_expires_at, note FROM owners WHERE owner_id=%s", (owner_id,))
        context.user_data.clear()
        if not row:
            await update.message.reply_text("❌ Owner غير موجود.")
            return
        await update.message.reply_text(_fmt_owner_row(row), reply_markup=_kb_owner_actions(owner_id), parse_mode="Markdown")
        return

    # --- Broadcast ---
    if flow == "broadcast" and step == "wait_text":
        text = (update.message.text or "").strip()
        if len(text) < 2:
            await update.message.reply_text("⚠️ اكتب نص أطول.")
            return

        owners = db.fetch("SELECT owner_id FROM owners")
        sent = 0
        for o in owners:
            try:
                await context.bot.send_message(chat_id=int(o["owner_id"]), text=text)
                sent += 1
            except:
                pass

        db.execute("INSERT INTO logs(action, details) VALUES(%s,%s)", ("broadcast", f"sent={sent}"))
        context.user_data.clear()
        await update.message.reply_text(f"✅ تم الإرسال. عدد من استلم: {sent}")
        return

    # --- Owner note ---
    if flow == "owner_note":
        owner_id = int(context.user_data.get("owner_id", 0))
        note = (update.message.text or "").strip()
        db.execute("UPDATE owners SET note=%s, updated_at=CURRENT_TIMESTAMP WHERE owner_id=%s", (note, owner_id))
        db.execute("INSERT INTO logs(owner_id, action, details) VALUES(%s,%s,%s)",
                   (owner_id, "owner_note_updated", f"len={len(note)}"))
        context.user_data.clear()
        await update.message.reply_text("✅ تم تحديث الملاحظة.")
        return
