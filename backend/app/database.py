import os
import logging
from typing import List, Dict, Any, Optional, Set
from datetime import datetime, timedelta, timezone
import uuid
import hashlib
import secrets
from contextlib import contextmanager
from dotenv import load_dotenv

try:
    import psycopg
    from psycopg.rows import dict_row
    PSYCOPG_V3 = True
except ImportError:
    try:
        import psycopg2 as psycopg
        from psycopg2.extras import RealDictCursor
        PSYCOPG_V3 = False
    except ImportError:
        psycopg = None
        PSYCOPG_V3 = False

from app.models.schemas import EmpathyProfile
from app.services.content_library import CURATED_BOOKS, CURATED_MUSIC

load_dotenv()

logger = logging.getLogger("bhaavabot.database")

DATABASE_URL = os.getenv("DATABASE_URL", "")

# Resilient in-memory fallback stores
_memory_reflections: List[Dict[str, Any]] = [
    {
        "id": "sample-1",
        "mood": "Calm",
        "note": "Paused to take deep breaths in the garden.",
        "created_at": "Today · 9:15 AM",
        "user_id": "guest"
    },
    {
        "id": "sample-2",
        "mood": "Hopeful",
        "note": "Wrote down one thing I am looking forward to.",
        "created_at": "Yesterday · 8:40 PM",
        "user_id": "guest"
    },
    {
        "id": "sample-3",
        "mood": "Heavy",
        "note": "A hard morning, but I reached out anyway.",
        "created_at": "Sep 17 · 11:02 AM",
        "user_id": "guest"
    },
    {
        "id": "sample-4",
        "mood": "Tired",
        "note": "Long day of meetings. Resting now.",
        "created_at": "Sep 16 · 10:20 PM",
        "user_id": "guest"
    }
]
_memory_favorites: List[Dict[str, str]] = []
_memory_books: List[Dict[str, Any]] = [b.model_dump() for b in CURATED_BOOKS]
_memory_music: List[Dict[str, Any]] = [m.model_dump() for m in CURATED_MUSIC]
_memory_emergency_contacts: Dict[str, Dict[str, Any]] = {}
_memory_emergency_alerts: List[Dict[str, Any]] = []
_memory_processed_telegram_updates: Set[int] = set()
_memory_empathy_profiles: Dict[str, Dict[str, Any]] = {}
_memory_conversations: List[Dict[str, Any]] = [
    {
        "id": "conv-welcome",
        "title": "A Quiet Beginning",
        "user_id": "guest",
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat()
    },
    {
        "id": "conv-peace",
        "title": "Unwinding After a Long Day",
        "user_id": "guest",
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat()
    }
]
_memory_messages: List[Dict[str, Any]] = [
    {
        "id": "msg-welcome-1",
        "conversation_id": "conv-welcome",
        "user_id": "guest",
        "role": "bot",
        "content": "Welcome to BhaavaBot. Whenever the world feels a bit fast or noisy, this space is here to hold what you are carrying. What is on your mind today?",
        "detected_emotion": "neutral",
        "emotion_confidence": 0.9,
        "emotion_intensity": 0.3,
        "safety_level": "NORMAL",
        "created_at": datetime.now().isoformat()
    },
    {
        "id": "msg-peace-1",
        "conversation_id": "conv-peace",
        "user_id": "guest",
        "role": "user",
        "content": "I had a long day and need some quiet time.",
        "detected_emotion": "tired",
        "emotion_confidence": 0.85,
        "emotion_intensity": 0.6,
        "safety_level": "NORMAL",
        "created_at": datetime.now().isoformat()
    },
    {
        "id": "msg-peace-2",
        "conversation_id": "conv-peace",
        "user_id": "guest",
        "role": "bot",
        "content": "You made it through the day. Let your shoulders soften a little. You don't have to carry anything else right now.",
        "detected_emotion": "tired",
        "emotion_confidence": 0.85,
        "emotion_intensity": 0.5,
        "safety_level": "NORMAL",
        "created_at": datetime.now().isoformat()
    }
]
_memory_user_preferences: Dict[str, Dict[str, Any]] = {
    "guest": {
        "user_id": "guest",
        "preferred_theme": "General Support",
        "preferred_content_type": "all",
        "updated_at": datetime.now().isoformat()
    }
}

_db_offline_until: float = 0.0

@contextmanager
def get_db():
    """
    Context manager that yields a psycopg connection to Neon PostgreSQL.
    Automatically closes on exit and commits on success.
    Yields None if DATABASE_URL is not configured or connection fails.
    """
    global _db_offline_until
    import time

    if os.getenv("TESTING") == "1" or os.getenv("PYTEST_CURRENT_TEST") or not DATABASE_URL or psycopg is None or time.time() < _db_offline_until:
        yield None
        return

    conn = None
    try:
        if PSYCOPG_V3:
            conn = psycopg.connect(DATABASE_URL, row_factory=dict_row, connect_timeout=3)
        else:
            conn = psycopg.connect(DATABASE_URL, cursor_factory=RealDictCursor, connect_timeout=3)
        yield conn
        conn.commit()
    except Exception as e:
        if conn:
            try:
                conn.rollback()
            except Exception:
                pass
        # If connection failed (e.g., sandbox offline or bad network), mark offline for 30s to avoid repeated blocking
        _db_offline_until = time.time() + 30.0
        logger.warning(f"Neon database operation error: {e}. Using in-memory fallback.")
        yield None
    finally:
        if conn:
            try:
                conn.close()
            except Exception:
                pass

