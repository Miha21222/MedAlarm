import pytest

from app.config import DEFAULT_JWT_SECRET, load_settings


def test_dev_env_allows_default_jwt_secret(monkeypatch):
    monkeypatch.setenv("APP_ENV", "dev")
    monkeypatch.delenv("JWT_SECRET", raising=False)
    settings = load_settings()
    assert settings.jwt_secret == DEFAULT_JWT_SECRET


def test_non_dev_env_rejects_default_jwt_secret(monkeypatch):
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("BOT_TOKEN", "test-bot-token")
    monkeypatch.delenv("JWT_SECRET", raising=False)
    with pytest.raises(RuntimeError, match="JWT_SECRET"):
        load_settings()


def test_non_dev_env_accepts_real_jwt_secret(monkeypatch):
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("BOT_TOKEN", "test-bot-token")
    monkeypatch.setenv("JWT_SECRET", "0123456789abcdef0123456789abcdef")
    monkeypatch.setenv("MINI_APP_URL", "https://example.github.io/MedAlarm/")
    monkeypatch.setenv("CORS_ALLOWED_ORIGINS", "https://example.github.io")
    settings = load_settings()
    assert settings.jwt_secret == "0123456789abcdef0123456789abcdef"
    assert settings.feedback_chat_id == -1004421534137
    assert settings.feedback_topic_id == 3
    assert settings.bug_report_topic_id == 5


def test_production_rejects_localhost_origin(monkeypatch):
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("BOT_TOKEN", "test-bot-token")
    monkeypatch.setenv("JWT_SECRET", "0123456789abcdef0123456789abcdef")
    monkeypatch.setenv("MINI_APP_URL", "https://example.github.io/MedAlarm/")
    monkeypatch.setenv("CORS_ALLOWED_ORIGINS", "http://localhost:5173")
    with pytest.raises(RuntimeError, match="CORS"):
        load_settings()
