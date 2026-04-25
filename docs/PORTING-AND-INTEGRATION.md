# Porting and integration (mobile)

This repository is set up for **mobile-oriented** development: the **React** app under `frontend/` and the **FastAPI** service under `backend/`. Wire the UI to your deployed API with `REACT_APP_BACKEND_URL`.

## What to use as the contract

- **HTTP API** — `frontend/src/lib/api.js` lists the paths the UI expects under `/api` (auth, locations, weather, hazards, dashboard).
- **Backend** — `backend/server.py` implements the same shape for local or hosted runs (MongoDB, license Worker proxy, public weather/hazard feeds).
- **Session** — the web app uses `localStorage` for tokens and guest id; a native app should use **Keychain / Keystore** and your product’s session model instead of copying storage keys blindly.

## Native iOS / Android

- There is **no** shared view layer with a future native app; reuse **behavior** and **API contracts**, not UI code, unless you adopt a cross-platform stack (e.g. React Native) and port components deliberately.
- **Push, background fetch, and location** follow platform rules; map the same product limits (e.g. guest vs signed-in) in your client.

## Design and media

- **`design_guidelines.json`** and stills under `assets/` support a consistent brand for store listings and iconography.

## Suggested work order

1. Run **`frontend`** against a configured **`backend`** (or staging API).
2. Harden **auth and guest** flows for your target platform.
3. Plan **store** distribution and updates (App Store / Play); this tree does not include desktop installers or `latest.yml` auto-updaters.