def _serialize_row(row: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """Converts datetime objects inside a database row to ISO strings."""
    if not row:
        return row
    res = dict(row)
    for k, v in res.items():
        if isinstance(v, datetime):
            res[k] = v.isoformat()
    return res

def _serialize_rows(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    return [_serialize_row(r) for r in rows if r]


def check_database_connectivity() -> Dict[str, Any]:
    """
    Checks database availability and connectivity without exposing credentials,
    connection strings, or sensitive infrastructure details.
    Returns safe, structured status information.
    """
    if os.getenv("TESTING") == "1":
        return {"status": "connected", "type": "in_memory"}

    if not DATABASE_URL or psycopg is None:
        return {"status": "connected", "type": "in_memory"}

    try:
        with get_db() as conn:
            if conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT 1;")
                return {"status": "connected", "type": "postgresql"}
            else:
                return {"status": "connected", "type": "in_memory_fallback"}
    except Exception as e:
        logger.warning(f"Database connectivity check failed: {e}")
        return {"status": "error", "type": "unknown"}


# --- Empathy Profile Operations ---

def save_empathy_profile(profile: EmpathyProfile) -> Dict[str, Any]:
    data = profile.model_dump()
    user_id = profile.user_id or "guest"
    data["user_id"] = user_id

    with get_db() as conn:
        if conn:
            try:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        INSERT INTO empathy_profiles (
                            user_id, total_empathy_score, emotional_empathy_score,
                            cognitive_empathy_score, dispersion_score, consistency_level,
                            profile_type, emotional_style, cognitive_style,
                            communication_style, preferred_pacing, updated_at
                        ) VALUES (
                            %(user_id)s, %(total_empathy_score)s, %(emotional_empathy_score)s,
                            %(cognitive_empathy_score)s, %(dispersion_score)s, %(consistency_level)s,
                            %(profile_type)s, %(emotional_style)s, %(cognitive_style)s,
                            %(communication_style)s, %(preferred_pacing)s, NOW()
                        )
                        ON CONFLICT (user_id) DO UPDATE SET
                            total_empathy_score = EXCLUDED.total_empathy_score,
                            emotional_empathy_score = EXCLUDED.emotional_empathy_score,
                            cognitive_empathy_score = EXCLUDED.cognitive_empathy_score,
                            dispersion_score = EXCLUDED.dispersion_score,
                            consistency_level = EXCLUDED.consistency_level,
                            profile_type = EXCLUDED.profile_type,
                            emotional_style = EXCLUDED.emotional_style,
                            cognitive_style = EXCLUDED.cognitive_style,
                            communication_style = EXCLUDED.communication_style,
                            preferred_pacing = EXCLUDED.preferred_pacing,
                            updated_at = NOW()
                        RETURNING *;
                        """,
                        data
                    )
                    row = cur.fetchone()
                    if row:
                        return _serialize_row(row)
            except Exception as e:
                logger.warning(f"Error saving empathy profile to Neon: {e}")

    _memory_empathy_profiles[user_id] = data
    return data

def get_empathy_profile(user_id: str = "guest") -> Optional[Dict[str, Any]]:
    target_user = user_id or "guest"
    with get_db() as conn:
        if conn:
            try:
                with conn.cursor() as cur:
                    cur.execute("SELECT * FROM empathy_profiles WHERE user_id = %s;", (target_user,))
                    row = cur.fetchone()
                    if row:
                        return _serialize_row(row)
            except Exception as e:
                logger.warning(f"Error retrieving empathy profile from Neon: {e}")

    return _memory_empathy_profiles.get(target_user)


# --- Conversation & Message Operations ---

def create_conversation(user_id: str = "guest", title: str = "A Quiet Conversation") -> Dict[str, Any]:
    conv_id = str(uuid.uuid4())
    now_iso = datetime.now().isoformat()
    entry = {
        "id": conv_id,
        "user_id": user_id or "guest",
        "title": title or "A Quiet Conversation",
        "created_at": now_iso,
        "updated_at": now_iso
    }

    with get_db() as conn:
        if conn:
            try:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        INSERT INTO conversations (id, user_id, title, created_at, updated_at)
                        VALUES (%s, %s, %s, NOW(), NOW())
                        RETURNING *;
                        """,
                        (conv_id, entry["user_id"], entry["title"])
                    )
                    row = cur.fetchone()
                    if row:
                        return _serialize_row(row)
            except Exception as e:
                logger.warning(f"Error creating conversation in Neon: {e}")

    _memory_conversations.insert(0, entry)
    return entry

def get_conversations(user_id: str = "guest") -> List[Dict[str, Any]]:
    target_user = user_id or "guest"
    with get_db() as conn:
        if conn:
            try:
                with conn.cursor() as cur:
                    cur.execute(
                        "SELECT * FROM conversations WHERE user_id = %s ORDER BY created_at DESC;",
                        (target_user,)
                    )
                    rows = cur.fetchall()
                    if rows:
                        return _serialize_rows(rows)
            except Exception as e:
                logger.warning(f"Error fetching conversations from Neon: {e}")

    user_convs = [c for c in _memory_conversations if c.get("user_id") == target_user]
    if not user_convs and target_user != "guest":
        return [c for c in _memory_conversations if c.get("user_id") == "guest"]
    return user_convs

def delete_conversation(conversation_id: str) -> bool:
    global _memory_conversations, _memory_messages
    with get_db() as conn:
        if conn:
            try:
                with conn.cursor() as cur:
                    cur.execute("DELETE FROM messages WHERE conversation_id = %s;", (conversation_id,))
                    cur.execute("DELETE FROM conversations WHERE id = %s;", (conversation_id,))
            except Exception as e:
                logger.warning(f"Error deleting conversation from Neon: {e}")

    _memory_conversations = [c for c in _memory_conversations if c.get("id") != conversation_id]
    _memory_messages = [m for m in _memory_messages if m.get("conversation_id") != conversation_id]
    return True

def record_chat_message(
    conversation_id: str,
    user_id: str,
    role: str,
    content: str,
    detected_emotion: str = "neutral",
    emotion_confidence: float = 0.8,
    emotion_intensity: float = 0.5,
    safety_level: str = "NORMAL"
) -> Dict[str, Any]:
    msg_id = str(uuid.uuid4())
    entry = {
        "id": msg_id,
        "conversation_id": conversation_id or "default",
        "user_id": user_id or "guest",
        "role": role,
        "content": content,
        "detected_emotion": detected_emotion,
        "emotion_confidence": emotion_confidence,
        "emotion_intensity": emotion_intensity,
        "safety_level": safety_level,
        "created_at": datetime.now().isoformat()
    }

    with get_db() as conn:
        if conn:
            try:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        INSERT INTO messages (
                            id, conversation_id, user_id, role, content,
                            detected_emotion, emotion_confidence, emotion_intensity,
                            safety_level, created_at
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())
                        RETURNING *;
                        """,
                        (
                            msg_id, entry["conversation_id"], entry["user_id"],
                            role, content, detected_emotion, emotion_confidence,
                            emotion_intensity, safety_level
                        )
                    )
                    row = cur.fetchone()
                    if row:
                        return _serialize_row(row)
            except Exception as e:
                logger.warning(f"Error saving message in Neon: {e}")

    _memory_messages.append(entry)
    return entry

def get_conversation_messages(conversation_id: str = "default") -> List[Dict[str, Any]]:
    target_conv = conversation_id or "default"
    with get_db() as conn:
        if conn:
            try:
                with conn.cursor() as cur:
                    cur.execute(
                        "SELECT * FROM messages WHERE conversation_id = %s ORDER BY created_at ASC LIMIT 50;",
                        (target_conv,)
                    )
                    rows = cur.fetchall()
                    if rows:
                        return _serialize_rows(rows)
            except Exception as e:
                logger.warning(f"Error fetching messages from Neon: {e}")

    return [m for m in _memory_messages if m.get("conversation_id") == target_conv]


# --- Daily Reflection Check-Ins ---

def save_reflection(user_id: str, mood: str, note: str = "") -> Dict[str, Any]:
    ref_id = str(uuid.uuid4())
    created_str = datetime.now().strftime("%b %d · %I:%M %p")
    entry = {
        "id": ref_id,
        "user_id": user_id or "guest",
        "mood": mood,
        "note": note,
        "created_at": created_str
    }

    with get_db() as conn:
        if conn:
            try:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        INSERT INTO reflections (id, user_id, mood, note, created_at)
                        VALUES (%s, %s, %s, %s, %s)
                        RETURNING *;
                        """,
                        (ref_id, entry["user_id"], mood, note, created_str)
                    )
                    row = cur.fetchone()
                    if row:
                        return _serialize_row(row)
            except Exception as e:
                logger.warning(f"Error saving reflection to Neon: {e}")

    _memory_reflections.insert(0, entry)
    return entry

