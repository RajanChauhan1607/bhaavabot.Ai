"""
Comprehensive Automated Test Suite for BhaavaBot Telegram Emergency Contact & Crisis Alerts.
Covers all 18 requirements:
1. Telegram configuration validation.
2. Simulation mode.
3. Successful Telegram API response.
4. Invalid bot token.
5. Invalid chat ID.
6. Blocked bot/user.
7. Network timeout.
8. Telegram rate limiting.
9. Pairing code generation.
10. Expired pairing code.
11. Reused pairing code.
12. Invalid pairing code.
13. Successful emergency contact pairing.
14. Webhook secret validation.
15. Duplicate webhook update handling.
16. Crisis notification integration.
17. Telegram API failure without interruption of crisis guidance.
18. Accurate notification status reporting.
"""

import os
os.environ["TESTING"] = "1"

import pytest
from unittest.mock import patch
from datetime import datetime, timedelta, timezone
from fastapi import HTTPException

from app.main import (
    app,
    create_pairing_code_endpoint,
    disconnect_emergency_contact_endpoint,
    chat_endpoint,
    telegram_webhook_endpoint
)
from app.models.schemas import PairingCodeRequest, ChatRequest
from app.core.config import settings
from app.services.telegram_service import (
    validate_telegram_configuration,
    get_bot_info,
    send_telegram_message,
    send_crisis_telegram,
    send_test_telegram,
    process_telegram_update
)
from app.database import (
    save_emergency_contact,
    get_emergency_contact,
    generate_contact_pairing_code,
    pair_contact_telegram,
    disconnect_contact_telegram,
    get_emergency_alerts,
    _memory_emergency_contacts,
    _memory_emergency_alerts,
    _memory_processed_telegram_updates
)

def _run_sync(coro):
    """Executes a coroutine directly without spinning up an OS socket loop."""
    try:
        coro.send(None)
    except StopIteration as e:
        return e.value


@pytest.fixture(autouse=True)
def clean_memory_state():
    """Reset in-memory storage before each test for clean isolation."""
    _memory_emergency_contacts.clear()
    _memory_emergency_alerts.clear()
    _memory_processed_telegram_updates.clear()
    settings.TELEGRAM_MODE = "simulation"
    settings.TELEGRAM_BOT_TOKEN = "123456789:ABCdefGHIjklMNOpqrsTUVwxyz"
    settings.TELEGRAM_BOT_USERNAME = "BhaavaBotSafetyBot"
    settings.TELEGRAM_WEBHOOK_SECRET = "test-webhook-secret"
    yield


# 1. Telegram configuration validation
def test_telegram_configuration_validation():
    conf = validate_telegram_configuration()
    assert conf["mode"] == "simulation"
    assert conf["is_configured"] is True
    assert conf["has_token"] is True
    assert conf["bot_username"] == "BhaavaBotSafetyBot"
    assert conf["has_webhook_secret"] is True


# 2. Simulation mode behavior
def test_telegram_simulation_mode():
    res = _run_sync(send_telegram_message(
        chat_id="999888777",
        message="Test alert",
        message_type="CRISIS_ALERT",
        user_id="user_sim",
        contact_name="Sarah"
    ))
    assert res["success"] is True
    assert res["status"] == "SIMULATED"
    assert res["channel"] == "TELEGRAM"
    assert res["error"] is None

    # Audit trail verification
    alerts = get_emergency_alerts("user_sim")
    assert len(alerts) > 0
    assert alerts[0]["status"] == "SIMULATED"
    assert alerts[0]["channel"] == "TELEGRAM"


# 3. Successful Telegram API response in Live mode
def test_successful_telegram_api_response():
    settings.TELEGRAM_MODE = "live"
    with patch("app.services.telegram_service._send_http_request", return_value=(200, {
        "ok": True,
        "result": {"message_id": 4321, "text": "Urgent alert"}
    })):
        res = _run_sync(send_telegram_message(
            chat_id="123456789",
            message="Urgent alert",
            user_id="user_live",
            contact_name="Dad"
        ))
        assert res["success"] is True
        assert res["status"] == "API_ACCEPTED"
        assert res["message_id"] == "4321"
        assert res["error"] is None


