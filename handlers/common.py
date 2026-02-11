from config import SUPERADMINS
from database import db
from datetime import datetime


def is_superadmin(user_id: int) -> bool:
    return user_id in SUPERADMINS


def get_owner(user_id: int):
    row = db.fetch_one(
        "SELECT * FROM owners WHERE owner_id=%s",
        (user_id,)
    )
    return row


def owner_is_active(user_id: int) -> bool:
    row = get_owner(user_id)

    if not row:
        return False

    if not row["active"]:
        return False

    if row["sub_expires_at"] is None:
        return True

    if row["sub_expires_at"] < datetime.utcnow():
        return False

    return True


def require_owner_active(user_id: int):
    if not owner_is_active(user_id):
        return False, "⛔ اشتراكك غير فعال، تواصل مع الإدارة."
    return True, None