def get_reflections(user_id: str = "guest") -> List[Dict[str, Any]]:
    with get_db() as conn:
        if conn:
            try:
                with conn.cursor() as cur:
                    cur.execute(
                        "SELECT * FROM reflections ORDER BY created_at DESC LIMIT 20;"
                    )
                    rows = cur.fetchall()
                    if rows:
                        return _serialize_rows(rows)
            except Exception as e:
                logger.warning(f"Error fetching reflections from Neon: {e}")

    return _memory_reflections


# --- Favorites ---

def toggle_favorite(user_id: str, title: str, item_type: str = "book") -> bool:
    target_user = user_id or "guest"
    with get_db() as conn:
        if conn:
            try:
                with conn.cursor() as cur:
                    cur.execute(
                        "SELECT * FROM favorites WHERE title = %s AND user_id = %s;",
                        (title, target_user)
                    )
                    existing = cur.fetchone()
                    if existing:
                        cur.execute(
                            "DELETE FROM favorites WHERE title = %s AND user_id = %s;",
                            (title, target_user)
                        )
                        return False
                    else:
                        cur.execute(
                            "INSERT INTO favorites (id, user_id, title, item_type) VALUES (%s, %s, %s, %s);",
                            (str(uuid.uuid4()), target_user, title, item_type)
                        )
                        return True
            except Exception as e:
                logger.warning(f"Error toggling favorite in Neon: {e}")

    for i, fav in enumerate(_memory_favorites):
        if fav.get("title") == title and fav.get("user_id") == target_user:
            _memory_favorites.pop(i)
            return False
    _memory_favorites.append({"title": title, "item_type": item_type, "user_id": target_user})
    return True

def get_favorites(user_id: str = "guest") -> List[str]:
    target_user = user_id or "guest"
    with get_db() as conn:
        if conn:
            try:
                with conn.cursor() as cur:
                    cur.execute("SELECT title FROM favorites WHERE user_id = %s;", (target_user,))
                    rows = cur.fetchall()
                    if rows:
                        return [r["title"] for r in rows]
            except Exception as e:
                logger.warning(f"Error fetching favorites from Neon: {e}")

    return [fav["title"] for fav in _memory_favorites if fav.get("user_id") == target_user]


# --- User Preferences ---

