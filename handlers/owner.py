from telegram import Update
from telegram.ext import ContextTypes
from database import db
from handlers.common import require_owner_active


async def link_channel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id
    allowed, msg = require_owner_active(user_id)
    if not allowed:
        await query.edit_message_text(msg)
        return

    context.user_data["link_channel"] = True

    await query.edit_message_text(
        "🔗 ربط قناة / مجموعة\n\n"
        "✅ الخطوات:\n"
        "1) أضف البوت كـ Admin داخل القناة/المجموعة\n"
        "2) اكتب أي رسالة داخل القناة (مثلاً: test)\n"
        "3) اعمل **Forward** لهذه الرسالة للبوت هنا بالخاص\n\n"
        "📌 ملاحظة: لازم يكون الـ Forward ظاهر (مو مخفي) حتى يقرأ البوت معلومات القناة."
    )


async def receive_channel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.user_data.get("link_channel"):
        return

    user_id = update.effective_user.id

    # لازم تكون رسالة Forward من قناة/مجموعة
    fchat = update.message.forward_from_chat
    if not fchat:
        await update.message.reply_text(
            "⚠️ لازم تعمل Forward لرسالة من القناة/المجموعة.\n"
            "ارجع واعمل Forward لرسالة من القناة بعد إضافة البوت Admin."
        )
        return

    chat_id = int(fchat.id)
    title = fchat.title or ""

    # حفظ القناة (مع دعم الهيكل الجديد لقاعدة البيانات)
    db.execute(
        """
        INSERT INTO channels(owner_id, chat_id, title)
        VALUES(%s, %s, %s)
        ON CONFLICT(owner_id, chat_id) DO UPDATE SET
            title = EXCLUDED.title,
            updated_at = CURRENT_TIMESTAMP
        """,
        (user_id, chat_id, title)
    )

    db.execute(
        "INSERT INTO logs(owner_id, action, details) VALUES(%s,%s,%s)",
        (user_id, "channel_linked", f"{chat_id}")
    )

    context.user_data.clear()

    await update.message.reply_text(
        "✅ تم ربط القناة بنجاح!\n\n"
        f"📌 الاسم: {title or 'بدون اسم'}\n"
        f"🆔 chat_id: `{chat_id}`",
        parse_mode="Markdown"
    )
