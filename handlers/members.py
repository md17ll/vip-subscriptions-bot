from datetime import datetime, timedelta
from telegram import (
    Update, InlineKeyboardMarkup, InlineKeyboardButton
)
from telegram.ext import ContextTypes

from database import db
from handlers.common import require_owner_active


# ========= Helpers =========

def _channels_of_owner(owner_id: int):
    return db.fetch(
        "SELECT id, chat_id, title, invite_minutes FROM channels WHERE owner_id=%s ORDER BY id DESC",
        (owner_id,)
    )

def _channel_by_id(owner_id: int, channel_id: int):
    return db.fetch_one(
        "SELECT id, chat_id, title, invite_minutes, notify_enabled, auto_remove_enabled, welcome_message "
        "FROM channels WHERE owner_id=%s AND id=%s",
        (owner_id, channel_id)
    )

def _sub_by_user(channel_id: int, user_id: int):
    return db.fetch_one(
        "SELECT * FROM subscribers WHERE channel_id=%s AND user_id=%s",
        (channel_id, user_id)
    )

def _set_selected(context: ContextTypes.DEFAULT_TYPE, channel_id: int, user_id: int):
    context.user_data["selected_channel_id"] = int(channel_id)
    context.user_data["selected_user_id"] = int(user_id)

def _get_selected(context: ContextTypes.DEFAULT_TYPE):
    ch = context.user_data.get("selected_channel_id")
    uid = context.user_data.get("selected_user_id")
    return ch, uid

def _parse_user_id_from_update(update: Update):
    msg = update.message
    if msg.forward_from and msg.forward_from.id:
        return int(msg.forward_from.id)
    text = (msg.text or "").strip()
    if text.isdigit():
        return int(text)
    return None

def _kb_channels_pick(channels, prefix_cb: str, back_cb: str):
    rows = []
    for c in channels:
        title = c["title"] or str(c["chat_id"])
        rows.append([InlineKeyboardButton(f"📌 {title}", callback_data=f"{prefix_cb}:{c['id']}")])
    rows.append([InlineKeyboardButton("🔙 رجوع", callback_data=back_cb)])
    return InlineKeyboardMarkup(rows)

def _kb_duration(back_cb: str):
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("7 أيام", callback_data="add_dur:7"),
            InlineKeyboardButton("30 يوم", callback_data="add_dur:30"),
        ],
        [InlineKeyboardButton("90 يوم", callback_data="add_dur:90")],
        [InlineKeyboardButton("مدة مخصصة ✍️", callback_data="add_dur:custom")],
        [InlineKeyboardButton("🔙 رجوع", callback_data=back_cb)],
    ])

def _kb_confirm(back_cb: str):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ تأكيد", callback_data="add_confirm")],
        [InlineKeyboardButton("❌ إلغاء", callback_data=back_cb)],
    ])

def _kb_member_actions(back_cb: str = "members_menu"):
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🔄 تمديد 7 أيام", callback_data="extend_7"),
            InlineKeyboardButton("🔄 تمديد 30 يوم", callback_data="extend_30"),
        ],
        [InlineKeyboardButton("♻️ إعادة تفعيل 30 يوم", callback_data="reactivate")],
        [InlineKeyboardButton("🔗 رابط دخول", callback_data="invite_link")],
        [InlineKeyboardButton("🚫 حذف/إزالة", callback_data="remove_member")],
        [InlineKeyboardButton("🔙 رجوع", callback_data=back_cb)],
    ])


# ========= Menus =========

async def members_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()

    allowed, msg = require_owner_active(q.from_user.id)
    if not allowed:
        await q.message.reply_text(msg)
        return

    from ui import members_menu as kb
    await q.message.reply_text("👤 إدارة المشتركين", reply_markup=kb)


# ========= Add Member =========