def get_user_preferences(user_id: str = "guest") -> Dict[str, Any]:
    target_user = user_id or "guest"
    with get_db() as conn:
        if conn:
            try:
                with conn.cursor() as cur:
                    cur.execute("SELECT * FROM user_preferences WHERE user_id = %s;", (target_user,))
                    row = cur.fetchone()
                    if row:
                        return _serialize_row(row)
            except Exception as e:
                logger.warning(f"Error getting user preferences from Neon: {e}")

    return _memory_user_preferences.get(target_user, {
        "user_id": target_user,
        "preferred_theme": "General Support",
        "preferred_content_type": "all",
        "updated_at": datetime.now().isoformat()
    })

def update_user_preferences(user_id: str = "guest", theme: str = None, content_type: str = None) -> Dict[str, Any]:
    target_user = user_id or "guest"
    current = get_user_preferences(target_user)
    if theme:
        current["preferred_theme"] = theme
    if content_type:
        current["preferred_content_type"] = content_type
    current["updated_at"] = datetime.now().isoformat()

    with get_db() as conn:
        if conn:
            try:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        INSERT INTO user_preferences (user_id, preferred_theme, preferred_content_type, updated_at)
                        VALUES (%s, %s, %s, NOW())
                        ON CONFLICT (user_id) DO UPDATE SET
                            preferred_theme = EXCLUDED.preferred_theme,
                            preferred_content_type = EXCLUDED.preferred_content_type,
                            updated_at = NOW()
                        RETURNING *;
                        """,
                        (target_user, current.get("preferred_theme"), current.get("preferred_content_type"))
                    )
                    row = cur.fetchone()
                    if row:
                        return _serialize_row(row)
            except Exception as e:
                logger.warning(f"Error updating preferences in Neon: {e}")

    _memory_user_preferences[target_user] = current
    return current


# --- Emergency Contacts & Telegram Safety Circle ---

def save_emergency_contact(
    user_id: str,
    name: str,
    phone: Optional[str] = "",
    relationship: str = "Family / Friend"
) -> Dict[str, Any]:
    target_user = user_id or "guest"
    now_iso = datetime.now(timezone.utc).isoformat()
    
    # Check existing memory record to preserve telegram status and chat_id
    existing = _memory_emergency_contacts.get(target_user, {})
    record = {
        "user_id": target_user,
        "name": name.strip(),
        "phone": (phone or "").strip(),
        "relationship": (relationship or "Family / Friend").strip(),
        "telegram_chat_id": existing.get("telegram_chat_id"),
        "telegram_username": existing.get("telegram_username"),
        "telegram_status": existing.get("telegram_status") or "NOT_CONNECTED",
        "pairing_code_hash": existing.get("pairing_code_hash"),
        "pairing_code_expires_at": existing.get("pairing_code_expires_at"),
        "connected_at": existing.get("connected_at"),
        "consent_at": existing.get("consent_at"),
        "created_at": existing.get("created_at") or now_iso,
        "updated_at": now_iso,
    }

    with get_db() as conn:
        if conn:
            try:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        INSERT INTO emergency_contacts (
                            user_id, name, phone, relationship, telegram_status, created_at, updated_at
                        )
                        VALUES (%s, %s, %s, %s, COALESCE(%s, 'NOT_CONNECTED'), NOW(), NOW())
                        ON CONFLICT (user_id) DO UPDATE SET
                            name = EXCLUDED.name,
                            phone = EXCLUDED.phone,
                            relationship = EXCLUDED.relationship,
                            updated_at = NOW()
                        RETURNING *;
                        """,
                        (record["user_id"], record["name"], record["phone"], record["relationship"], record["telegram_status"])
                    )
                    row = cur.fetchone()
                    if row:
                        serialized = _serialize_row(row)
                        _memory_emergency_contacts[target_user] = serialized
                        return serialized
            except Exception as e:
                logger.warning(f"Error saving emergency contact to Neon: {e}")

    _memory_emergency_contacts[target_user] = record
    return record


def get_emergency_contact(user_id: str = "guest") -> Optional[Dict[str, Any]]:
    target_user = user_id or "guest"
    with get_db() as conn:
        if conn:
            try:
                with conn.cursor() as cur:
                    cur.execute("SELECT * FROM emergency_contacts WHERE user_id = %s;", (target_user,))
                    row = cur.fetchone()
                    if row:
                        serialized = _serialize_row(row)
                        _memory_emergency_contacts[target_user] = serialized
                        return serialized
            except Exception as e:
                logger.warning(f"Error fetching emergency contact from Neon: {e}")

    return _memory_emergency_contacts.get(target_user)


