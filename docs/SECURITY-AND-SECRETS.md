# Security and secrets

## What must not be in Git

- **`.env`** and any file containing **API keys**, **bearer tokens**, or **connection strings** for live services.
- **Firebase** `*adminsdk*.json` or any **service account** JSON.

The repository **.gitignore** is configured to exclude these patterns; double-check with `git status` before any push.

## Runtime and CI secrets

- **`LICENSE_API_SECRET`** (and similar) should be set in **the OS environment** or a **CI secret store**, not committed.
- The **shipped** license **Worker** URL in code may be public; any **shared bearer** or **client secret** is sensitive. Rotate if leaked.

## Mobile clients

- Do not embed a **bearer** or **client secret** in a store app. Use the token model your backend defines (OAuth, per-device registration, etc.).

## Reporting

- If you find credentials in a commit, **rotate** the credential, **remove** the blob from history (BFG or `git filter-repo`) if the repo is public, and re-push.
