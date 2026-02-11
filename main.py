import re
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters
)

from config import BOT_TOKEN
from handlers.start import start
from handlers.common import is_superadmin

# Owner
from handlers.owner import link_channel, receive_channel

# Members
from handlers.members import (
    members_menu, add_member_start, search_member_start, remove_member_start,
    handle_text as members_text,
    pick_channel_for_add, pick_channel_for_search, pick_channel_for_remove,
    add_duration_pick, add_confirm,
    extend_selected, reactivate_selected, invite_link_selected, remove_selected
)

# Settings
from handlers.settings import (
    open_settings, pick_settings_channel,
    toggle_notify, toggle_autoremove,
    open_invite_duration, set_invite_minutes,
    open_welcome_message, set_welcome_prompt, receive_welcome_text, clear_welcome_message
)

# Admin
from handlers.admin import (
    admin_panel, manage_owners,
    add_owner_start, extend_owner_start, disable_owner_start, search_owner_start,
    owners_list, system_stats, broadcast_start,
    admin_text_receiver, owner_action_callback
)

# Jobs
from jobs.expire_members import expire_members_job
from jobs.owner_guard import owner_guard_job

# UI
from ui import owner_main_menu


async def back_main(update, context):
    q = update.callback_query
    await q.answer()
    uid = q.from_user.id
    await q.message.reply_text("🏠 القائمة الرئيسية", reply_markup=owner_main_menu(is_superadmin(uid)))


# ===== wrappers to extract IDs from callback_data =====

async def _pick_ch_add(update, context):
    cid = int(update.callback_query.data.split(":")[1])
    await pick_channel_for_add(update, context, cid)

async def _pick_ch_search(update, context):
    cid = int(update.callback_query.data.split(":")[1])
    await pick_channel_for_search(update, context, cid)

async def _pick_ch_remove(update, context):
    cid = int(update.callback_query.data.split(":")[1])
    await pick_channel_for_remove(update, context, cid)

async def _settings_pick_ch(update, context):
    cid = int(update.callback_query.data.split(":")[1])
    await pick_settings_channel(update, context, cid)

async def _owner_extend30(update, context):
    oid = int(update.callback_query.data.split(":")[1])
    await owner_action_callback(update, context, "extend30", oid)

async def _owner_extend365(update, context):
    oid = int(update.callback_query.data.split(":")[1])
    await owner_action_callback(update, context, "extend365", oid)

async def _owner_enable(update, context):
    oid = int(update.callback_query.data.split(":")[1])
    await owner_action_callback(update, context, "enable", oid)

async def _owner_disable(update, context):
    oid = int(update.callback_query.data.split(":")[1])
    await owner_action_callback(update, context, "disable", oid)

async def _owner_note(update, context):
    oid = int(update.callback_query.data.split(":")[1])
    await owner_action_callback(update, context, "note", oid)


