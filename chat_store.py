import datetime as dt
import json
from typing import Dict, List, Optional

try:
    import psycopg
    from psycopg.rows import dict_row
    _DRIVER = "psycopg"
except ModuleNotFoundError:
    psycopg = None
    dict_row = None
    try:
        import psycopg2
        from psycopg2.extras import RealDictCursor
        _DRIVER = "psycopg2"
    except ModuleNotFoundError:
        psycopg2 = None
        RealDictCursor = None
        _DRIVER = None


class ChatStore:
    def __init__(self, database_url: str):
        if _DRIVER is None:
            raise ModuleNotFoundError(
                "No PostgreSQL driver found. Install one with "
                "`pip install psycopg[binary]` or `pip install psycopg2-binary`."
            )
        self.database_url = database_url

    def _connect(self):
        if _DRIVER == "psycopg":
            return psycopg.connect(self.database_url, row_factory=dict_row)
        return psycopg2.connect(self.database_url, cursor_factory=RealDictCursor)

    def ensure_schema(self) -> None:
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS users (
                    id BIGSERIAL PRIMARY KEY,
                    name TEXT NOT NULL UNIQUE,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                );
                """
            )
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS conversations (
                    id BIGSERIAL PRIMARY KEY,
                    user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                    title TEXT,
                    status TEXT NOT NULL DEFAULT 'active',
                    started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    ended_at TIMESTAMPTZ,
                    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    end_trigger TEXT
                );
                """
            )
            cur.execute(
                """
                ALTER TABLE conversations
                ADD COLUMN IF NOT EXISTS prompt_snapshot JSONB;
                """
            )
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS messages (
                    id BIGSERIAL PRIMARY KEY,
                    conversation_id BIGINT NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    position INTEGER NOT NULL,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
                    UNIQUE (conversation_id, position)
                );
                """
            )
            conn.commit()

    def upsert_user(self, name: str) -> int:
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO users (name)
                VALUES (%s)
                ON CONFLICT (name) DO UPDATE SET name = EXCLUDED.name
                RETURNING id;
                """,
                (name.strip(),),
            )
            row = cur.fetchone()
            conn.commit()
            return int(row["id"])

    def create_conversation(self, user_name: str, prompt_snapshot: Optional[Dict] = None) -> int:
        user_id = self.upsert_user(user_name)
        snapshot_json = json.dumps(prompt_snapshot) if prompt_snapshot is not None else None
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO conversations (user_id, status, prompt_snapshot)
                VALUES (%s, 'active', %s::jsonb)
                RETURNING id;
                """,
                (user_id, snapshot_json),
            )
            row = cur.fetchone()
            conn.commit()
            return int(row["id"])

    def append_message(self, conversation_id: int, role: str, content: str) -> None:
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO messages (conversation_id, role, content, position)
                VALUES (
                    %s,
                    %s,
                    %s,
                    COALESCE(
                        (SELECT MAX(position) + 1 FROM messages WHERE conversation_id = %s),
                        0
                    )
                );
                """,
                (conversation_id, role, content, conversation_id),
            )
            cur.execute(
                """
                UPDATE conversations
                SET updated_at = NOW()
                WHERE id = %s;
                """,
                (conversation_id,),
            )
            conn.commit()

    def has_user_messages(self, conversation_id: int) -> bool:
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute(
                """
                SELECT 1
                FROM messages
                WHERE conversation_id = %s
                  AND role = 'user'
                LIMIT 1;
                """,
                (conversation_id,),
            )
            return cur.fetchone() is not None

    def derive_title(self, conversation_id: int) -> str:
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute(
                """
                SELECT content
                FROM messages
                WHERE conversation_id = %s
                  AND role = 'user'
                ORDER BY position ASC
                LIMIT 1;
                """,
                (conversation_id,),
            )
            row = cur.fetchone()
            if not row:
                return "New chat"
            first_message = " ".join(row["content"].split())
            if not first_message:
                return "New chat"
            if len(first_message) <= 60:
                return first_message
            return first_message[:57].rstrip() + "..."

    def delete_conversation(self, conversation_id: int) -> None:
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute("DELETE FROM conversations WHERE id = %s;", (conversation_id,))
            conn.commit()

    def end_conversation(
        self,
        conversation_id: int,
        end_trigger: str,
        title: Optional[str] = None,
        discard_if_empty: bool = True,
    ) -> bool:
        has_user_messages = self.has_user_messages(conversation_id)
        if discard_if_empty and not has_user_messages:
            self.delete_conversation(conversation_id)
            return False

        final_title = title or self.derive_title(conversation_id)
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute(
                """
                UPDATE conversations
                SET status = 'ended',
                    ended_at = NOW(),
                    updated_at = NOW(),
                    end_trigger = %s,
                    title = COALESCE(NULLIF(%s, ''), title, 'New chat')
                WHERE id = %s;
                """,
                (end_trigger, final_title, conversation_id),
            )
            conn.commit()
        return True

    def finalize_stale_conversations(self, user_name: str, stale_minutes: int = 120) -> int:
        stale_cutoff = dt.datetime.now(dt.timezone.utc) - dt.timedelta(minutes=stale_minutes)
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute(
                """
                SELECT c.id
                FROM conversations c
                JOIN users u ON u.id = c.user_id
                WHERE u.name = %s
                  AND c.status = 'active'
                  AND c.updated_at < %s;
                """,
                (user_name.strip(), stale_cutoff),
            )
            rows = cur.fetchall()

        finalized = 0
        for row in rows:
            kept = self.end_conversation(int(row["id"]), "stale_timeout", discard_if_empty=True)
            if kept:
                finalized += 1
        return finalized

    def list_conversations(self, user_name: str, limit: int = 100) -> List[Dict]:
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                    c.id,
                    COALESCE(NULLIF(c.title, ''), 'New chat') AS title,
                    c.started_at,
                    c.ended_at,
                    u.name AS user_name
                FROM conversations c
                JOIN users u ON u.id = c.user_id
                WHERE u.name = %s
                  AND EXISTS (
                      SELECT 1
                      FROM messages m
                      WHERE m.conversation_id = c.id
                        AND m.role = 'user'
                  )
                ORDER BY COALESCE(c.ended_at, c.started_at) DESC
                LIMIT %s;
                """,
                (user_name.strip(), limit),
            )
            return [dict(row) for row in cur.fetchall()]

    def get_messages(self, conversation_id: int) -> List[Dict]:
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute(
                """
                SELECT role, content, position, created_at
                FROM messages
                WHERE conversation_id = %s
                ORDER BY position ASC;
                """,
                (conversation_id,),
            )
            rows = cur.fetchall()
            return [
                {"role": row["role"], "content": row["content"], "position": row["position"], "created_at": row["created_at"]}
                for row in rows
            ]