def generate_contact_pairing_code(
    user_id: str = "guest",
    name: Optional[str] = None,
    phone: Optional[str] = "",
    relationship: Optional[str] = "Family / Friend",
    user_name: Optional[str] = None
) -> Dict[str, Any]:
    """
    Generates a cryptographically random, 8-character, 10-minute pairing code.
    Stores the SHA-256 hash in database rather than plaintext.
    Returns the plain code and expiry for sharing via deep link.
    """
    target_user = user_id or "guest"
    now_utc = datetime.now(timezone.utc)
    expires_at = now_utc + timedelta(minutes=10)

    # Cryptographically secure random 8-character code
    plain_code = secrets.token_hex(4).upper()
    code_hash = hashlib.sha256(plain_code.encode("utf-8")).hexdigest()

    existing = get_emergency_contact(target_user) or {}
    contact_name = (name or existing.get("name") or "Emergency Contact").strip()
    contact_phone = (phone if phone is not None else existing.get("phone", "")).strip()
    contact_rel = (relationship or existing.get("relationship") or "Family / Friend").strip()
    user_display = (user_name or existing.get("user_name") or get_user_display_name(target_user) or "Mitwa Ninama").strip()

    record = {
        "user_id": target_user,
        "name": contact_name,
        "phone": contact_phone,
        "relationship": contact_rel,
        "user_name": user_display,
        "telegram_chat_id": existing.get("telegram_chat_id"),
        "telegram_username": existing.get("telegram_username"),
        "telegram_status": "PENDING" if existing.get("telegram_status") != "CONNECTED" else "CONNECTED",
        "pairing_code_hash": code_hash,
        "pairing_code_expires_at": expires_at.isoformat(),
        "connected_at": existing.get("connected_at"),
        "consent_at": existing.get("consent_at"),
        "created_at": existing.get("created_at") or now_utc.isoformat(),
        "updated_at": now_utc.isoformat(),
    }

    with get_db() as conn:
        if conn:
            try:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        INSERT INTO emergency_contacts (
                            user_id, name, phone, relationship, user_name, telegram_status,
                            pairing_code_hash, pairing_code_expires_at, created_at, updated_at
                        )
                        VALUES (%s, %s, %s, %s, %s, 'PENDING', %s, %s, NOW(), NOW())
                        ON CONFLICT (user_id) DO UPDATE SET
                            name = EXCLUDED.name,
                            phone = EXCLUDED.phone,
                            relationship = EXCLUDED.relationship,
                            user_name = EXCLUDED.user_name,
                            pairing_code_hash = EXCLUDED.pairing_code_hash,
                            pairing_code_expires_at = EXCLUDED.pairing_code_expires_at,
                            telegram_status = CASE 
                                WHEN emergency_contacts.telegram_status = 'CONNECTED' THEN 'CONNECTED' 
                                ELSE 'PENDING' 
                            END,
                            updated_at = NOW()
                        RETURNING *;
                        """,
                        (target_user, contact_name, contact_phone, contact_rel, user_display, code_hash, expires_at)
                    )
                    row = cur.fetchone()
                    if row:
                        serialized = _serialize_row(row)
                        _memory_emergency_contacts[target_user] = serialized
            except Exception as e:
                logger.warning(f"Error persisting pairing code to Neon: {e}")

    _memory_emergency_contacts[target_user] = record
    return {
        "success": True,
        "pairing_code": plain_code,
        "expires_at": expires_at.isoformat(),
        "expires_in_seconds": 600,
        "status": record["telegram_status"]
    }


def pair_contact_telegram(
    pairing_code: str,
    chat_id: str,
    telegram_username: Optional[str] = None
) -> Dict[str, Any]:
    """
    Validates pairing code hash and expiry.
    If valid, associates telegram_chat_id, updates status to CONNECTED,
    records consent timestamp, and invalidates the code for single-use security.
    """
    clean_code = pairing_code.strip()
    code_hash = hashlib.sha256(clean_code.encode("utf-8")).hexdigest()
    now_utc = datetime.now(timezone.utc)

    # 1. Check Neon PostgreSQL
    with get_db() as conn:
        if conn:
            try:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        SELECT * FROM emergency_contacts 
                        WHERE pairing_code_hash = %s;
                        """,
                        (code_hash,)
                    )
                    row = cur.fetchone()
                    if row:
                        serialized = _serialize_row(row)
                        exp_str = serialized.get("pairing_code_expires_at")
                        if exp_str:
                            try:
                                exp_dt = datetime.fromisoformat(str(exp_str).replace("Z", "+00:00"))
                                if exp_dt.tzinfo is None:
                                    exp_dt = exp_dt.replace(tzinfo=timezone.utc)
                                if now_utc > exp_dt:
                                    return {"success": False, "error": "This pairing code has expired (10-minute validity)."}
                            except Exception as parse_err:
                                logger.warning(f"Could not parse pairing expiry: {parse_err}")

                        # Update to CONNECTED and invalidate code
                        cur.execute(
                            """
                            UPDATE emergency_contacts SET
                                telegram_chat_id = %s,
                                telegram_username = %s,
                                telegram_status = 'CONNECTED',
                                connected_at = NOW(),
                                consent_at = NOW(),
                                pairing_code_hash = NULL,
                                pairing_code_expires_at = NULL,
                                updated_at = NOW()
                            WHERE user_id = %s
                            RETURNING *;
                            """,
                            (str(chat_id), telegram_username or "", serialized["user_id"])
                        )
                        updated_row = cur.fetchone()
                        updated = _serialize_row(updated_row) if updated_row else serialized
                        _memory_emergency_contacts[serialized["user_id"]] = updated
                        u_name = (
                            updated.get("user_name")
                            or serialized.get("user_name")
                            or get_user_display_name(updated["user_id"])
                        )
                        if not u_name or u_name in ("BhaavaBot User", "your loved one"):
                            u_name = "Mitwa Ninama"

                        return {
                            "success": True,
                            "user_id": updated["user_id"],
                            "contact_name": updated["name"],
                            "user_name": u_name
                        }
            except Exception as e:
                logger.warning(f"Error pairing telegram contact in Neon: {e}")

    # 2. Check In-Memory Store
    for uid, contact in _memory_emergency_contacts.items():
        if contact.get("pairing_code_hash") == code_hash:
            exp_str = contact.get("pairing_code_expires_at")
            if exp_str:
                try:
                    exp_dt = datetime.fromisoformat(str(exp_str).replace("Z", "+00:00"))
                    if exp_dt.tzinfo is None:
                        exp_dt = exp_dt.replace(tzinfo=timezone.utc)
                    if now_utc > exp_dt:
                        return {"success": False, "error": "This pairing code has expired (10-minute validity)."}
                except Exception:
                    pass

            contact["telegram_chat_id"] = str(chat_id)
            contact["telegram_username"] = telegram_username or ""
            contact["telegram_status"] = "CONNECTED"
            contact["connected_at"] = now_utc.isoformat()
            contact["consent_at"] = now_utc.isoformat()
            contact["pairing_code_hash"] = None
            contact["pairing_code_expires_at"] = None
            contact["updated_at"] = now_utc.isoformat()

            u_name = (
                contact.get("user_name")
                or get_user_display_name(uid)
            )
            if not u_name or u_name in ("BhaavaBot User", "your loved one"):
                u_name = "Mitwa Ninama"

            return {
                "success": True,
                "user_id": uid,
                "contact_name": contact["name"],
                "user_name": u_name
            }

    return {"success": False, "error": "Invalid pairing code. Please generate a new connection link in BhaavaBot."}


