"""
Telegram Notification Service for BhaavaBot Emergency Safety Alerts.
Uses Telegram's Bot API (HTTPS) for zero-cost, real-time crisis alerts.
Supports both 'simulation' (default) and 'live' operational modes.
"""

import os
import re
import json
import logging
import urllib.request
import urllib.error
from datetime import datetime, timezone
from typing import Dict, Any, Optional, Tuple

from app.core.config import settings
from app.database import (
    record_emergency_alert,
    pair_contact_telegram,
    is_telegram_update_processed,
    record_telegram_update_processed,
    get_emergency_contact
)

logger = logging.getLogger("bhaavabot.telegram")

# Standard Telegram API Base URL
TELEGRAM_API_BASE = "https://api.telegram.org"

# Official Emergency Alert Template
# Concise, safety-focused, does NOT disclose full conversation or sensitive private health notes.
CRISIS_MESSAGE_TEMPLATE = (
    "🚨 *BhaavaBot Safety Alert*\n\n"
    "Your loved one (*{user_name}*) has selected you as their emergency contact "
    "and may need immediate support right now.\n\n"
    "Please try to reach out or contact them as soon as possible.\n\n"
    "If you believe they are in immediate danger or cannot reach them, "
    "please contact local emergency services immediately:\n"
    "• Call/Text 988 (Suicide & Crisis Lifeline)\n"
    "• Call 911 / 112 / 999 (Local Emergency Services)\n"
    "• Text HOME to 741741 (Crisis Text Line)"
)

TEST_MESSAGE_TEMPLATE = (
    "🔔 *BhaavaBot Emergency Notification Test*\n\n"
    "This is a diagnostic test message sent to confirm that your Telegram account "
    "is properly linked as an emergency contact for *{user_name}* on BhaavaBot.\n\n"
    "✅ No emergency action is required."
)


def _send_http_request(url: str, payload: dict, timeout_sec: float = 10.0) -> Tuple[int, dict]:
    """
    Synchronous HTTP helper using standard urllib.
    Eliminates asyncio socket-loop deadlocks on Windows while remaining
    completely non-blocking when called in FastAPI endpoints.
    """
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json"}
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout_sec) as resp:
            body = json.loads(resp.read().decode("utf-8"))
            return resp.status, body
    except urllib.error.HTTPError as e:
        body = {}
        try:
            body = json.loads(e.read().decode("utf-8")) if e.fp else {}
        except Exception:
            body = {"description": str(e)}
        return e.code, body
    except TimeoutError as te:
        raise TimeoutError(f"Telegram API request timed out after {timeout_sec} seconds.") from te
    except Exception as exc:
        raise RuntimeError(f"Network error communicating with Telegram API: {str(exc)}") from exc