def main():
    app = Application.builder().token(BOT_TOKEN).build()

    # /start
    app.add_handler(CommandHandler("start", start))

    # Global back
    app.add_handler(CallbackQueryHandler(back_main, pattern=r"^back_main$"))

    # Admin entry
    app.add_handler(CallbackQueryHandler(admin_panel, pattern=r"^admin_panel$"))
    app.add_handler(CallbackQueryHandler(manage_owners, pattern=r"^manage_owners$"))

    app.add_handler(CallbackQueryHandler(add_owner_start, pattern=r"^add_owner$"))
    app.add_handler(CallbackQueryHandler(extend_owner_start, pattern=r"^extend_owner$"))
    app.add_handler(CallbackQueryHandler(disable_owner_start, pattern=r"^disable_owner$"))
    app.add_handler(CallbackQueryHandler(search_owner_start, pattern=r"^search_owner$"))
    app.add_handler(CallbackQueryHandler(owners_list, pattern=r"^owners_list$"))
    app.add_handler(CallbackQueryHandler(system_stats, pattern=r"^system_stats$"))
    app.add_handler(CallbackQueryHandler(broadcast_start, pattern=r"^broadcast$"))

    # Admin owner actions (dynamic)
    app.add_handler(CallbackQueryHandler(_owner_extend30, pattern=r"^owner_extend30:\d+$"))
    app.add_handler(CallbackQueryHandler(_owner_extend365, pattern=r"^owner_extend365:\d+$"))
    app.add_handler(CallbackQueryHandler(_owner_enable, pattern=r"^owner_enable:\d+$"))
    app.add_handler(CallbackQueryHandler(_owner_disable, pattern=r"^owner_disable:\d+$"))
    app.add_handler(CallbackQueryHandler(_owner_note, pattern=r"^owner_note:\d+$"))

    # Owner: link channel
    app.add_handler(CallbackQueryHandler(link_channel, pattern=r"^link_channel$"))

    # Members menus
    app.add_handler(CallbackQueryHandler(members_menu, pattern=r"^members_menu$"))
    app.add_handler(CallbackQueryHandler(add_member_start, pattern=r"^add_member$"))
    app.add_handler(CallbackQueryHandler(search_member_start, pattern=r"^search_member$"))
    app.add_handler(CallbackQueryHandler(remove_member_start, pattern=r"^remove_member$"))

    # pick channel for member flows
    app.add_handler(CallbackQueryHandler(_pick_ch_add, pattern=r"^pick_ch_add:\d+$"))
    app.add_handler(CallbackQueryHandler(_pick_ch_search, pattern=r"^pick_ch_search:\d+$"))
    app.add_handler(CallbackQueryHandler(_pick_ch_remove, pattern=r"^pick_ch_remove:\d+$"))

    # add duration + confirm
    app.add_handler(CallbackQueryHandler(add_duration_pick, pattern=r"^add_dur:(7|30|90|custom)$"))
    app.add_handler(CallbackQueryHandler(add_confirm, pattern=r"^add_confirm$"))

    # selected member actions
    app.add_handler(CallbackQueryHandler(lambda u, c: extend_selected(u, c, 7), pattern=r"^extend_7$"))
    app.add_handler(CallbackQueryHandler(lambda u, c: extend_selected(u, c, 30), pattern=r"^extend_30$"))
    app.add_handler(CallbackQueryHandler(reactivate_selected, pattern=r"^reactivate$"))
    app.add_handler(CallbackQueryHandler(invite_link_selected, pattern=r"^invite_link$"))
    app.add_handler(CallbackQueryHandler(remove_selected, pattern=r"^remove_member$"))

    # Settings
    app.add_handler(CallbackQueryHandler(open_settings, pattern=r"^channel_settings$"))
    app.add_handler(CallbackQueryHandler(_settings_pick_ch, pattern=r"^settings_ch:\d+$"))
    app.add_handler(CallbackQueryHandler(toggle_notify, pattern=r"^toggle_notify$"))
    app.add_handler(CallbackQueryHandler(toggle_autoremove, pattern=r"^toggle_autoremove$"))
    app.add_handler(CallbackQueryHandler(open_invite_duration, pattern=r"^invite_duration$"))
    app.add_handler(CallbackQueryHandler(lambda u, c: set_invite_minutes(u, c, 5), pattern=r"^set_invite_5$"))
    app.add_handler(CallbackQueryHandler(lambda u, c: set_invite_minutes(u, c, 10), pattern=r"^set_invite_10$"))
    app.add_handler(CallbackQueryHandler(lambda u, c: set_invite_minutes(u, c, 30), pattern=r"^set_invite_30$"))
    app.add_handler(CallbackQueryHandler(lambda u, c: set_invite_minutes(u, c, 60), pattern=r"^set_invite_60$"))
    app.add_handler(CallbackQueryHandler(open_welcome_message, pattern=r"^welcome_message$"))
    app.add_handler(CallbackQueryHandler(set_welcome_prompt, pattern=r"^set_welcome_msg$"))
    app.add_handler(CallbackQueryHandler(clear_welcome_message, pattern=r"^clear_welcome_msg$"))

    # Text receiver (admin + owner + members + settings)
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, admin_text_receiver))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, receive_channel))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, members_text))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, receive_welcome_text))

    # Jobs
    app.job_queue.run_repeating(expire_members_job, interval=60, first=10)  # كل دقيقة
    app.job_queue.run_repeating(owner_guard_job, interval=300, first=20)    # كل 5 دقائق

    app.run_polling()


if __name__ == "__main__":
    main()
