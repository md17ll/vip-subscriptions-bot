from database import db


async def owner_guard_job(context):
    # اجلب الـ owners الذين انتهى اشتراكهم وهم ما زالوا active
    rows = db.fetch("""
        SELECT owner_id, sub_expires_at
        FROM owners
        WHERE active=TRUE
          AND sub_expires_at IS NOT NULL
          AND sub_expires_at <= NOW()
        LIMIT 500
    """)

    if not rows:
        return

    for r in rows:
        owner_id = int(r["owner_id"])

        db.execute(
            "UPDATE owners SET active=FALSE, updated_at=CURRENT_TIMESTAMP WHERE owner_id=%s",
            (owner_id,)
        )
        db.execute(
            "INSERT INTO logs(owner_id, action, details) VALUES(%s,%s,%s)",
            (owner_id, "owner_auto_disabled", "subscription expired")
        )