async def add_member_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()

    owner_id = q.from_user.id
    allowed, msg = require_owner_active(owner_id)
    if not allowed:
        await q.message.reply_text(msg)
        return

    channels = _channels_of_owner(owner_id)
    if not channels:
        await q.message.reply_text("⚠️ لم تربط أي قناة بعد. اربط قناة أولاً من (🔗 ربط قناة).")
        return

    context.user_data.clear()
    context.user_data["flow"] = "add_member"

    if len(channels) == 1:
        context.user_data["channel_id"] = int(channels[0]["id"])
        context.user_data["step"] = "wait_user"
        await q.message.reply_text("👤 أرسل ID المشترك أو Forward رسالة منه:")
        return

    await q.message.reply_text(
        "📌 اختر القناة لإضافة مشترك:",
        reply_markup=_kb_channels_pick(channels, "pick_ch_add", "members_menu")
    )

async def pick_channel_for_add(update: Update, context: ContextTypes.DEFAULT_TYPE, channel_id: int):
    q = update.callback_query
    await q.answer()
    context.user_data["flow"] = "add_member"
    context.user_data["channel_id"] = int(channel_id)
    context.user_data["step"] = "wait_user"
    await q.message.reply_text("👤 أرسل ID المشترك أو Forward رسالة منه:")

