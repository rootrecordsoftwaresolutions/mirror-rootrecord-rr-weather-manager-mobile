# Brand assets → app stores & legacy icons

## What’s in this folder

- **`logo-mark.svg`** — optional vector mark for marketing / Figma.
- **Launcher foreground (current):** `assets/1qOHn-removebg-preview.png` is copied into Android `drawable-nodpi/ic_launcher_foreground_photo.png` and `frontend/public/app-icon.png`, wired in `mipmap-anydpi-v26`. Re-copy after replacing the source file.

## Adaptive icon (API 26+)

The app uses **`ic_launcher_foreground_brand.xml`** + dark **`#121212`** background. Rebuild the Android app to see the new launcher on most devices.

## Legacy mipmap PNGs (API &lt; 26 and some OEMs)

Capacitor’s generated **`mipmap-*/ic_launcher*.png`** files may still appear on very old Android versions. To refresh **all** densities from `logo-mark.svg`:

1. Open **`frontend/android`** in **Android Studio**.
2. **File → New → Image Asset** (or right-click `res` → **New → Image Asset**).
3. **Icon type:** Launcher Icons (Adaptive and Legacy).
4. **Path:** set foreground to `assets/brand/logo-mark.svg` (or export a 432×432 PNG with important content in the center **66dp** safe circle).
5. **Background color:** `#121212`.
6. Finish — this overwrites **`mipmap-*`** and keeps **`mipmap-anydpi-v26`** in sync if you choose adaptive + legacy.

## PWA / favicon

`frontend/public/logo.svg` is wired in **`index.html`** and **`manifest.json`**. For a classic **`.ico`**, export a 32×32 PNG from the SVG and replace `public/favicon.ico` (optional).
