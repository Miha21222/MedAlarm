import hashlib
import hmac
import json
import time
from urllib.parse import urlencode

import pytest

from app.api.auth import (
    create_access_token,
    decode_access_token,
    validate_telegram_init_data,
)


def test_access_token_round_trip():
    token = create_access_token(telegram_id=123456, secret="test-secret", ttl_seconds=60)
    assert decode_access_token(token, secret="test-secret") == 123456


def test_expired_access_token_is_rejected():
    token = create_access_token(telegram_id=123456, secret="test-secret", ttl_seconds=-1)
    with pytest.raises(ValueError, match="expired"):
        decode_access_token(token, secret="test-secret", now=int(time.time()))


def test_invalid_telegram_init_data_is_rejected():
    with pytest.raises(ValueError, match="hash"):
        validate_telegram_init_data("user=%7B%22id%22%3A1%7D&hash=invalid", "bot-token")


def _signed_init_data(bot_token: str, auth_date: int) -> str:
    values = {
        "auth_date": str(auth_date),
        "query_id": "test-query",
        "user": json.dumps({"id": 123456, "first_name": "Test"}, separators=(",", ":")),
    }
    data_check = "\n".join(f"{key}={values[key]}" for key in sorted(values))
    secret = hmac.new(b"WebAppData", bot_token.encode(), hashlib.sha256).digest()
    values["hash"] = hmac.new(secret, data_check.encode(), hashlib.sha256).hexdigest()
    return urlencode(values)


def test_valid_telegram_init_data_is_accepted():
    now = int(time.time())
    identity = validate_telegram_init_data(_signed_init_data("bot-token", now), "bot-token", now=now)
    assert identity["id"] == 123456


def test_expired_telegram_init_data_is_rejected():
    now = int(time.time())
    with pytest.raises(ValueError, match="expired"):
        validate_telegram_init_data(
            _signed_init_data("bot-token", now - 86401),
            "bot-token",
            now=now,
        )