# 4. Invalid bot token
def test_invalid_bot_token():
    settings.TELEGRAM_MODE = "live"
    with patch("app.services.telegram_service._send_http_request", return_value=(401, {
        "ok": False,
        "error_code": 401,
        "description": "Unauthorized: invalid bot token"
    })):
        res = _run_sync(send_telegram_message(
            chat_id="123456789",
            message="Alert",
            user_id="user_token_err"
        ))
        assert res["success"] is False
        assert res["status"] == "FAILED"
        assert "401" in res["error"]


# 5. Invalid chat ID
def test_invalid_chat_id():
    # Empty chat ID
    settings.TELEGRAM_MODE = "live"
    res_empty = _run_sync(send_telegram_message(
        chat_id="",
        message="Alert",
        user_id="user_bad_chat"
    ))
    assert res_empty["success"] is False
    assert res_empty["status"] == "FAILED"
    assert "missing" in res_empty["error"]

    # Non-existent chat_id rejected by Telegram
    with patch("app.services.telegram_service._send_http_request", return_value=(400, {
        "ok": False,
        "error_code": 400,
        "description": "Bad Request: chat not found"
    })):
        res_bad = _run_sync(send_telegram_message(
            chat_id="99999999999999",
            message="Alert",
            user_id="user_bad_chat"
        ))
        assert res_bad["success"] is False
        assert res_bad["status"] == "FAILED"
        assert "Invalid chat_id" in res_bad["error"]


# 6. Blocked bot/user (HTTP 403)
def test_blocked_bot_by_user():
    settings.TELEGRAM_MODE = "live"
    with patch("app.services.telegram_service._send_http_request", return_value=(403, {
        "ok": False,
        "error_code": 403,
        "description": "Forbidden: bot was blocked by the user"
    })):
        res = _run_sync(send_telegram_message(
            chat_id="123456789",
            message="Alert",
            user_id="user_blocked"
        ))
        assert res["success"] is False
        assert res["status"] == "FAILED"
        assert "blocked by user" in res["error"]


# 7. Network timeout
def test_network_timeout():
    settings.TELEGRAM_MODE = "live"
    with patch("app.services.telegram_service._send_http_request", side_effect=TimeoutError("Telegram API request timed out after 10.0 seconds.")):
        res = _run_sync(send_telegram_message(
            chat_id="123456789",
            message="Alert",
            user_id="user_timeout"
        ))
        assert res["success"] is False
        assert res["status"] == "FAILED"
        assert "timed out" in res["error"]


# 8. Telegram rate limiting (HTTP 429)
def test_telegram_rate_limiting():
    settings.TELEGRAM_MODE = "live"
    with patch("app.services.telegram_service._send_http_request", return_value=(429, {
        "ok": False,
        "error_code": 429,
        "description": "Too Many Requests: retry after 25",
        "parameters": {"retry_after": 25}
    })):
        res = _run_sync(send_telegram_message(
            chat_id="123456789",
            message="Alert",
            user_id="user_rate"
        ))
        assert res["success"] is False
        assert res["status"] == "FAILED"
        assert "rate limit" in res["error"]


# 9. Pairing code generation
def test_pairing_code_generation():
    res = generate_contact_pairing_code(
        user_id="user_pairing_test",
        name="Brother Dave",
        relationship="Brother"
    )
    assert res["success"] is True
    assert len(res["pairing_code"]) == 8
    assert res["expires_in_seconds"] == 600
    assert res["status"] == "PENDING"

    # API Endpoint check
    api_res = _run_sync(create_pairing_code_endpoint(PairingCodeRequest(
        user_id="user_pairing_api",
        name="Sister Claire",
        relationship="Sister"
    )))
    assert api_res.success is True
    assert "https://t.me/" in api_res.pairing_link
    assert api_res.pairing_code in api_res.pairing_link


