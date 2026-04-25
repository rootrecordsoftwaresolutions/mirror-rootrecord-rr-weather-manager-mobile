# Assets (mobile and brand reference)

- **Posters, photos, `github-icon.jpg`, etc.** — store listings, social, and README; not loaded by the dev server at runtime unless you wire them in.
- **`notification-sounds-source/*.mp3`** — candidate alert sounds for a native app (iOS / Android) or a web build that plays MP3; pick and ship the set you license for production.

The previous Windows installer used separate NSIS art and a root-level `.ico` for the desktop shell; those were removed from this mobile-focused tree. Use platform-appropriate icon sets (e.g. adaptive icons, asset catalogs) when you ship to stores.
