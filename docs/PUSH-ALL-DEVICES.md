# All-device push (FCM broadcast)



The mobile app registers tokens with **`POST /api/me/push-token`** (after `REACT_APP_ENABLE_PUSH=1` and a native build with Firebase). An operator broadcast sends one notification to **every** stored token.



## Cloudflare (`rootrecord-primary`)



Production API: **`POST /api/internal/push-broadcast`** — JSON `{ "title": "…", "body": "…" }`, header **`X-RR-Push-Admin-Key`** (plaintext; Worker compares SHA-256 digests).



**Wrangler secrets** (from `cloudflare/rootrecord-primary`):



- **`RR_PUSH_ADMIN_SECRET`** — you choose it; same value you send as **`X-RR-Push-Admin-Key`**.

- **`FCM_SERVICE_ACCOUNT_JSON`** — full Firebase **service account** JSON (one paste). Optional: split into `FCM_PROJECT_ID`, `FCM_CLIENT_EMAIL`, `FCM_PRIVATE_KEY` instead.



Response shape: `{ ok, fcm: { success, failure, total_tokens, errors } }`.



Example:



```bash

curl -sS -X POST "$BASE/api/internal/push-broadcast" \

  -H "Content-Type: application/json" \

  -H "X-RR-Push-Admin-Key: YOUR_PLAINTEXT_SECRET" \

  -d '{"title":"Heads up","body":"Message for all devices."}'

```



`BASE` is the API origin **without** `/api` (same as `REACT_APP_BACKEND_URL`).



## Ops script (PowerShell)



From repo root, with **`RR_PUSH_ADMIN_KEY`** and optional **`REACT_APP_BACKEND_URL`**:



```powershell

.\rr-weather-manager-mobile\scripts\push-broadcast.ps1 -Title "Test" -Body "Hello from ops"

```



## Optional Python API



The `backend/` tree in this repo can run a separate FastAPI service with the same broadcast contract if you ever host it; production for the mobile app is the Worker above.

