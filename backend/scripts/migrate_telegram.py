"""
Database Migration Script for Telegram Emergency Contacts & Alerts.
Applies non-destructive ALTER TABLE commands to ensure existing Neon databases
support Telegram pairing, chat IDs, consent timestamps, and alert statuses.
"""

import os
import sys
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

MIGRATION_SQL = """
-- 1. Upgrade emergency_contacts table
ALTER TABLE emergency_contacts 
    ADD COLUMN IF NOT EXISTS telegram_chat_id TEXT,
    ADD COLUMN IF NOT EXISTS telegram_username TEXT,
    ADD COLUMN IF NOT EXISTS telegram_status TEXT DEFAULT 'NOT_CONNECTED',
    ADD COLUMN IF NOT EXISTS pairing_code_hash TEXT,
    ADD COLUMN IF NOT EXISTS pairing_code_expires_at TIMESTAMP WITH TIME ZONE,
    ADD COLUMN IF NOT EXISTS connected_at TIMESTAMP WITH TIME ZONE,
    ADD COLUMN IF NOT EXISTS consent_at TIMESTAMP WITH TIME ZONE,
    ADD COLUMN IF NOT EXISTS user_name TEXT DEFAULT '';

-- 2. Upgrade emergency_alerts table
ALTER TABLE emergency_alerts
    ADD COLUMN IF NOT EXISTS contact_id TEXT DEFAULT '',
    ADD COLUMN IF NOT EXISTS channel TEXT DEFAULT 'TELEGRAM',
    ADD COLUMN IF NOT EXISTS message_type TEXT DEFAULT 'CRISIS_ALERT',
    ADD COLUMN IF NOT EXISTS telegram_message_id TEXT,
    ADD COLUMN IF NOT EXISTS error_details TEXT,
    ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW();

-- 3. Create telegram update deduplication table
CREATE TABLE IF NOT EXISTS telegram_processed_updates (
    update_id BIGINT PRIMARY KEY,
    processed_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
"""

def run_migration():
    if not DATABASE_URL:
        print("[MIGRATE] No DATABASE_URL set; skipping remote Neon migration (in-memory database will use new schema).")
        return

    print("[MIGRATE] Connecting to PostgreSQL/Neon database...")
    try:
        import psycopg
        with psycopg.connect(DATABASE_URL) as conn:
            with conn.cursor() as cur:
                cur.execute(MIGRATION_SQL)
            conn.commit()
        print("[MIGRATE] Successfully applied Telegram database migrations!")
    except ImportError:
        try:
            import psycopg2
            conn = psycopg2.connect(DATABASE_URL)
            with conn.cursor() as cur:
                cur.execute(MIGRATION_SQL)
            conn.commit()
            conn.close()
            print("[MIGRATE] Successfully applied Telegram database migrations (via psycopg2)!")
        except Exception as e:
            print(f"[MIGRATE] Database migration failed: {e}")
            sys.exit(1)
    except Exception as e:
        print(f"[MIGRATE] Database migration failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    run_migration()
