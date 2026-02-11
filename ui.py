from telegram import InlineKeyboardMarkup, InlineKeyboardButton


# =========================
# MAIN MENUS
# =========================

def owner_main_menu(is_admin=False):
    rows = [
        [InlineKeyboardButton("🔗 ربط قناة / مجموعة", callback_data="link_channel")],
        [InlineKeyboardButton("👤 إدارة المشتركين", callback_data="members_menu")],
        [InlineKeyboardButton("⏳ القريبة من الانتهاء", callback_data="expiring_menu")],
        [InlineKeyboardButton("📋 قائمة المشتركين", callback_data="list_members")],
        [InlineKeyboardButton("📊 إحصائيات القناة", callback_data="channel_stats")],
        [InlineKeyboardButton("⚙️ إعدادات القناة", callback_data="channel_settings")],
        [InlineKeyboardButton("🆘 مساعدة", callback_data="help")]
    ]

    if is_admin:
        rows.append([InlineKeyboardButton("🛠️ لوحة الأدمن", callback_data="admin_panel")])

    return InlineKeyboardMarkup(rows)


# زر رجوع عام للمنيو الرئيسية
back_main_kb = InlineKeyboardMarkup([
    [InlineKeyboardButton("🔙 رجوع", callback_data="back_main")]
])


# =========================
# ADMIN PANEL
# =========================

admin_panel_menu = InlineKeyboardMarkup([
    [InlineKeyboardButton("🏷️ إدارة أصحاب القنوات", callback_data="manage_owners")],
    [InlineKeyboardButton("📋 قائمة الـ Owners", callback_data="owners_list")],
    [InlineKeyboardButton("📊 إحصائيات النظام", callback_data="system_stats")],
    [InlineKeyboardButton("📨 رسالة جماعية", callback_data="broadcast")],
    [InlineKeyboardButton("🔙 رجوع", callback_data="back_main")]
])


manage_owners_menu = InlineKeyboardMarkup([
    [InlineKeyboardButton("➕ إضافة Owner", callback_data="add_owner")],
    [InlineKeyboardButton("♻️ تمديد اشتراك Owner", callback_data="extend_owner")],
    [InlineKeyboardButton("⛔ إيقاف Owner", callback_data="disable_owner")],
    [InlineKeyboardButton("🔍 بحث عن Owner", callback_data="search_owner")],
    [InlineKeyboardButton("🔙 رجوع", callback_data="admin_panel")]
])


# =========================
# MEMBERS
# =========================

members_menu = InlineKeyboardMarkup([
    [InlineKeyboardButton("➕ إضافة مشترك", callback_data="add_member")],
    [InlineKeyboardButton("🔍 بحث عن مشترك", callback_data="search_member")],
    [InlineKeyboardButton("🚫 حذف مشترك", callback_data="remove_member")],
    [InlineKeyboardButton("🔙 رجوع", callback_data="back_main")]
])


member_actions_menu = InlineKeyboardMarkup([
    [InlineKeyboardButton("🔄 تمديد 7 أيام", callback_data="extend_7")],
    [InlineKeyboardButton("🔄 تمديد 30 يوم", callback_data="extend_30")],
    [InlineKeyboardButton("♻️ إعادة تفعيل", callback_data="reactivate")],
    [InlineKeyboardButton("🔗 رابط دخول", callback_data="invite_link")],
    [InlineKeyboardButton("🚫 حذف", callback_data="remove_selected")],  # ✅ إصلاح التعارض
    [InlineKeyboardButton("🔙 رجوع", callback_data="members_menu")]
])


# =========================
# LISTS / STATS / EXPIRING
# =========================

expiring_menu_kb = InlineKeyboardMarkup([
    [InlineKeyboardButton("🔙 رجوع", callback_data="back_main")]
])

list_members_kb = InlineKeyboardMarkup([
    [InlineKeyboardButton("🔙 رجوع", callback_data="back_main")]
])

channel_stats_kb = InlineKeyboardMarkup([
    [InlineKeyboardButton("🔙 رجوع", callback_data="back_main")]
])


# =========================
# SETTINGS
# =========================

channel_settings_menu = InlineKeyboardMarkup([
    [InlineKeyboardButton("🔔 تنبيهات انتهاء الاشتراك", callback_data="toggle_notify")],
    [InlineKeyboardButton("🧹 الحذف التلقائي", callback_data="toggle_autoremove")],
    [InlineKeyboardButton("⏱️ مدة رابط الدعوة", callback_data="invite_duration")],
    [InlineKeyboardButton("📩 رسالة الدخول", callback_data="welcome_message")],
    [InlineKeyboardButton("🔙 رجوع", callback_data="back_main")]
])


invite_duration_menu = InlineKeyboardMarkup([
    [InlineKeyboardButton("5 دقائق", callback_data="set_invite_5")],
    [InlineKeyboardButton("10 دقائق", callback_data="set_invite_10")],
    [InlineKeyboardButton("30 دقيقة", callback_data="set_invite_30")],
    [InlineKeyboardButton("60 دقيقة", callback_data="set_invite_60")],
    [InlineKeyboardButton("🔙 رجوع", callback_data="channel_settings")]
])
