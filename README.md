# Root Record Weather Manager — mobile development

This tree is for **mobile-oriented** work: the **React** app in `frontend/` (package name `rrweather-mobile`) and the optional **FastAPI** service in `backend/` for local or hosted APIs.

## Run the mobile UI (web / dev server)

```bash
cd frontend
npm install
npm start
```

From the repository root you can also run `npm start` (see root `package.json`).

Set `REACT_APP_BACKEND_URL` to your API base (no trailing `/api`); the client uses `${REACT_APP_BACKEND_URL}/api` (see `frontend/src/lib/api.js`).

## Optional: local API

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
# configure .env (see backend code for MONGO_URL, etc.)
uvicorn server:app --reload
```

## Design and assets

- **`design_guidelines.json`** — product design reference.
- **`assets/`** — brand and marketing stills, icon sources, and **`notification-sounds-source/`** (alert sound options for native mobile).

## Docs

- **[docs/README.md](docs/README.md)** — index.
- **[docs/PORTING-AND-INTEGRATION.md](docs/PORTING-AND-INTEGRATION.md)** — platform notes and API expectations.
- **[docs/SECURITY-AND-SECRETS.md](docs/SECURITY-AND-SECRETS.md)** — what must not be committed.

There is **no** Windows desktop or Electron build in this copy.
