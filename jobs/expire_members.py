from database import db
from datetime import datetime


async def expire_members_job(context):
    rows = db.fetch("""
        SELECT s.id, s.user_id, s.channel_id, c.chat_id
        FROM subscribers s
        JOIN channels c ON c.id = s.channel_id
        WHERE s.status='active'
          AND s.expires_at <= NOW()
        LIMIT 200
    """)

    if not rows:
        return

    bot = context.bot

    for r in rows:
        sub_id = int(r["id"])
        user_id = int(r["user_id"])
        chat_id = int(r["chat_id"])

        # تحديث الحالة أولاً حتى لا تتكرر المحاولة
        db.execute(
            "UPDATE subscribers SET status='expired', updated_at=CURRENT_TIMESTAMP WHERE id=%s",
            (sub_id,)
        )

        try:
            # إزالة المستخدم (ban ثم unban)
            await bot.ban_chat_member(chat_id, user_id)
            await bot.unban_chat_member(chat_id, user_id)

            db.execute(
                "INSERT INTO logs(channel_id, user_id, action, details) VALUES(%s,%s,%s,%s)",
                (int(r["channel_id"]), user_id, "member_removed", "expired_auto")
            )

        except Exception as e:
            # لا نوقف الـ job حتى لو فشل الحذف
            db.execute(
                "INSERT INTO logs(channel_id, user_id, action, details) VALUES(%s,%s,%s,%s)",
                (int(r["channel_id"]), user_id, "remove_failed", str(e)[:200])
            )
