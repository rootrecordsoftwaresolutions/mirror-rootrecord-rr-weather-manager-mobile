"""Firebase Cloud Messaging — optional; used only when FCM_SERVICE_ACCOUNT_JSON is set."""

from __future__ import annotations

import logging
import os
from typing import Any, List

logger = logging.getLogger("rrweather")


def credentials_path() -> str:
    return (os.environ.get("FCM_SERVICE_ACCOUNT_JSON") or "").strip()


def is_fcm_configured() -> bool:
    p = credentials_path()
    return bool(p and os.path.isfile(p))


def _ensure_app() -> None:
    import firebase_admin
    from firebase_admin import credentials

    try:
        firebase_admin.get_app()
    except ValueError:
        cred = credentials.Certificate(credentials_path())
        firebase_admin.initialize_app(cred)


def send_multicast_blocking(tokens: List[str], title: str, body: str) -> dict[str, Any]:
    """Blocking FCM send (call via asyncio.to_thread from FastAPI)."""
    from firebase_admin import messaging

    if not tokens:
        return {"success": 0, "failure": 0, "errors": [], "total_tokens": 0}

    _ensure_app()
    success = 0
    failure = 0
    sample_errors: list[str] = []
    chunk_size = 500

    for i in range(0, len(tokens), chunk_size):
        chunk = tokens[i : i + chunk_size]
        msg = messaging.MulticastMessage(
            notification=messaging.Notification(title=title, body=body),
            tokens=chunk,
            android=messaging.AndroidConfig(
                priority="high",
                notification=messaging.AndroidNotification(sound="default"),
            ),
        )
        resp = messaging.send_each_for_multicast(msg)
        success += resp.success_count
        failure += resp.failure_count
        for idx, r in enumerate(resp.responses):
            if not r.success and r.exception is not None and len(sample_errors) < 8:
                tid = chunk[idx][:32] if chunk[idx] else "?"
                sample_errors.append(f"{tid}…: {r.exception}")

    return {
        "success": success,
        "failure": failure,
        "errors": sample_errors,
        "total_tokens": len(tokens),
    }
