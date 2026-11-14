import os
os.environ["TESTING"] = "1"

import pytest
from fastapi import HTTPException
from app.main import app, health_check, chat_endpoint
from app.models.schemas import ChatRequest

def _run_sync(coro):
    """Executes a coroutine directly without spinning up an OS socket loop."""
    try:
        coro.send(None)
    except StopIteration as e:
        return e.value
    raise RuntimeError("Coroutine did not resolve synchronously")

def test_health_check_endpoint():
    """Verify health check returns service, database, and model metadata without exposing secrets."""
    data = health_check()
    assert data["status"] == "healthy"
    assert "database" in data
    assert data["database"]["connected"] is True
    assert "gemini" in data["model"]
    # Ensure sensitive credentials are never leaked
    data_str = str(data)
    assert "password" not in data_str.lower()
    assert "postgres://" not in data_str
    assert "neon.tech" not in data_str

def test_chat_normal_flow():
    """Verify standard emotional chat generates empathetic response with detected emotion."""
    res = _run_sync(chat_endpoint(ChatRequest(
        message="I've been feeling deeply anxious about my exams lately.",
        user_id="test-chat-user"
    )))
    assert res.reply is not None
    assert len(res.reply) > 10
    assert res.detected_emotion in ["anxiety", "fear", "stress"]
    assert res.safety_level == "NORMAL"

def test_chat_crisis_interception_before_llm():
    """Verify crisis messages return immediate emergency resources and crisis action."""
    res = _run_sync(chat_endpoint(ChatRequest(
        message="I can't take this anymore, I want to kill myself.",
        user_id="test-crisis-user"
    )))
    assert res.safety_level == "CRISIS"
    assert res.suggested_action == "show_crisis_modal"
    assert "988" in res.reply

def test_chat_empty_message_validation():
    """Verify empty message triggers 400 Bad Request."""
    with pytest.raises(HTTPException) as exc_info:
        _run_sync(chat_endpoint(ChatRequest(message="   ")))
    assert exc_info.value.status_code == 400