# 10. Expired pairing code rejection
def test_expired_pairing_code():
    res = generate_contact_pairing_code(user_id="user_exp", name="John")
    code = res["pairing_code"]

    # Artificially expire the code in storage
    contact = get_emergency_contact("user_exp")
    contact["pairing_code_expires_at"] = (datetime.now(timezone.utc) - timedelta(minutes=5)).isoformat()

    pair_res = pair_contact_telegram(pairing_code=code, chat_id="888777666")
    assert pair_res["success"] is False
    assert "expired" in pair_res["error"]


# 11. Reused pairing code invalidation
def test_reused_pairing_code():
    res = generate_contact_pairing_code(user_id="user_reuse", name="Maria")
    code = res["pairing_code"]

    # First use: must succeed
    pair_1 = pair_contact_telegram(pairing_code=code, chat_id="111222333")
    assert pair_1["success"] is True

    # Second use: must be rejected
    pair_2 = pair_contact_telegram(pairing_code=code, chat_id="444555666")
    assert pair_2["success"] is False
    assert "Invalid pairing code" in pair_2["error"]


# 12. Invalid pairing code
def test_invalid_pairing_code():
    pair_res = pair_contact_telegram(pairing_code="TOTALLY_BOGUS_CODE", chat_id="12345")
    assert pair_res["success"] is False
    assert "Invalid" in pair_res["error"]


# 13. Successful emergency contact pairing via /start
def test_successful_pairing_via_update():
    res = generate_contact_pairing_code(user_id="user_hook_pair", name="Elena")
    code = res["pairing_code"]

    update = {
        "update_id": 9001,
        "message": {
            "message_id": 50,
            "from": {"id": 777123, "first_name": "Elena", "username": "elena_tele"},
            "chat": {"id": 777123, "type": "private"},
            "text": f"/start {code}"
        }
    }

    result = _run_sync(process_telegram_update(update))
    assert result["status"] == "paired"
    assert result["chat_id"] == "777123"

    # Verify contact is now marked CONNECTED with chat_id
    contact = get_emergency_contact("user_hook_pair")
    assert contact["telegram_status"] == "CONNECTED"
    assert contact["telegram_chat_id"] == "777123"
    assert contact["connected_at"] is not None


# 14. Webhook secret validation
def test_webhook_secret_validation():
    settings.TELEGRAM_WEBHOOK_SECRET = "super-secret-token-xyz"

    class MockRequest:
        async def json(self):
            return {"update_id": 101, "message": {"text": "/start", "chat": {"id": 1}}}

    # Reject without header or with wrong header
    with pytest.raises(HTTPException) as exc_info:
        _run_sync(telegram_webhook_endpoint(
            request=MockRequest(),
            x_telegram_bot_api_secret_token="wrong-secret"
        ))
    assert exc_info.value.status_code == 403

    # Accept with correct header
    res_good = _run_sync(telegram_webhook_endpoint(
        request=MockRequest(),
        x_telegram_bot_api_secret_token="super-secret-token-xyz"
    ))
    assert res_good["ok"] is True


# 15. Duplicate webhook update handling (idempotency)
def test_duplicate_update_idempotency():
    update = {
        "update_id": 88888,
        "message": {
            "chat": {"id": 1234},
            "text": "/start"
        }
    }

    res1 = _run_sync(process_telegram_update(update))
    assert res1["status"] in ("welcome_sent", "unhandled_message")

    # Second pass with same update_id
    res2 = _run_sync(process_telegram_update(update))
    assert res2["status"] == "ignored"
    assert res2["reason"] == "duplicate_update"


# 16. Crisis notification integration
def test_crisis_notification_integration():
    # Register and pair contact
    save_emergency_contact("user_crisis_test", name="Aunt Susan", relationship="Aunt")
    pair_res = generate_contact_pairing_code("user_crisis_test")
    pair_contact_telegram(pair_res["pairing_code"], chat_id="999111222")

    # Express suicidal crisis
    chat_payload = ChatRequest(
        message="I want to die, I have no reason to live anymore and want to end it all.",
        user_id="user_crisis_test",
        conversation_id="conv-crisis-telegram"
    )

    data = _run_sync(chat_endpoint(chat_payload))

    assert data.safety_level == "CRISIS"
    assert data.suggested_action == "show_crisis_modal"
    assert data.emergency_alert_dispatched is True
    assert "Aunt Susan" in (data.contact_notified or "")
    assert "988" in data.reply

    # Verify audit log recorded TELEGRAM channel
    alerts = get_emergency_alerts("user_crisis_test")
    assert len(alerts) > 0
    assert alerts[0]["channel"] == "TELEGRAM"


