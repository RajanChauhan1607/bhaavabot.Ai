import os
import psycopg
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://neondb_owner:npg_JIdRbs9uc5LH@ep-dawn-dawn-azxkv85y-pooler.c-3.ap-southeast-1.aws.neon.tech/neondb?sslmode=require"
)

SCHEMA_SQL = """
-- ============================================================
-- 1. BHAAVABOT BACKEND TABLES
-- ============================================================

CREATE TABLE IF NOT EXISTS empathy_profiles (
    user_id TEXT PRIMARY KEY,
    total_empathy_score DOUBLE PRECISION DEFAULT 60.0,
    emotional_empathy_score DOUBLE PRECISION DEFAULT 0.7,
    cognitive_empathy_score DOUBLE PRECISION DEFAULT 0.7,
    dispersion_score DOUBLE PRECISION DEFAULT 0.8,
    consistency_level TEXT DEFAULT 'high',
    profile_type TEXT DEFAULT 'PROFILE_A',
    emotional_style TEXT DEFAULT 'responsive',
    cognitive_style TEXT DEFAULT 'collaborative',
    communication_style TEXT DEFAULT 'warm',
    preferred_pacing TEXT DEFAULT 'normal',
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS conversations (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL DEFAULT 'guest',
    title TEXT NOT NULL DEFAULT 'A Quiet Conversation',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS messages (
    id TEXT PRIMARY KEY,
    conversation_id TEXT NOT NULL,
    user_id TEXT NOT NULL DEFAULT 'guest',
    role TEXT NOT NULL,
    content TEXT NOT NULL,
    detected_emotion TEXT DEFAULT 'neutral',
    emotion_confidence DOUBLE PRECISION DEFAULT 0.8,
    emotion_intensity DOUBLE PRECISION DEFAULT 0.5,
    safety_level TEXT DEFAULT 'NORMAL',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS reflections (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL DEFAULT 'guest',
    mood TEXT NOT NULL,
    note TEXT DEFAULT '',
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS favorites (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL DEFAULT 'guest',
    title TEXT NOT NULL,
    item_type TEXT DEFAULT 'book'
);

CREATE TABLE IF NOT EXISTS user_preferences (
    user_id TEXT PRIMARY KEY,
    preferred_theme TEXT DEFAULT 'I just want someone to listen',
    preferred_content_type TEXT DEFAULT 'all',
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS emergency_contacts (
    user_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    phone TEXT DEFAULT '',
    relationship TEXT DEFAULT 'Family / Friend',
    telegram_chat_id TEXT,
    telegram_username TEXT,
    telegram_status TEXT DEFAULT 'NOT_CONNECTED',
    pairing_code_hash TEXT,
    pairing_code_expires_at TIMESTAMP WITH TIME ZONE,
    connected_at TIMESTAMP WITH TIME ZONE,
    consent_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS emergency_alerts (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL DEFAULT 'guest',
    contact_id TEXT DEFAULT '',
    contact_name TEXT NOT NULL,
    contact_phone TEXT DEFAULT '',
    channel TEXT NOT NULL DEFAULT 'TELEGRAM',
    message_type TEXT NOT NULL DEFAULT 'CRISIS_ALERT',
    message TEXT NOT NULL,
    trigger_text TEXT DEFAULT '',
    status TEXT NOT NULL DEFAULT 'SIMULATED',
    telegram_message_id TEXT,
    error_details TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS telegram_processed_updates (
    update_id BIGINT PRIMARY KEY,
    processed_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- ============================================================
-- 2. FRONTEND AUTH TABLES (Drizzle ORM / Better-Auth)
-- ============================================================

CREATE TABLE IF NOT EXISTS "user" (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    email TEXT NOT NULL UNIQUE,
    "emailVerified" BOOLEAN NOT NULL DEFAULT FALSE,
    image TEXT,
    "createdAt" TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    "updatedAt" TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS session (
    id TEXT PRIMARY KEY,
    "expiresAt" TIMESTAMP WITH TIME ZONE NOT NULL,
    token TEXT NOT NULL UNIQUE,
    "createdAt" TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    "updatedAt" TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    "ipAddress" TEXT,
    "userAgent" TEXT,
    "userId" TEXT NOT NULL REFERENCES "user"(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS account (
    id TEXT PRIMARY KEY,
    "accountId" TEXT NOT NULL,
    "providerId" TEXT NOT NULL,
    "userId" TEXT NOT NULL REFERENCES "user"(id) ON DELETE CASCADE,
    "accessToken" TEXT,
    "refreshToken" TEXT,
    "idToken" TEXT,
    "accessTokenExpiresAt" TIMESTAMP WITH TIME ZONE,
    "refreshTokenExpiresAt" TIMESTAMP WITH TIME ZONE,
    scope TEXT,
    password TEXT,
    "createdAt" TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    "updatedAt" TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS verification (
    id TEXT PRIMARY KEY,
    identifier TEXT NOT NULL,
    value TEXT NOT NULL,
    "expiresAt" TIMESTAMP WITH TIME ZONE NOT NULL,
    "createdAt" TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    "updatedAt" TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_messages_conversation_id ON messages (conversation_id);
CREATE INDEX IF NOT EXISTS idx_conversations_user_id ON conversations (user_id);
CREATE INDEX IF NOT EXISTS idx_reflections_user_id ON reflections (user_id);
"""

