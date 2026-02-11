import os

# Telegram
BOT_TOKEN = os.getenv("BOT_TOKEN")

# Railway PostgreSQL
DATABASE_URL = os.getenv("DATABASE_URL")

# Super Admins (IDs مفصولة بفاصلة)
SUPERADMINS = [
    int(x) for x in os.getenv("SUPERADMINS", "").split(",") if x
]

# Invite link default duration
DEFAULT_INVITE_MINUTES = 10
