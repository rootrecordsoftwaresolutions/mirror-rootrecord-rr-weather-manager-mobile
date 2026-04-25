#!/usr/bin/env python3
"""POST /api/internal/push-broadcast — stdlib only. Set RR_API_BASE, RR_PUSH_ADMIN_KEY (same as server RR_PUSH_ADMIN_SECRET)."""

from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request

# Cloudflare Browser Integrity Check blocks default Python-urllib User-Agent (HTTP 403, error 1010).
_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/131.0.0.0 Safari/537.36 RootRecordBroadcast/1.0"
)


def _read_rr_push_secret_from_backend_env() -> str:
    root = os.getcwd()
    path = os.path.join(root, "backend", ".env")
    if not os.path.isfile(path):
        return ""
    try:
        with open(path, encoding="utf-8", errors="replace") as f:
            for raw in f:
                line = raw.strip()
                if not line or line.startswith("#"):
                    continue
                if line.startswith("RR_PUSH_ADMIN_SECRET="):
                    v = line.split("=", 1)[1].strip().strip('"').strip("'")
                    return v
    except OSError:
        return ""
    return ""


def main() -> int:
    base = (os.environ.get("RR_API_BASE") or "https://rootrecord-primary.rootrecord.workers.dev/api").rstrip("/")
    key = (os.environ.get("RR_PUSH_ADMIN_KEY") or "").strip()
    if not key:
        key = _read_rr_push_secret_from_backend_env()
    if not key:
        print(
            "Missing admin key: set RR_PUSH_ADMIN_KEY, or add RR_PUSH_ADMIN_SECRET=... to backend\\.env",
            file=sys.stderr,
        )
        return 1

    title = os.environ.get("TITLE") or (sys.argv[1] if len(sys.argv) > 1 else "Root Record test")
    body = os.environ.get("BODY") or (sys.argv[2] if len(sys.argv) > 2 else "All-device broadcast test.")

    url = f"{base}/internal/push-broadcast"
    payload = json.dumps({"title": title, "body": body}).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=payload,
        headers={
            "Content-Type": "application/json; charset=utf-8",
            "X-RR-Push-Admin-Key": key,
            "User-Agent": _UA,
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "en-US,en;q=0.9",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
            print(raw)
            if resp.status >= 400:
                return 1
    except urllib.error.HTTPError as e:
        err_body = e.read().decode("utf-8", errors="replace") if e.fp else ""
        print(f"HTTP {e.code}: {err_body or e.reason}", file=sys.stderr)
        return 1
    except urllib.error.URLError as e:
        print(str(e.reason), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
