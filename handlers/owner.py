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
        await query.message.reply_text(msg)
        return

    context.user_data["link_channel"] = True

    await query.message.reply_text(
        "أرسل chat_id للقناة بعد جعل البوت Admin"
    )


async def receive_channel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.user_data.get("link_channel"):
        return

    user_id = update.effective_user.id
    chat_id = update.message.text

    db.execute(
        "INSERT INTO channels(owner_id,chat_id) VALUES(%s,%s) ON CONFLICT DO NOTHING",
        (user_id, chat_id)
    )

    await update.message.reply_text("✅ تم ربط القناة بنجاح")

    context.user_data.clear()
