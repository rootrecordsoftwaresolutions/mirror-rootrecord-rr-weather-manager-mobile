# Root Record Weather Manager — mobile development

This tree is for **mobile-oriented** work: the **React** app in `frontend/` (package name `rrweather-mobile`) and the optional **FastAPI** service in `backend/` for local or hosted APIs.

## Run the mobile UI (web / dev server)

This repo is meant to sit under the **`Mobile App Development`** folder next to the root **`package.json`** / **`pnpm-workspace.yaml`**, so **one pnpm store** and **hoisted `node_modules`** serve Weather Manager and future apps under `apps/*`.

**Install once (from `Mobile App Development`):**

```bash
pnpm install
```

**Run the UI:**

```bash
pnpm weather:start
```

Or from this repository’s root: **`pnpm start`** (delegates to the workspace). From `frontend/`: **`pnpm start`** still works if dependencies are already installed.

Set `REACT_APP_BACKEND_URL` to your API base (no trailing `/api`); the client uses `${REACT_APP_BACKEND_URL}/api` (see `frontend/src/lib/api.js`). For Android/production builds use **`frontend/.env.production`** (gitignored). To pull secrets you keep on **`F:\Root Record Operations`**, create **`F:\Root Record Operations\secrets\rr-weather-manager\frontend.env.production`** and **`backend.env`**, then run **`powershell -NoProfile -File frontend\scripts\sync-env-from-operations.ps1`**. **`backend/.env.example`** lists FastAPI variables; copy to **`backend/.env`**.

**Visible installs:** from this repo’s root run **`pnpm run install:frontend:verbose`** — it runs `frontend/scripts/npm-install-with-progress.ps1` (debug-level pnpm log + `pnpm-install.log` next to the workspace `package.json`). **`pnpm run install:frontend`** runs **`pnpm install`** at the workspace root. Commit the workspace **`pnpm-lock.yaml`** (one lockfile for all packages); **`pnpm run ci:frontend`** runs **`pnpm install --frozen-lockfile`** from the workspace root.

**If installs spam `TAR_ENTRY_ERROR` on Windows:** stop the process, then run `frontend\scripts\clean-install-frontend.ps1` (rimraf workspace + frontend `node_modules`, then frozen install when a lockfile exists). Use **`-PurgeLockfile`** only if the lockfile itself is suspect. `frontend/.npmrc` sets `maxsockets=1` for day‑to‑day installs. If errors persist, move the workspace to a **shorter path** (for example `C:\dev\rr-weather\`) or enable [Windows long paths](https://learn.microsoft.com/en-us/windows/win32/fileio/maximum-file-path-limitation).

**Standalone clone (only this repo, no parent workspace):** use `cd frontend && npm install && npm start` as before; you will not share the parent pnpm store until you place the clone under the workspace layout above.

**If the terminal “does nothing” while deleting `node_modules`:** use the clean-install script (rimraf), or delete `frontend/node_modules` in Explorer, then `pnpm run install:frontend` or the verbose script above.

## Android (Capacitor)

Native project: **`frontend/android/`** (Capacitor 6). This dev PC uses **JDK 17** for Gradle via **`%USERPROFILE%\.gradle\gradle.properties`**, **`ANDROID_HOME`** / **`ANDROID_SDK_ROOT`** → `%LOCALAPPDATA%\Android\Sdk`, and **`frontend/android/local.properties`** (`sdk.dir`; gitignored).

**Debug APK (CLI):** from **`frontend/`**, run **`pnpm run android:assemble`**. Output: **`frontend/android/app/build/outputs/apk/debug/RootRecord-Weather.apk`** (release: **`.../release/RootRecord-Weather-release.apk`**).

**Android Studio:** open **`frontend/android`**, sync Gradle, choose a device or emulator, **Run**. Double-click **`open-weather-android-studio.bat`** in this repo root, or run **`pnpm run android:open`** from **`frontend/`**.

Scripts in `frontend/package.json`: `cap:sync`, `android:open`, `android:build`, `android:assemble`.

## Pre-release testing (before Google Play)

The **public** source repo for early access is **[github.com/RootRecord/rootrecord-weather-manager](https://github.com/RootRecord/rootrecord-weather-manager)**. It tracks the same app as the private development remote; use it to clone, inspect, and file issues.

**APK:** we do not ship a store build from this README alone. Testers can either (1) install from **GitHub Releases** when you attach a signed or debug APK there, or (2) build locally: from `frontend/`, run `pnpm run android:assemble` and share `frontend/android/app/build/outputs/apk/debug/RootRecord-Weather.apk` (debug) or the release output after your signing setup. Pre-releases are **not** a replacement for Play Protect / production distribution.

**What changed this build:** from the **repo root** (`rr-weather-manager-mobile/`), run **`pnpm changelog:stamp`** before you tag or publish a pre-release. That appends a timestamped block to **`CHANGELOG.md`** listing commits since the last stamp (tracked in **`.changelog-last-ref`**). Optional one-liner: `CHANGELOG_NOTE="Short human summary" pnpm changelog:stamp`. Then commit `CHANGELOG.md` + `.changelog-last-ref` and paste the new section into the GitHub Release notes if you like.

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
