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

Set `REACT_APP_BACKEND_URL` to your API base (no trailing `/api`); the client uses `${REACT_APP_BACKEND_URL}/api` (see `frontend/src/lib/api.js`).

**Visible installs:** from this repo’s root run **`pnpm run install:frontend:verbose`** — it runs `frontend/scripts/npm-install-with-progress.ps1` (debug-level pnpm log + `pnpm-install.log` next to the workspace `package.json`). **`pnpm run install:frontend`** runs **`pnpm install`** at the workspace root. Commit the workspace **`pnpm-lock.yaml`** (one lockfile for all packages); **`pnpm run ci:frontend`** runs **`pnpm install --frozen-lockfile`** from the workspace root.

**If installs spam `TAR_ENTRY_ERROR` on Windows:** stop the process, then run `frontend\scripts\clean-install-frontend.ps1` (rimraf workspace + frontend `node_modules`, then frozen install when a lockfile exists). Use **`-PurgeLockfile`** only if the lockfile itself is suspect. `frontend/.npmrc` sets `maxsockets=1` for day‑to‑day installs. If errors persist, move the workspace to a **shorter path** (for example `C:\dev\rr-weather\`) or enable [Windows long paths](https://learn.microsoft.com/en-us/windows/win32/fileio/maximum-file-path-limitation).

**Standalone clone (only this repo, no parent workspace):** use `cd frontend && npm install && npm start` as before; you will not share the parent pnpm store until you place the clone under the workspace layout above.

**If the terminal “does nothing” while deleting `node_modules`:** use the clean-install script (rimraf), or delete `frontend/node_modules` in Explorer, then `pnpm run install:frontend` or the verbose script above.

## Android (Capacitor)

The native project lives in **`frontend/android/`** (Capacitor 6). Use **JDK 17** for Gradle (the Android Gradle Plugin used here does not run the Gradle daemon on **JDK 25**). Set **`ANDROID_HOME`** (and optionally **`ANDROID_SDK_ROOT`**) to your Android SDK, e.g. `%LOCALAPPDATA%\Android\Sdk` on Windows.

**Typical flow (from `frontend/`):** `pnpm run build` → `pnpm exec cap sync android` → open **`android/`** in Android Studio and **Run**, or from `frontend/android/` run **`.\gradlew.bat assembleDebug`** (debug APK under `app/build/outputs/apk/debug/`).

**Gradle JVM:** if your default `java` is newer than Gradle supports (for example **JDK 25**), point Gradle at **JDK 17** with `org.gradle.java.home` in **`%USERPROFILE%\.gradle\gradle.properties`**. **`frontend/android/local.properties`** can set `sdk.dir` for CLI builds (gitignored—Android Studio can create it, or copy from a teammate’s example with your own SDK path).

Scripts in `frontend/package.json`: `cap:sync`, `android:open`, `android:build`, `android:assemble`.

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