def disconnect_contact_telegram(user_id: str = "guest") -> Dict[str, Any]:
    """
    Disconnects the registered Telegram account for an emergency contact.
    """
    target_user = user_id or "guest"
    now_iso = datetime.now(timezone.utc).isoformat()

    with get_db() as conn:
        if conn:
            try:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        UPDATE emergency_contacts SET
                            telegram_chat_id = NULL,
                            telegram_username = NULL,
                            telegram_status = 'NOT_CONNECTED',
                            pairing_code_hash = NULL,
                            pairing_code_expires_at = NULL,
                            connected_at = NULL,
                            consent_at = NULL,
                            updated_at = NOW()
                        WHERE user_id = %s
                        RETURNING *;
                        """,
                        (target_user,)
                    )
                    row = cur.fetchone()
                    if row:
                        serialized = _serialize_row(row)
                        _memory_emergency_contacts[target_user] = serialized
                        return serialized
            except Exception as e:
                logger.warning(f"Error disconnecting telegram contact in Neon: {e}")

    if target_user in _memory_emergency_contacts:
        contact = _memory_emergency_contacts[target_user]
        contact["telegram_chat_id"] = None
        contact["telegram_username"] = None
        contact["telegram_status"] = "NOT_CONNECTED"
        contact["pairing_code_hash"] = None
        contact["pairing_code_expires_at"] = None
        contact["connected_at"] = None
        contact["consent_at"] = None
        contact["updated_at"] = now_iso
        return contact

    return {"user_id": target_user, "telegram_status": "NOT_CONNECTED"}


def get_user_display_name(user_id: str = "guest") -> str:
    """
    Retrieves the user's human-readable name from the database.
    Falls back gracefully to 'Mitwa Ninama' if not found or guest.
    """
    if not user_id or user_id == "guest":
        return "Mitwa Ninama"

    with get_db() as conn:
        if conn:
            try:
                with conn.cursor() as cur:
                    cur.execute('SELECT name FROM "user" WHERE id = %s;', (user_id,))
                    row = cur.fetchone()
                    if row and row.get("name"):
                        val = str(row["name"]).strip()
                        if val:
                            return val
            except Exception as e:
                logger.debug(f"Could not fetch user name: {e}")

    profile = _memory_empathy_profiles.get(user_id)
    if profile and profile.get("name"):
        return profile["name"].strip()

    return "Mitwa Ninama"


def record_emergency_alert(
    user_id: str,
    contact_name: str,
    contact_phone: str = "",
    contact_id: str = "",
    channel: str = "TELEGRAM",
    message_type: str = "CRISIS_ALERT",
    message: str = "",
    trigger_text: str = "",
    status: str = "SIMULATED",
    telegram_message_id: Optional[str] = None,
    error_details: Optional[str] = None
) -> Dict[str, Any]:
    """
    Persists an emergency alert audit record.
    Status values strictly constrained to: 'SIMULATED', 'API_ACCEPTED', 'FAILED'.
    """
    alert_id = str(uuid.uuid4())
    now_iso = datetime.now(timezone.utc).isoformat()
    alert = {
        "id": alert_id,
        "user_id": user_id or "guest",
        "contact_id": contact_id or "",
        "contact_name": contact_name,
        "contact_phone": contact_phone or "",
        "channel": channel or "TELEGRAM",
        "message_type": message_type or "CRISIS_ALERT",
        "message": message,
        "trigger_text": trigger_text,
        "status": status,
        "telegram_message_id": telegram_message_id,
        "error_details": error_details,
        "created_at": now_iso,
        "updated_at": now_iso
    }

    with get_db() as conn:
        if conn:
            try:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        INSERT INTO emergency_alerts (
                            id, user_id, contact_id, contact_name, contact_phone,
                            channel, message_type, message, trigger_text, status,
                            telegram_message_id, error_details, created_at, updated_at
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW(), NOW())
                        RETURNING *;
                        """,
                        (
                            alert_id, alert["user_id"], alert["contact_id"], alert["contact_name"], alert["contact_phone"],
                            alert["channel"], alert["message_type"], message, trigger_text, status,
                            telegram_message_id, error_details
                        )
                    )
                    row = cur.fetchone()
                    if row:
                        return _serialize_row(row)
            except Exception as e:
                # If optional columns do not exist yet in legacy table, fallback to legacy insert
                try:
                    with conn.cursor() as cur:
                        cur.execute(
                            """
                            INSERT INTO emergency_alerts (
                                id, user_id, contact_name, contact_phone, message, trigger_text, status, created_at
                            ) VALUES (%s, %s, %s, %s, %s, %s, %s, NOW())
                            RETURNING *;
                            """,
                            (alert_id, alert["user_id"], contact_name, contact_phone, message, trigger_text, status)
                        )
                        row = cur.fetchone()
                        if row:
                            return _serialize_row(row)
                except Exception as inner_e:
                    logger.warning(f"Error recording emergency alert to Neon: {inner_e}")

    _memory_emergency_alerts.insert(0, alert)
    return alert


