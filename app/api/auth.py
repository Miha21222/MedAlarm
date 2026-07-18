from __future__ import annotations

import base64
import binascii
import hashlib
import hmac
import json
import time
from urllib.parse import parse_qsl


def _encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode("ascii")


def _decode(value: str) -> bytes:
    padding = "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode(f"{value}{padding}")


def create_access_token(telegram_id: int, secret: str, ttl_seconds: int = 86400) -> str:
    payload = {
        "sub": telegram_id,
        "exp": int(time.time()) + ttl_seconds,
    }
    body = _encode(json.dumps(payload, separators=(",", ":")).encode())
    signature = _encode(hmac.new(secret.encode(), body.encode(), hashlib.sha256).digest())
    return f"{body}.{signature}"


def decode_access_token(token: str, secret: str, now: int | None = None) -> int:
    try:
        body, signature = token.split(".", maxsplit=1)
        expected = _encode(hmac.new(secret.encode(), body.encode(), hashlib.sha256).digest())
        if not hmac.compare_digest(signature, expected):
            raise ValueError("invalid token signature")
        payload = json.loads(_decode(body))
        if not isinstance(payload, dict):
            raise ValueError("invalid access token")
        expires_at = int(payload["exp"])
        telegram_id = int(payload["sub"])
        if expires_at <= (int(time.time()) if now is None else now):
            raise ValueError("token expired")
        if telegram_id <= 0:
            raise ValueError("invalid access token")
        return telegram_id
    except (binascii.Error, KeyError, TypeError, UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
        if isinstance(exc, ValueError) and str(exc) in {
            "invalid token signature",
            "token expired",
        }:
            raise
        raise ValueError("invalid access token") from exc


def validate_telegram_init_data(
    init_data: str,
    bot_token: str,
    *,
    max_age_seconds: int = 86400,
    now: int | None = None,
) -> dict[str, object]:
    pairs = parse_qsl(init_data, keep_blank_values=True)
    if len({key for key, _ in pairs}) != len(pairs):
        raise ValueError("duplicate Telegram parameter")
    values = dict(pairs)
    received_hash = values.pop("hash", "")
    if not received_hash:
        raise ValueError("missing Telegram hash")

    data_check = "\n".join(f"{key}={values[key]}" for key in sorted(values))
    secret_key = hmac.new(b"WebAppData", bot_token.encode(), hashlib.sha256).digest()
    expected_hash = hmac.new(secret_key, data_check.encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(received_hash, expected_hash):
        raise ValueError("invalid Telegram hash")

    auth_date = int(values.get("auth_date", "0"))
    current = int(time.time()) if now is None else now
    if auth_date <= 0 or current - auth_date > max_age_seconds:
        raise ValueError("Telegram authorization expired")
    if auth_date - current > 30:
        raise ValueError("Telegram authorization date is in the future")

    try:
        user = json.loads(values["user"])
    except (KeyError, json.JSONDecodeError) as exc:
        raise ValueError("missing Telegram user") from exc
    if not isinstance(user, dict) or not isinstance(user.get("id"), int):
        raise ValueError("invalid Telegram user")
    return user
