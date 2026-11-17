"""Password hashing (scrypt, built into Python) and a tiny in-memory rate limiter."""
import hashlib
import hmac
import os
import time
from collections import defaultdict, deque

from .errors import AppError


def hash_password(password: str) -> str:
    salt = os.urandom(16)
    digest = hashlib.scrypt(password.encode(), salt=salt, n=2**14, r=8, p=1)
    return f"{salt.hex()}${digest.hex()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        salt_hex, digest_hex = stored.split("$")
        digest = hashlib.scrypt(password.encode(), salt=bytes.fromhex(salt_hex), n=2**14, r=8, p=1)
    except ValueError:
        return False
    return hmac.compare_digest(digest.hex(), digest_hex)


_hits: dict[str, deque] = defaultdict(deque)


def rate_limit(key: str, limit: int, window_seconds: int, message: str) -> None:
    """Allow `limit` calls per `window_seconds` per key. (Memory only: resets on restart.)"""
    now = time.monotonic()
    q = _hits[key]
    while q and now - q[0] > window_seconds:
        q.popleft()
    if len(q) >= limit:
        raise AppError(429, message, "RATE_LIMITED")
    q.append(now)
