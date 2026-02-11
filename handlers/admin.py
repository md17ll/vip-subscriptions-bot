from telegram import Update
from telegram.ext import ContextTypes
from ui import admin_panel_menu
from database import db
from handlers.common import is_superadmin


async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if not is_superadmin(query.from_user.id):
        await query.message.reply_text("⛔ غير مسموح.")
        return

    await query.message.reply_text(
        "🛠️ لوحة تحكم الأدمن",
        reply_markup=admin_panel_menu
    )


async def add_owner(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    context.user_data["add_owner"] = True
    await query.message.reply_text("أرسل ID صاحب القناة")


async def receive_owner_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.user_data.get("add_owner"):
        return

    owner_id = update.message.text

    db.execute(
        "INSERT INTO owners(owner_id,active) VALUES(%s,TRUE) ON CONFLICT DO NOTHING",
        (owner_id,)
    )

    await update.message.reply_text("✅ تم إضافة Owner بنجاح")

    context.user_data.clear()