# 17. Telegram API failure without interruption of crisis guidance
def test_crisis_guidance_uninterrupted_on_telegram_failure():
    settings.TELEGRAM_MODE = "live"
    save_emergency_contact("user_fail_test", name="Marcus")
    # Unconnected contact (no chat_id) in live mode will fail delivery
    contact = get_emergency_contact("user_fail_test")
    contact["telegram_status"] = "NOT_CONNECTED"
    contact["telegram_chat_id"] = None

    chat_payload = ChatRequest(
        message="I am thinking of killing myself tonight.",
        user_id="user_fail_test",
        conversation_id="conv-fail-test"
    )

    data = _run_sync(chat_endpoint(chat_payload))

    # User MUST still receive compassionate crisis guidance and helplines
    assert data.safety_level == "CRISIS"
    assert "988" in data.reply
    assert "Crisis Text Line" in data.reply
    # Does not falsely claim an alert was dispatched
    assert data.emergency_alert_dispatched is False


# 18. Accurate notification status reporting
def test_accurate_notification_status_reporting():
    # Disconnect endpoint test
    save_emergency_contact("user_disc", name="Laura")
    pair_res = generate_contact_pairing_code("user_disc")
    pair_contact_telegram(pair_res["pairing_code"], chat_id="555444")

    c_before = get_emergency_contact("user_disc")
    assert c_before["telegram_status"] == "CONNECTED"

    # Disconnect
    disc_res = _run_sync(disconnect_emergency_contact_endpoint({"user_id": "user_disc"}))
    assert disc_res.success is True

    c_after = get_emergency_contact("user_disc")
    assert c_after["telegram_status"] == "NOT_CONNECTED"
    assert c_after["telegram_chat_id"] is None


# 19. Ensure alert messages state Mitwa Ninama (the app user) and not Rajan (the relative)
def test_telegram_messages_address_mitwa_not_relative():
    # Setup contact named "Rajan" for app user "Mitwa Ninama"
    res = generate_contact_pairing_code(
        user_id="user_mitwa_rajan",
        name="Rajan",
        relationship="Parent",
        user_name="Mitwa Ninama"
    )
    code = res["pairing_code"]

    update = {
        "update_id": 99912,
        "message": {
            "message_id": 101,
            "from": {"id": 888999, "first_name": "Rajan", "username": "rajan_parent"},
            "chat": {"id": 888999, "type": "private"},
            "text": f"/start {code}"
        }
    }

    result = _run_sync(process_telegram_update(update))
    assert result["status"] == "paired"
    assert result["contact_name"] == "Rajan"

    contact = get_emergency_contact("user_mitwa_rajan")
    assert contact["telegram_status"] == "CONNECTED"
    assert contact["user_name"] == "Mitwa Ninama"

    # Test crisis alert dispatch content
    crisis_res = _run_sync(send_crisis_telegram(contact=contact, user_name="Mitwa Ninama"))
    assert crisis_res["success"] is True
    # Verify crisis message body contains Mitwa Ninama as the protected loved one
    alerts = get_emergency_alerts("user_mitwa_rajan")
    crisis_alert = [a for a in alerts if a["message_type"] == "CRISIS_ALERT"][-1]
    assert "Mitwa Ninama" in crisis_alert["message"]
    assert "Rajan" not in crisis_alert["message"].split("loved one (")[1].split(")")[0]

    # Test diagnostic message content
    test_res = _run_sync(send_test_telegram(contact=contact, user_name="Mitwa Ninama"))
    assert test_res["success"] is True
    alerts = get_emergency_alerts("user_mitwa_rajan")
    test_alert = [a for a in alerts if a["message_type"] == "TEST"][-1]
    assert "Mitwa Ninama" in test_alert["message"]

