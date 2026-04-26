# Changelog

## [Unreleased]

## [1.0.2] — 2026-04-26

- **Settings:** “Contact & support” section with website, contact form, Discord, and Telegram (opens in the system browser).

## [1.0.1] — 2026-04-26

- **Weather:** hourly strip and “now” fallback use NWS grid `properties.units` (`hourly_grid_units`) when resolving air temperature, so SI (°C) hourly values are not misread as °F (fixes ~5°F cold bias vs station “now”).
- **API:** Cloudflare `rootrecord-primary` forecast JSON includes `hourly_grid_units`; optional FastAPI mirror matches.

