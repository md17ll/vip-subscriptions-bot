import psycopg2
from psycopg2.extras import RealDictCursor
from config import DATABASE_URL


class DB:
    def __init__(self):
        self.conn = psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)
        self.init_tables()

    def init_tables(self):
        cur = self.conn.cursor()

        # 1) Owners (أصحاب القنوات) — اشتراكهم عندك
        cur.execute("""
        CREATE TABLE IF NOT EXISTS owners (
            owner_id BIGINT PRIMARY KEY,
            active BOOLEAN NOT NULL DEFAULT TRUE,
            sub_expires_at TIMESTAMP NULL,
            note TEXT NOT NULL DEFAULT '',
            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        """)

        # 2) Channels (قنوات/مجموعات كل Owner) + إعدادات القناة
        cur.execute("""
        CREATE TABLE IF NOT EXISTS channels (
            id SERIAL PRIMARY KEY,
            owner_id BIGINT NOT NULL REFERENCES owners(owner_id) ON DELETE CASCADE,
            chat_id BIGINT NOT NULL,
            title TEXT NOT NULL DEFAULT '',
            invite_minutes INT NOT NULL DEFAULT 10,  -- 5/10/30/60
            notify_enabled BOOLEAN NOT NULL DEFAULT TRUE,
            auto_remove_enabled BOOLEAN NOT NULL DEFAULT TRUE,
            welcome_message TEXT NOT NULL DEFAULT '',
            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(owner_id, chat_id)
        );
        """)

        # 3) Subscribers (مشتركين VIP لكل قناة)
        cur.execute("""
        CREATE TABLE IF NOT EXISTS subscribers (
            id SERIAL PRIMARY KEY,
            channel_id INT NOT NULL REFERENCES channels(id) ON DELETE CASCADE,
            user_id BIGINT NOT NULL,
            name TEXT NOT NULL DEFAULT '',
            status TEXT NOT NULL DEFAULT 'active',  -- active/expired/removed
            expires_at TIMESTAMP NOT NULL,
            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(channel_id, user_id)
        );
        """)

        # ✅ جديد (بدون تخريب): إذا كان الجدول قديم وما فيه name نضيفه
        cur.execute("""
        ALTER TABLE subscribers
        ADD COLUMN IF NOT EXISTS name TEXT NOT NULL DEFAULT '';
        """)

        # 4) Logs (سجل العمليات التفصيلي)
        cur.execute("""
        CREATE TABLE IF NOT EXISTS logs (
            id SERIAL PRIMARY KEY,
            owner_id BIGINT NULL,
            channel_id INT NULL,
            user_id BIGINT NULL,
            action TEXT NOT NULL,
            details TEXT NOT NULL DEFAULT '',
            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        """)

        # Indexes (سرعة)
        cur.execute("CREATE INDEX IF NOT EXISTS idx_channels_owner ON channels(owner_id);")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_subs_channel ON subscribers(channel_id);")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_subs_expires ON subscribers(expires_at);")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_logs_owner ON logs(owner_id);")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_logs_channel ON logs(channel_id);")

        self.conn.commit()

    def execute(self, query, params=None):
        cur = self.conn.cursor()
        cur.execute(query, params)
        self.conn.commit()

    def fetch(self, query, params=None):
        cur = self.conn.cursor()
        cur.execute(query, params)
        return cur.fetchall()

    def fetch_one(self, query, params=None):
        cur = self.conn.cursor()
        cur.execute(query, params)
        return cur.fetchone()


db = DB()
