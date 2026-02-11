from telegram import Update
from telegram.ext import ContextTypes
from ui import owner_main_menu
from handlers.common import is_superadmin


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    is_admin = is_superadmin(user_id)

    text = (
        "👋 أهلاً بك في نظام إدارة اشتراكات قنوات VIP\n\n"
        "يمكنك من هنا إدارة قنواتك ومشتركيك بسهولة."
    )

    await update.message.reply_text(
        text,
        reply_markup=owner_main_menu(is_admin)
    )