def get_emergency_alerts(user_id: Optional[str] = None) -> List[Dict[str, Any]]:
    with get_db() as conn:
        if conn:
            try:
                with conn.cursor() as cur:
                    if user_id:
                        cur.execute("SELECT * FROM emergency_alerts WHERE user_id = %s ORDER BY created_at DESC;", (user_id,))
                    else:
                        cur.execute("SELECT * FROM emergency_alerts ORDER BY created_at DESC;")
                    rows = cur.fetchall()
                    if rows:
                        return _serialize_rows(rows)
            except Exception as e:
                logger.warning(f"Error fetching emergency alerts from Neon: {e}")

    if user_id:
        return [a for a in _memory_emergency_alerts if a.get("user_id") == user_id]
    return _memory_emergency_alerts


def is_telegram_update_processed(update_id: int) -> bool:
    """Checks whether this update_id was already handled to guarantee idempotency."""
    if update_id in _memory_processed_telegram_updates:
        return True

    with get_db() as conn:
        if conn:
            try:
                with conn.cursor() as cur:
                    cur.execute(
                        "SELECT 1 FROM telegram_processed_updates WHERE update_id = %s;",
                        (update_id,)
                    )
                    return cur.fetchone() is not None
            except Exception:
                pass
    return False


def record_telegram_update_processed(update_id: int) -> None:
    """Marks update_id as processed in database and in-memory set."""
    _memory_processed_telegram_updates.add(update_id)

    with get_db() as conn:
        if conn:
            try:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        INSERT INTO telegram_processed_updates (update_id, processed_at)
                        VALUES (%s, NOW())
                        ON CONFLICT (update_id) DO NOTHING;
                        """,
                        (update_id,)
                    )
            except Exception:
                pass


# --- Curated Books & Sacred Texts ---

def seed_initial_books() -> int:
    """
    Idempotently seeds the 5 initial sacred texts / books into PostgreSQL/Neon books table.
    Uses ON CONFLICT (title) DO UPDATE to guarantee zero duplicates.
    Returns the count of seeded/ensured books.
    """
    count = 0
    with get_db() as conn:
        if conn:
            try:
                with conn.cursor() as cur:
                    cur.execute("""
                        CREATE TABLE IF NOT EXISTS books (
                            id TEXT PRIMARY KEY,
                            title TEXT NOT NULL UNIQUE,
                            author TEXT NOT NULL,
                            tradition TEXT,
                            category TEXT,
                            kind TEXT NOT NULL,
                            language TEXT DEFAULT 'English',
                            description TEXT,
                            pages TEXT,
                            year TEXT,
                            icon TEXT DEFAULT 'book',
                            tone TEXT DEFAULT 'peach',
                            cover_image_url TEXT,
                            reading_url TEXT,
                            url TEXT,
                            source_name TEXT DEFAULT 'Project Gutenberg',
                            source TEXT DEFAULT 'Project Gutenberg',
                            license TEXT DEFAULT 'Public Domain',
                            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                            updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
                        );
                    """)
                    for b in CURATED_BOOKS:
                        cur.execute("""
                            INSERT INTO books (
                                id, title, author, tradition, category, kind, language,
                                description, pages, year, icon, tone, cover_image_url,
                                reading_url, url, source_name, source, license, updated_at
                            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())
                            ON CONFLICT (title) DO UPDATE SET
                                reading_url = EXCLUDED.reading_url,
                                url = EXCLUDED.url,
                                description = EXCLUDED.description,
                                tradition = EXCLUDED.tradition,
                                category = EXCLUDED.category,
                                language = EXCLUDED.language,
                                cover_image_url = EXCLUDED.cover_image_url,
                                source_name = EXCLUDED.source_name,
                                license = EXCLUDED.license,
                                updated_at = NOW();
                        """, (
                            b.id, b.title, b.author, b.tradition, b.category, b.kind, b.language,
                            b.description, b.pages, b.year, b.icon, b.tone, b.cover_image_url,
                            b.reading_url or b.url, b.url or b.reading_url, b.source_name or b.source,
                            b.source, b.license
                        ))
                        count += 1
                    conn.commit()
                    return count
            except Exception as e:
                logger.warning(f"Error seeding books to Neon: {e}")
    return len(_memory_books)


def get_books(category: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Retrieves available books from PostgreSQL/Neon books table with in-memory fallback.
    Filters by tradition, category, or kind if category is provided and not 'For you'.
    """
    db_books = []
    with get_db() as conn:
        if conn:
            try:
                with conn.cursor() as cur:
                    cur.execute("""
                        CREATE TABLE IF NOT EXISTS books (
                            id TEXT PRIMARY KEY,
                            title TEXT NOT NULL UNIQUE,
                            author TEXT NOT NULL,
                            tradition TEXT,
                            category TEXT,
                            kind TEXT NOT NULL,
                            language TEXT DEFAULT 'English',
                            description TEXT,
                            pages TEXT,
                            year TEXT,
                            icon TEXT DEFAULT 'book',
                            tone TEXT DEFAULT 'peach',
                            cover_image_url TEXT,
                            reading_url TEXT,
                            url TEXT,
                            source_name TEXT DEFAULT 'Project Gutenberg',
                            source TEXT DEFAULT 'Project Gutenberg',
                            license TEXT DEFAULT 'Public Domain',
                            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                            updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
                        );
                    """)
                    cur.execute("SELECT * FROM books ORDER BY created_at ASC;")
                    rows = cur.fetchall()
                    if rows:
                        db_books = _serialize_rows(rows)
                    else:
                        # Auto-seed on empty table
                        seed_initial_books()
                        cur.execute("SELECT * FROM books ORDER BY created_at ASC;")
                        rows = cur.fetchall()
                        if rows:
                            db_books = _serialize_rows(rows)
            except Exception as e:
                logger.warning(f"Error fetching books from Neon: {e}")

    items = db_books if db_books else _memory_books

    if category and category.lower() not in ("for you", "all"):
        cat_low = category.lower().strip()
        filtered = []
        for item in items:
            kind_str = (item.get("kind") or "").lower()
            tradition_str = (item.get("tradition") or "").lower()
            category_str = (item.get("category") or "").lower()
            desc_str = (item.get("description") or "").lower()
            title_str = (item.get("title") or "").lower()
            if (
                cat_low in tradition_str
                or cat_low in category_str
                or cat_low in kind_str
                or cat_low in desc_str
                or cat_low in title_str
            ):
                filtered.append(item)
        return filtered

    return items


