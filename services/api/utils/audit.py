import os
import psycopg

DATABASE_URL = os.getenv("DATABASE_URL")


def write_audit_event(
    event_type: str,
    user_id: str | None = None,
    ip_address: str | None = None,
    metadata: dict | None = None,
):
    """
    Insert one row into audit_logs. Fire-and-forget — if it fails we log the
    error but never let it break the request that triggered it.
    """
    try:
        with psycopg.connect(DATABASE_URL) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO audit_logs (event_type, user_id, ip_address, metadata)
                    VALUES (%s, %s, %s, %s)
                    """,
                    (event_type, user_id, ip_address, psycopg.types.json.Jsonb(metadata or {})),
                )
            conn.commit()
    except Exception as e:
        print(f"[audit] failed to write event '{event_type}': {e}")