INITIAL_SEEDS_SQL = """
-- Default sample conversations for guest
INSERT INTO conversations (id, user_id, title, created_at, updated_at)
VALUES 
    ('conv-welcome', 'guest', 'A Quiet Beginning', NOW(), NOW()),
    ('conv-peace', 'guest', 'Unwinding After a Long Day', NOW(), NOW())
ON CONFLICT (id) DO NOTHING;

-- Default sample messages
INSERT INTO messages (id, conversation_id, user_id, role, content, detected_emotion, emotion_confidence, emotion_intensity, safety_level, created_at)
VALUES 
    ('msg-welcome-1', 'conv-welcome', 'guest', 'bot', 'Welcome to BhaavaBot. Whenever the world feels a bit fast or noisy, this space is here to hold what you are carrying. What is on your mind today?', 'neutral', 0.9, 0.3, 'NORMAL', NOW()),
    ('msg-peace-1', 'conv-peace', 'guest', 'user', 'I had a long day and need some quiet time.', 'tired', 0.85, 0.6, 'NORMAL', NOW()),
    ('msg-peace-2', 'conv-peace', 'guest', 'bot', 'You made it through the day. Let your shoulders soften a little. You don''t have to carry anything else right now.', 'tired', 0.85, 0.5, 'NORMAL', NOW())
ON CONFLICT (id) DO NOTHING;

-- Default sample reflections
INSERT INTO reflections (id, user_id, mood, note, created_at)
VALUES 
    ('sample-1', 'guest', 'Calm', 'Paused to take deep breaths in the garden.', 'Today · 9:15 AM'),
    ('sample-2', 'guest', 'Hopeful', 'Wrote down one thing I am looking forward to.', 'Yesterday · 8:40 PM'),
    ('sample-3', 'guest', 'Heavy', 'A hard morning, but I reached out anyway.', 'Sep 17 · 11:02 AM'),
    ('sample-4', 'guest', 'Tired', 'Long day of meetings. Resting now.', 'Sep 16 · 10:20 PM')
ON CONFLICT (id) DO NOTHING;

-- Default user preferences
INSERT INTO user_preferences (user_id, preferred_theme, preferred_content_type, updated_at)
VALUES ('guest', 'I just want someone to listen', 'all', NOW())
ON CONFLICT (user_id) DO NOTHING;
"""

def setup_database():
    print(f"Connecting to Neon PostgreSQL...")
    with psycopg.connect(DATABASE_URL) as conn:
        with conn.cursor() as cur:
            print("Applying schema...")
            cur.execute(SCHEMA_SQL)
            print("Seeding initial data...")
            cur.execute(INITIAL_SEEDS_SQL)
        conn.commit()
    print("Database schema created and seeded successfully!")

if __name__ == "__main__":
    setup_database()
