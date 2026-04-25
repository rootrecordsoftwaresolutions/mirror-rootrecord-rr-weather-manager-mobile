#!/usr/bin/env python3
"""POST /api/internal/push-broadcast — stdlib only. Set RR_API_BASE, RR_PUSH_ADMIN_KEY (same as server RR_PUSH_ADMIN_SECRET)."""

from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request


def main() -> int:
    base = (os.environ.get("RR_API_BASE") or "https://rootrecord-primary.rootrecord.workers.dev/api").rstrip("/")
    key = (os.environ.get("RR_PUSH_ADMIN_KEY") or "").strip()
    if not key:
        print("Set RR_PUSH_ADMIN_KEY to match RR_PUSH_ADMIN_SECRET on the API server.", file=sys.stderr)
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
