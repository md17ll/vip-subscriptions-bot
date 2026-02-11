from datetime import datetime
from database import db


async def expire_members_job(context):
    # اجلب جميع الاشتراكات التي انتهت وهي نشطة
    rows = db.fetch("""
        SELECT s.id AS sub_id, s.user_id, s.channel_id, s.expires_at,
               c.chat_id, c.auto_remove_enabled, c.owner_id
        FROM subscribers s
        JOIN channels c ON c.id = s.channel_id
        WHERE s.status='active' AND s.expires_at <= NOW()
        ORDER BY s.expires_at ASC
        LIMIT 500
    """)

    if not rows:
        return

    for r in rows:
        sub_id = r["sub_id"]
        user_id = int(r["user_id"])
        channel_id = int(r["channel_id"])
        chat_id = int(r["chat_id"])
        owner_id = int(r["owner_id"])
        auto_remove = bool(r["auto_remove_enabled"])

        # 1) حدّث الحالة إلى expired
        db.execute(
            "UPDATE subscribers SET status='expired', updated_at=CURRENT_TIMESTAMP WHERE id=%s",
            (sub_id,)
        )
        db.execute(
            "INSERT INTO logs(owner_id, channel_id, user_id, action, details) VALUES(%s,%s,%s,%s,%s)",
            (owner_id, channel_id, user_id, "marked_expired", "")
        )

        # 2) إن كان الحذف التلقائي مفعّل -> إزالة من القناة
        if auto_remove:
            try:
                await context.bot.ban_chat_member(chat_id, user_id)
                await context.bot.unban_chat_member(chat_id, user_id)

                db.execute(
                    "INSERT INTO logs(owner_id, channel_id, user_id, action, details) VALUES(%s,%s,%s,%s,%s)",
                    (owner_id, channel_id, user_id, "auto_removed", "")
                )
            except Exception as e:
                db.execute(
                    "INSERT INTO logs(owner_id, channel_id, user_id, action, details) VALUES(%s,%s,%s,%s,%s)",
                    (owner_id, channel_id, user_id, "auto_remove_failed", str(e))
                )
