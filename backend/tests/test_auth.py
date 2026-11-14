import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_user_preferences_default():
    """Verify default user preferences are returned when no custom preferences exist."""
    res = client.get("/api/empathy/profile?user_id=new-guest-user")
    assert res.status_code == 200
    data = res.json()
    assert data["communication_style"] == "warm"
    assert data["preferred_pacing"] == "normal"
    assert data["profile_type"] == "PROFILE_A"