async def add_duration_pick(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()

    if context.user_data.get("flow") != "add_member":
        return

    data = q.data  # add_dur:7 / add_dur:custom
    _, val = data.split(":", 1)

    if val == "custom":
        context.user_data["step"] = "wait_custom_days"
        await q.message.reply_text("✍️ اكتب عدد الأيام الآن (مثال: 45):")
        return

    days = int(val)
    context.user_data["days"] = days
    context.user_data["step"] = "confirm"

    ch_id = context.user_data["channel_id"]
    user_id = context.user_data["user_id"]
    expires_at = datetime.utcnow() + timedelta(days=days)

    await q.message.reply_text(
        "✅ تأكيد إضافة مشترك\n\n"
        f"📌 Channel ID: {ch_id}\n"
        f"👤 User ID: {user_id}\n"
        f"⏳ المدة: {days} يوم\n"
        f"📅 ينتهي: {expires_at.strftime('%Y-%m-%d %H:%M')} UTC",
        reply_markup=_kb_confirm("members_menu")
    )

async def add_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()

    if context.user_data.get("flow") != "add_member":
        return

    owner_id = q.from_user.id
    allowed, msg = require_owner_active(owner_id)
    if not allowed:
        await q.message.reply_text(msg)
        return

    channel_id = int(context.user_data.get("channel_id"))
    user_id = int(context.user_data.get("user_id"))
    days = int(context.user_data.get("days"))

    ch = _channel_by_id(owner_id, channel_id)
    if not ch:
        context.user_data.clear()
        await q.message.reply_text("⚠️ القناة غير موجودة أو ليست لك.")
        return

    expires_at = datetime.utcnow() + timedelta(days=days)

    # upsert subscriber
    db.execute(
        """
        INSERT INTO subscribers(channel_id, user_id, status, expires_at, created_at, updated_at)
        VALUES (%s,%s,'active',%s, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
        ON CONFLICT(channel_id, user_id)
        DO UPDATE SET status='active', expires_at=EXCLUDED.expires_at, updated_at=CURRENT_TIMESTAMP
        """,
        (channel_id, user_id, expires_at)
    )

    db.execute(
        "INSERT INTO logs(owner_id, channel_id, user_id, action, details) VALUES(%s,%s,%s,%s,%s)",
        (owner_id, channel_id, user_id, "member_added", f"{days} days")
    )

    # create invite link with channel invite_minutes
    invite_minutes = int(ch["invite_minutes"] or 10)
    invite_url = None
    try:
        link = await context.bot.create_chat_invite_link(
            chat_id=int(ch["chat_id"]),
            expire_date=datetime.utcnow() + timedelta(minutes=invite_minutes),
            member_limit=1
        )
        invite_url = link.invite_link
    except Exception as e:
        db.execute(
            "INSERT INTO logs(owner_id, channel_id, user_id, action, details) VALUES(%s,%s,%s,%s,%s)",
            (owner_id, channel_id, user_id, "invite_failed", str(e))
        )

    # set selection for quick actions
    _set_selected(context, channel_id, user_id)

    context.user_data.clear()

    if invite_url:
        await q.message.reply_text(
            "✅ تم حفظ الاشتراك وإنشاء رابط دخول.\n\n"
            f"⏳ صلاحية الرابط: {invite_minutes} دقيقة\n"
            "🔒 استخدام: مرة واحدة\n\n"
            f"🔗 {invite_url}",
            reply_markup=_kb_member_actions()
        )
    else:
        await q.message.reply_text(
            "✅ تم حفظ الاشتراك.\n⚠️ فشل إنشاء الرابط (تأكد صلاحيات Invite للبوت).",
            reply_markup=_kb_member_actions()
        )


# ========= Search / Remove =========

async def search_member_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()

    owner_id = q.from_user.id
    allowed, msg = require_owner_active(owner_id)
    if not allowed:
        await q.message.reply_text(msg)
        return

    channels = _channels_of_owner(owner_id)
    if not channels:
        await q.message.reply_text("⚠️ اربط قناة أولاً.")
        return

    context.user_data.clear()
    context.user_data["flow"] = "search_member"

    if len(channels) == 1:
        context.user_data["channel_id"] = int(channels[0]["id"])
        context.user_data["step"] = "wait_user"
        await q.message.reply_text("🔍 أرسل ID المشترك أو Forward رسالة منه للبحث:")
        return

    await q.message.reply_text(
        "📌 اختر القناة للبحث:",
        reply_markup=_kb_channels_pick(channels, "pick_ch_search", "members_menu")
    )

async def pick_channel_for_search(update: Update, context: ContextTypes.DEFAULT_TYPE, channel_id: int):
    q = update.callback_query
    await q.answer()
    context.user_data["flow"] = "search_member"
    context.user_data["channel_id"] = int(channel_id)
    context.user_data["step"] = "wait_user"
    await q.message.reply_text("🔍 أرسل ID المشترك أو Forward رسالة منه للبحث:")

async def remove_member_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()

    owner_id = q.from_user.id
    allowed, msg = require_owner_active(owner_id)
    if not allowed:
        await q.message.reply_text(msg)
        return

    channels = _channels_of_owner(owner_id)
    if not channels:
        await q.message.reply_text("⚠️ اربط قناة أولاً.")
        return

    context.user_data.clear()
    context.user_data["flow"] = "remove_member"

    if len(channels) == 1:
        context.user_data["channel_id"] = int(channels[0]["id"])
        context.user_data["step"] = "wait_user"
        await q.message.reply_text("🚫 أرسل ID المشترك أو Forward رسالة منه للحذف:")
        return

    await q.message.reply_text(
        "📌 اختر القناة للحذف:",
        reply_markup=_kb_channels_pick(channels, "pick_ch_remove", "members_menu")
    )

async def pick_channel_for_remove(update: Update, context: ContextTypes.DEFAULT_TYPE, channel_id: int):
    q = update.callback_query
    await q.answer()
    context.user_data["flow"] = "remove_member"
    context.user_data["channel_id"] = int(channel_id)
    context.user_data["step"] = "wait_user"
    await q.message.reply_text("🚫 أرسل ID المشترك أو Forward رسالة منه للحذف:")


# ========= Text Receiver for flows =========

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    flow = context.user_data.get("flow")
    step = context.user_data.get("step")

    if flow not in ("add_member", "search_member", "remove_member"):
        return

    if step == "wait_user":
        uid = _parse_user_id_from_update(update)
        if not uid:
            await update.message.reply_text("⚠️ أرسل ID صحيح أو Forward رسالة من المشترك.")
            return

        context.user_data["user_id"] = uid

        if flow == "add_member":
            context.user_data["step"] = "pick_duration"
            await update.message.reply_text("⏳ اختر مدة الاشتراك:", reply_markup=_kb_duration("members_menu"))
            return

        # search or remove: show file or execute remove
        channel_id = int(context.user_data["channel_id"])
        sub = _sub_by_user(channel_id, uid)

        if not sub:
            await update.message.reply_text("❌ هذا المستخدم غير موجود ضمن هذه القناة.")
            context.user_data.clear()
            return

        if flow == "search_member":
            _set_selected(context, channel_id, uid)
            context.user_data.clear()
            await update.message.reply_text(
                "👤 ملف المشترك\n\n"
                f"🆔 {uid}\n"
                f"📅 ينتهي: {sub['expires_at']}\n"
                f"📊 الحالة: {sub['status']}",
                reply_markup=_kb_member_actions()
            )
            return

        if flow == "remove_member":
            # store selection and run remove via existing callback flow
            _set_selected(context, channel_id, uid)
            context.user_data.clear()
            await update.message.reply_text(
                "✅ تم تحديد المشترك. اضغط زر (🚫 حذف/إزالة) للتأكيد.",
                reply_markup=_kb_member_actions()
            )
            return

    if flow == "add_member" and step == "wait_custom_days":
        text = (update.message.text or "").strip()
        if not text.isdigit():
            await update.message.reply_text("⚠️ اكتب رقم أيام صحيح فقط (مثال: 45).")
            return
        days = int(text)
        if days <= 0 or days > 3650:
            await update.message.reply_text("⚠️ اكتب مدة بين 1 و 3650 يوم.")
            return

        context.user_data["days"] = days
        context.user_data["step"] = "confirm"

        ch_id = context.user_data["channel_id"]
        user_id = context.user_data["user_id"]
        expires_at = datetime.utcnow() + timedelta(days=days)

        await update.message.reply_text(
            "✅ تأكيد إضافة مشترك\n\n"
            f"📌 Channel ID: {ch_id}\n"
            f"👤 User ID: {user_id}\n"
            f"⏳ المدة: {days} يوم\n"
            f"📅 ينتهي: {expires_at.strftime('%Y-%m-%d %H:%M')} UTC",
            reply_markup=_kb_confirm("members_menu")
        )


# ========= Selected member actions =========

async def extend_selected(update: Update, context: ContextTypes.DEFAULT_TYPE, days: int):
    q = update.callback_query
    await q.answer()

    owner_id = q.from_user.id
    allowed, msg = require_owner_active(owner_id)
    if not allowed:
        await q.message.reply_text(msg)
        return

    channel_id, user_id = _get_selected(context)
    if not channel_id or not user_id:
        await q.message.reply_text("⚠️ ابحث عن المشترك أولاً.")
        return

    sub = _sub_by_user(channel_id, user_id)
    if not sub:
        await q.message.reply_text("❌ المشترك غير موجود.")
        return

    base = sub["expires_at"]
    # base قد تكون datetime من psycopg2
    if base < datetime.utcnow():
        base = datetime.utcnow()

    new_exp = base + timedelta(days=days)

    db.execute(
        "UPDATE subscribers SET expires_at=%s, status='active', updated_at=CURRENT_TIMESTAMP WHERE channel_id=%s AND user_id=%s",
        (new_exp, channel_id, user_id)
    )
    db.execute(
        "INSERT INTO logs(owner_id, channel_id, user_id, action, details) VALUES(%s,%s,%s,%s,%s)",
        (owner_id, channel_id, user_id, "extended", f"{days} days")
    )

    await q.message.reply_text(f"✅ تم التمديد. الانتهاء الجديد: {new_exp}", reply_markup=_kb_member_actions())

async def reactivate_selected(update: Update, context: ContextTypes.DEFAULT_TYPE, days: int = 30):
    q = update.callback_query
    await q.answer()

    owner_id = q.from_user.id
    allowed, msg = require_owner_active(owner_id)
    if not allowed:
        await q.message.reply_text(msg)
        return

    channel_id, user_id = _get_selected(context)
    if not channel_id or not user_id:
        await q.message.reply_text("⚠️ ابحث عن المشترك أولاً.")
        return

    new_exp = datetime.utcnow() + timedelta(days=days)

    db.execute(
        "UPDATE subscribers SET expires_at=%s, status='active', updated_at=CURRENT_TIMESTAMP WHERE channel_id=%s AND user_id=%s",
        (new_exp, channel_id, user_id)
    )
    db.execute(
        "INSERT INTO logs(owner_id, channel_id, user_id, action, details) VALUES(%s,%s,%s,%s,%s)",
        (owner_id, channel_id, user_id, "reactivated", f"{days} days")
    )

    await q.message.reply_text(f"♻️ تم إعادة التفعيل. الانتهاء: {new_exp}", reply_markup=_kb_member_actions())

async def invite_link_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()

    owner_id = q.from_user.id
    allowed, msg = require_owner_active(owner_id)
    if not allowed:
        await q.message.reply_text(msg)
        return

    channel_id, user_id = _get_selected(context)
    if not channel_id or not user_id:
        await q.message.reply_text("⚠️ ابحث عن المشترك أولاً.")
        return

    ch = _channel_by_id(owner_id, channel_id)
    if not ch:
        await q.message.reply_text("⚠️ القناة غير موجودة.")
        return

    invite_minutes = int(ch["invite_minutes"] or 10)

    try:
        link = await context.bot.create_chat_invite_link(
            chat_id=int(ch["chat_id"]),
            expire_date=datetime.utcnow() + timedelta(minutes=invite_minutes),
            member_limit=1
        )
        db.execute(
            "INSERT INTO logs(owner_id, channel_id, user_id, action, details) VALUES(%s,%s,%s,%s,%s)",
            (owner_id, channel_id, user_id, "invite_created", f"{invite_minutes} minutes")
        )
        await q.message.reply_text(
            f"🔗 رابط دخول مؤقت ({invite_minutes} دقيقة / مرة واحدة):\n\n{link.invite_link}",
            reply_markup=_kb_member_actions()
        )
    except Exception as e:
        db.execute(
            "INSERT INTO logs(owner_id, channel_id, user_id, action, details) VALUES(%s,%s,%s,%s,%s)",
            (owner_id, channel_id, user_id, "invite_failed", str(e))
        )
        await q.message.reply_text("⚠️ فشل إنشاء الرابط. تأكد صلاحية Invite للبوت.", reply_markup=_kb_member_actions())

async def remove_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()

    owner_id = q.from_user.id
    allowed, msg = require_owner_active(owner_id)
    if not allowed:
        await q.message.reply_text(msg)
        return

    channel_id, user_id = _get_selected(context)
    if not channel_id or not user_id:
        await q.message.reply_text("⚠️ ابحث عن المشترك أولاً.")
        return

    # get chat_id
    ch = _channel_by_id(owner_id, channel_id)
    if not ch:
        await q.message.reply_text("⚠️ القناة غير موجودة.")
        return

    # remove from channel
    try:
        await context.bot.ban_chat_member(int(ch["chat_id"]), int(user_id))
        await context.bot.unban_chat_member(int(ch["chat_id"]), int(user_id))
    except Exception as e:
        db.execute(
            "INSERT INTO logs(owner_id, channel_id, user_id, action, details) VALUES(%s,%s,%s,%s,%s)",
            (owner_id, channel_id, user_id, "remove_failed", str(e))
        )

    db.execute(
        "UPDATE subscribers SET status='removed', updated_at=CURRENT_TIMESTAMP WHERE channel_id=%s AND user_id=%s",
        (channel_id, user_id)
    )
    db.execute(
        "INSERT INTO logs(owner_id, channel_id, user_id, action, details) VALUES(%s,%s,%s,%s,%s)",
        (owner_id, channel_id, user_id, "removed", "")
    )

    await q.message.reply_text("🚫 تم إزالة المشترك وتحديث حالته.", reply_markup=_kb_member_actions())
