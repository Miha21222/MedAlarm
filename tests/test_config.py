import pytest

from app.config import DEFAULT_JWT_SECRET, load_settings


def test_dev_env_allows_default_jwt_secret(monkeypatch):
    monkeypatch.setenv("APP_ENV", "dev")
    monkeypatch.delenv("JWT_SECRET", raising=False)
    settings = load_settings()
    assert settings.jwt_secret == DEFAULT_JWT_SECRET


def test_non_dev_env_rejects_default_jwt_secret(monkeypatch):
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.delenv("JWT_SECRET", raising=False)
    with pytest.raises(RuntimeError, match="JWT_SECRET"):
        load_settings()


def test_non_dev_env_accepts_real_jwt_secret(monkeypatch):
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("JWT_SECRET", "a-real-random-secret")
    settings = load_settings()
    assert settings.jwt_secret == "a-real-random-secret"
