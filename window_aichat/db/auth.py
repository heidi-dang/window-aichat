import base64
import hashlib
import os
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional

from jose import jwt


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    iterations = 200_000
    dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations, dklen=32)
    return f"pbkdf2_sha256${iterations}${base64.b64encode(salt).decode()}${base64.b64encode(dk).decode()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        scheme, iters_str, salt_b64, hash_b64 = stored.split("$", 3)
        if scheme != "pbkdf2_sha256":
            return False
        iterations = int(iters_str)
        salt = base64.b64decode(salt_b64.encode())
        expected = base64.b64decode(hash_b64.encode())
        dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations, dklen=len(expected))
        return secrets.compare_digest(dk, expected)
    except Exception:
        return False


def _jwt_secret() -> str:
    secret = os.getenv("WINDOW_AICHAT_JWT_SECRET")
    if secret:
        return secret
    return "dev-insecure-secret-change-me"


def issue_token(user_id: str, username: str) -> str:
    now = datetime.now(timezone.utc)
    exp = now + timedelta(hours=int(os.getenv("WINDOW_AICHAT_JWT_TTL_HOURS", "72")))
    payload = {"sub": user_id, "username": username, "iat": int(now.timestamp()), "exp": int(exp.timestamp())}
    return jwt.encode(payload, _jwt_secret(), algorithm="HS256")


def decode_token(token: str) -> Optional[dict]:
    try:
        return jwt.decode(token, _jwt_secret(), algorithms=["HS256"])
    except Exception:
        return None