# --- Curated Audio Tracks & Soundscapes ---

def seed_initial_audio() -> int:
    """
    Idempotently seeds the 10 initial audio soundscapes into PostgreSQL/Neon audio_tracks table.
    Uses ON CONFLICT (title) DO UPDATE to guarantee zero duplicates.
    Returns the count of seeded/ensured audio tracks.
    """
    count = 0
    with get_db() as conn:
        if conn:
            try:
                with conn.cursor() as cur:
                    cur.execute("""
                        CREATE TABLE IF NOT EXISTS audio_tracks (
                            id TEXT PRIMARY KEY,
                            title TEXT NOT NULL UNIQUE,
                            artist TEXT NOT NULL,
                            kind TEXT,
                            category TEXT,
                            icon TEXT,
                            tone TEXT,
                            source TEXT,
                            license TEXT,
                            attribution TEXT,
                            url TEXT,
                            audio_url TEXT,
                            duration_seconds INTEGER,
                            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                            updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
                        );
                    """)
                    for m in CURATED_MUSIC:
                        cur.execute("""
                            INSERT INTO audio_tracks (
                                id, title, artist, kind, category, icon, tone,
                                source, license, attribution, url, audio_url, duration_seconds, updated_at
                            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())
                            ON CONFLICT (title) DO UPDATE SET
                                artist = EXCLUDED.artist,
                                kind = EXCLUDED.kind,
                                category = EXCLUDED.category,
                                icon = EXCLUDED.icon,
                                tone = EXCLUDED.tone,
                                source = EXCLUDED.source,
                                license = EXCLUDED.license,
                                attribution = EXCLUDED.attribution,
                                url = EXCLUDED.url,
                                audio_url = EXCLUDED.audio_url,
                                duration_seconds = EXCLUDED.duration_seconds,
                                updated_at = NOW();
                        """, (
                            m.id, m.title, m.artist, m.kind, m.category, m.icon, m.tone,
                            m.source, m.license, m.attribution, m.url, m.audio_url, m.duration_seconds
                        ))
                        count += 1
                    conn.commit()
                    return count
            except Exception as e:
                logger.warning(f"Error seeding audio tracks to Neon: {e}")
    return len(_memory_music)


def get_audio_tracks(category: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Retrieves available audio tracks from PostgreSQL/Neon audio_tracks table with in-memory fallback.
    Filters by category or kind if category is provided and not 'For you'.
    """
    db_tracks = []
    with get_db() as conn:
        if conn:
            try:
                with conn.cursor() as cur:
                    cur.execute("""
                        CREATE TABLE IF NOT EXISTS audio_tracks (
                            id TEXT PRIMARY KEY,
                            title TEXT NOT NULL UNIQUE,
                            artist TEXT NOT NULL,
                            kind TEXT,
                            category TEXT,
                            icon TEXT,
                            tone TEXT,
                            source TEXT,
                            license TEXT,
                            attribution TEXT,
                            url TEXT,
                            audio_url TEXT,
                            duration_seconds INTEGER,
                            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
                            updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
                        );
                    """)
                    cur.execute("SELECT * FROM audio_tracks ORDER BY created_at ASC;")
                    rows = cur.fetchall()
                    if rows:
                        db_tracks = _serialize_rows(rows)
                    else:
                        seed_initial_audio()
                        cur.execute("SELECT * FROM audio_tracks ORDER BY created_at ASC;")
                        rows = cur.fetchall()
                        if rows:
                            db_tracks = _serialize_rows(rows)
            except Exception as e:
                logger.warning(f"Error fetching audio tracks from Neon: {e}")

    items = db_tracks if db_tracks else _memory_music

    if category and category.lower() not in ("for you", "all"):
        cat_low = category.lower().strip()
        filtered = []
        for item in items:
            kind_str = (item.get("kind") or "").lower()
            category_str = (item.get("category") or "").lower()
            title_str = (item.get("title") or "").lower()
            if cat_low in category_str or cat_low in kind_str or cat_low in title_str:
                filtered.append(item)
        return filtered

    return items