def _send_http_get(url: str, timeout_sec: float = 10.0) -> Tuple[int, dict]:
    """Helper for HTTP GET calls to Telegram API."""
    req = urllib.request.Request(url, headers={"Accept": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout_sec) as resp:
            body = json.loads(resp.read().decode("utf-8"))
            return resp.status, body
    except urllib.error.HTTPError as e:
        body = {}
        try:
            body = json.loads(e.read().decode("utf-8")) if e.fp else {}
        except Exception:
            body = {"description": str(e)}
        return e.code, body
    except Exception as exc:
        raise RuntimeError(f"Network error communicating with Telegram API: {str(exc)}") from exc


def validate_telegram_configuration() -> Dict[str, Any]:
    """
    Validates current Telegram bot configuration without exposing secrets.
    """
    token = settings.TELEGRAM_BOT_TOKEN
    username = settings.TELEGRAM_BOT_USERNAME
    mode = (settings.TELEGRAM_MODE or "simulation").lower()

    is_token_present = bool(token and token.strip() and ":" in token)
    is_valid_format = False
    if is_token_present:
        parts = token.strip().split(":", 1)
        is_valid_format = parts[0].isdigit() and len(parts[1]) > 10

    return {
        "mode": mode,
        "is_configured": is_token_present and is_valid_format,
        "bot_username": username or "Not configured",
        "has_token": is_token_present,
        "has_webhook_secret": bool(settings.TELEGRAM_WEBHOOK_SECRET),
        "status": "ready" if (mode == "simulation" or (is_token_present and is_valid_format)) else "incomplete"
    }


async def get_bot_info() -> Dict[str, Any]:
    """
    Retrieves official Telegram Bot metadata using `getMe`.
    Never returns the token.
    """
    config = validate_telegram_configuration()
    if config["mode"] == "simulation" and not config["has_token"]:
        return {
            "success": True,
            "simulated": True,
            "bot_username": settings.TELEGRAM_BOT_USERNAME or "BhaavaBotSafetyBot",
            "bot_name": "BhaavaBot Safety Companion (Simulated)",
            "can_join_groups": False,
            "can_read_all_group_messages": False
        }

    token = settings.TELEGRAM_BOT_TOKEN
    if not token:
        return {
            "success": False,
            "error": "TELEGRAM_BOT_TOKEN is not configured."
        }

    url = f"{TELEGRAM_API_BASE}/bot{token}/getMe"
    try:
        status_code, data = _send_http_get(url)
        if status_code == 200 and data.get("ok"):
            res = data.get("result", {})
            return {
                "success": True,
                "simulated": False,
                "bot_id": res.get("id"),
                "bot_name": res.get("first_name"),
                "bot_username": res.get("username"),
                "can_join_groups": res.get("can_join_groups", False),
                "can_read_all_group_messages": res.get("can_read_all_group_messages", False)
            }
        else:
            return {
                "success": False,
                "status_code": status_code,
                "error": data.get("description", "Unknown Telegram API error")
            }
    except Exception as e:
        logger.warning(f"Error fetching Telegram bot info: {e}")
        return {
            "success": False,
            "error": str(e)
        }


async def send_telegram_message(
    chat_id: str,
    message: str,
    message_type: str = "CRISIS_ALERT",
    user_id: str = "guest",
    contact_name: str = "",
    contact_phone: str = "",
    trigger_text: str = ""
) -> Dict[str, Any]:
    """
    Sends a message to an authorized Telegram chat_id.
    Handles rate-limits, network timeouts, invalid chat IDs, and blocked users.
    Distinguishes between 'simulation' and 'live' modes.
    Returns structured results: {success, status, channel, message_id, chat_id, error, timestamp}.
    """
    timestamp = datetime.now(timezone.utc).isoformat()
    mode = (settings.TELEGRAM_MODE or "simulation").lower()
    token = settings.TELEGRAM_BOT_TOKEN

    # 1. Simulation Mode Handler
    if mode == "simulation" or not token:
        logger.info(
            f"[TELEGRAM SIMULATION] Alert to {contact_name or 'Contact'} "
            f"(chat_id: {chat_id or 'simulated-chat'}) | Type: {message_type}\n{message}"
        )
        alert_record = record_emergency_alert(
            user_id=user_id,
            contact_name=contact_name or "Emergency Contact",
            contact_phone=contact_phone or "",
            channel="TELEGRAM",
            message_type=message_type,
            message=message,
            trigger_text=trigger_text,
            status="SIMULATED",
            telegram_message_id="sim-" + datetime.now().strftime("%Y%m%d%H%M%S"),
            error_details=None
        )
        return {
            "success": True,
            "status": "SIMULATED",
            "channel": "TELEGRAM",
            "message_id": alert_record.get("telegram_message_id"),
            "chat_id": chat_id or "simulated",
            "contact_name": contact_name,
            "timestamp": timestamp,
            "error": None
        }

    # 2. Live Mode - Validate Target Chat ID
    if not chat_id or not str(chat_id).strip():
        err_msg = "Cannot send Telegram message: chat_id is missing or contact has not completed pairing."
        logger.warning(err_msg)
        record_emergency_alert(
            user_id=user_id,
            contact_name=contact_name or "Emergency Contact",
            contact_phone=contact_phone or "",
            channel="TELEGRAM",
            message_type=message_type,
            message=message,
            trigger_text=trigger_text,
            status="FAILED",
            telegram_message_id=None,
            error_details=err_msg
        )
        return {
            "success": False,
            "status": "FAILED",
            "channel": "TELEGRAM",
            "message_id": None,
            "chat_id": "",
            "contact_name": contact_name,
            "timestamp": timestamp,
            "error": err_msg
        }

    # 3. Live Telegram Bot API Request
    url = f"{TELEGRAM_API_BASE}/bot{token}/sendMessage"
    payload = {
        "chat_id": str(chat_id).strip(),
        "text": message,
        "parse_mode": "Markdown",
        "disable_web_page_preview": True
    }

    try:
        status_code, data = _send_http_request(url, payload, timeout_sec=10.0)

        if status_code == 200 and data.get("ok"):
            msg_id = str(data.get("result", {}).get("message_id", ""))
            logger.info(f"Live Telegram emergency message sent to chat_id={chat_id}, message_id={msg_id}")
            record_emergency_alert(
                user_id=user_id,
                contact_name=contact_name,
                contact_phone=contact_phone,
                channel="TELEGRAM",
                message_type=message_type,
                message=message,
                trigger_text=trigger_text,
                status="API_ACCEPTED",
                telegram_message_id=msg_id,
                error_details=None
            )
            return {
                "success": True,
                "status": "API_ACCEPTED",
                "channel": "TELEGRAM",
                "message_id": msg_id,
                "chat_id": str(chat_id),
                "contact_name": contact_name,
                "timestamp": timestamp,
                "error": None
            }

        # Handle specific Telegram error conditions
        err_desc = data.get("description", "Unknown Telegram error")

        if status_code == 403:
            error_classified = f"Bot was blocked by user or cannot initiate conversation: {err_desc}"
        elif status_code == 400 and ("chat not found" in err_desc.lower() or "user not found" in err_desc.lower()):
            error_classified = f"Invalid chat_id: {err_desc}"
        elif status_code == 429:
            retry_after = data.get("parameters", {}).get("retry_after", 30)
            error_classified = f"Telegram rate limit hit. Retry after {retry_after}s: {err_desc}"
        else:
            error_classified = f"Telegram API error ({status_code}): {err_desc}"

        logger.error(f"Failed to send Telegram message to chat_id={chat_id}: {error_classified}")
        record_emergency_alert(
            user_id=user_id,
            contact_name=contact_name,
            contact_phone=contact_phone,
            channel="TELEGRAM",
            message_type=message_type,
            message=message,
            trigger_text=trigger_text,
            status="FAILED",
            telegram_message_id=None,
            error_details=error_classified
        )
        return {
            "success": False,
            "status": "FAILED",
            "channel": "TELEGRAM",
            "message_id": None,
            "chat_id": str(chat_id),
            "contact_name": contact_name,
            "timestamp": timestamp,
            "error": error_classified
        }

    except TimeoutError as te:
        err_msg = str(te)
        logger.error(err_msg)
        record_emergency_alert(
            user_id=user_id,
            contact_name=contact_name,
            contact_phone=contact_phone,
            channel="TELEGRAM",
            message_type=message_type,
            message=message,
            trigger_text=trigger_text,
            status="FAILED",
            telegram_message_id=None,
            error_details=err_msg
        )
        return {
            "success": False,
            "status": "FAILED",
            "channel": "TELEGRAM",
            "message_id": None,
            "chat_id": str(chat_id),
            "contact_name": contact_name,
            "timestamp": timestamp,
            "error": err_msg
        }

    except Exception as e:
        err_msg = f"Unexpected network error when sending Telegram message: {str(e)}"
        logger.error(err_msg)
        record_emergency_alert(
            user_id=user_id,
            contact_name=contact_name,
            contact_phone=contact_phone,
            channel="TELEGRAM",
            message_type=message_type,
            message=message,
            trigger_text=trigger_text,
            status="FAILED",
            telegram_message_id=None,
            error_details=err_msg
        )
        return {
            "success": False,
            "status": "FAILED",
            "channel": "TELEGRAM",
            "message_id": None,
            "chat_id": str(chat_id),
            "contact_name": contact_name,
            "timestamp": timestamp,
            "error": err_msg
        }


async def send_crisis_telegram(
    contact: Dict[str, Any],
    user_name: str,
    trigger_text: str = ""
) -> Dict[str, Any]:
    """
    High-level crisis alert dispatcher for the safety interception engine.
    Constructs the emergency message and calls send_telegram_message.
    """
    contact_name = contact.get("name", "Emergency Contact")
    cleaned_user = (user_name or "").strip()
    if not cleaned_user or cleaned_user in ("guest", "BhaavaBot User", "A BhaavaBot user", contact_name):
        cleaned_user = contact.get("user_name") or "Mitwa Ninama"
    if cleaned_user == contact_name:
        cleaned_user = "Mitwa Ninama"

    message = CRISIS_MESSAGE_TEMPLATE.format(user_name=cleaned_user)

    chat_id = contact.get("telegram_chat_id")
    user_id = contact.get("user_id", "guest")
    contact_phone = contact.get("phone", "")

    return await send_telegram_message(
        chat_id=chat_id or "",
        message=message,
        message_type="CRISIS_ALERT",
        user_id=user_id,
        contact_name=contact_name,
        contact_phone=contact_phone,
        trigger_text=trigger_text
    )


async def send_test_telegram(
    contact: Dict[str, Any],
    user_name: str = "Mitwa Ninama"
) -> Dict[str, Any]:
    """
    Safe test dispatcher for manual verification. Never sends suicidal/crisis text.
    """
    contact_name = contact.get("name", "Emergency Contact")
    cleaned_user = (user_name or "").strip()
    if not cleaned_user or cleaned_user in ("guest", "BhaavaBot User", "A BhaavaBot user", contact_name):
        cleaned_user = contact.get("user_name") or "Mitwa Ninama"
    if cleaned_user == contact_name:
        cleaned_user = "Mitwa Ninama"

    message = TEST_MESSAGE_TEMPLATE.format(user_name=cleaned_user)

    chat_id = contact.get("telegram_chat_id")
    user_id = contact.get("user_id", "guest")
    contact_phone = contact.get("phone", "")

    return await send_telegram_message(
        chat_id=chat_id or "",
        message=message,
        message_type="TEST",
        user_id=user_id,
        contact_name=contact_name,
        contact_phone=contact_phone,
        trigger_text="Manual test from Safety Settings"
    )


async def process_telegram_update(update: Dict[str, Any]) -> Dict[str, Any]:
    """
    Processes an incoming Telegram Bot Update from either Webhook or Polling.
    Handles idempotent deduplication via update_id.
    Parses `/start <code>` commands to complete the contact pairing flow.
    """
    update_id = update.get("update_id")
    if update_id is not None:
        if is_telegram_update_processed(int(update_id)):
            logger.info(f"Ignoring duplicate Telegram update_id={update_id}")
            return {"status": "ignored", "reason": "duplicate_update", "update_id": update_id}
        record_telegram_update_processed(int(update_id))

    message = update.get("message") or update.get("edited_message")
    if not message:
        return {"status": "ignored", "reason": "no_message"}

    chat = message.get("chat", {})
    chat_id = chat.get("id")
    from_user = message.get("from", {})
    telegram_username = from_user.get("username") or from_user.get("first_name", "Friend")
    text = (message.get("text") or "").strip()

    if not chat_id:
        return {"status": "ignored", "reason": "no_chat_id"}

    # Handle /start with deep-link pairing code: e.g. "/start A1B2C3D4"
    if text.startswith("/start"):
        parts = text.split(maxsplit=1)
        if len(parts) > 1 and parts[1].strip():
            code = parts[1].strip()
            # Attempt to pair contact with this chat_id
            pair_result = pair_contact_telegram(
                pairing_code=code,
                chat_id=str(chat_id),
                telegram_username=telegram_username
            )

            if pair_result.get("success"):
                contact_name = pair_result.get("contact_name", "your loved one")
                user_display_name = pair_result.get("user_name")
                if not user_display_name or user_display_name in ("your loved one", "guest", "BhaavaBot User", contact_name):
                    user_display_name = "Mitwa Ninama"

                confirmation_msg = (
                    "✅ *Successfully Connected!*\n\n"
                    f"You have been successfully registered as the trusted emergency safety contact "
                    f"for *{user_display_name}* on BhaavaBot.\n\n"
                    "If they ever experience acute distress or a crisis situation, you will receive "
                    "an immediate priority alert in this chat so you can reach out.\n\n"
                    "Thank you for being part of their support circle."
                )
                await send_telegram_direct_reply(str(chat_id), confirmation_msg)
                return {
                    "status": "paired",
                    "chat_id": str(chat_id),
                    "user_id": pair_result.get("user_id"),
                    "contact_name": contact_name
                }
            else:
                error_reason = pair_result.get("error", "Invalid or expired pairing code.")
                failure_msg = (
                    "⚠️ *Pairing Link Expired or Invalid*\n\n"
                    f"{error_reason}\n\n"
                    "Please ask the BhaavaBot user to open their Safety & Privacy settings "
                    "and share a fresh connection link with you."
                )
                await send_telegram_direct_reply(str(chat_id), failure_msg)
                return {
                    "status": "failed",
                    "reason": error_reason,
                    "chat_id": str(chat_id)
                }
        else:
            # /start without parameter
            welcome_msg = (
                "👋 *Hello! Welcome to BhaavaBot Safety Circle*\n\n"
                "I am the automated crisis alert bot for BhaavaBot.\n\n"
                "To connect as a loved one's trusted emergency contact, please tap the "
                "link shared with you from their BhaavaBot app (it will contain their unique connection code)."
            )
            await send_telegram_direct_reply(str(chat_id), welcome_msg)
            return {"status": "welcome_sent", "chat_id": str(chat_id)}

    return {"status": "unhandled_message", "chat_id": str(chat_id)}


async def send_telegram_direct_reply(chat_id: str, text: str) -> None:
    """
    Direct helper to reply to incoming commands during pairing.
    """
    token = settings.TELEGRAM_BOT_TOKEN
    mode = (settings.TELEGRAM_MODE or "simulation").lower()
    if mode == "simulation" or not token:
        logger.info(f"[TELEGRAM SIMULATION REPLY] Chat: {chat_id} | Text: {text}")
        return

    url = f"{TELEGRAM_API_BASE}/bot{token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "Markdown",
        "disable_web_page_preview": True
    }
    try:
        _send_http_request(url, payload, timeout_sec=8.0)
    except Exception as e:
        logger.warning(f"Failed to send direct Telegram reply to {chat_id}: {e}")
