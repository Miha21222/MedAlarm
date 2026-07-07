import time

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
