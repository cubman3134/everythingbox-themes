# My Media Vault — Themes

A community registry of themes for **My Media Vault**. There are two kinds:

- **`themes2/`** — the **new declarative front-end themes** (folders with a `theme.json` that lay out the home
  screen from elements: carousels, grids, the PlayStation-style XMB cross, particles, a wave, sounds, …). These
  are picked in **Settings → Appearance**. **Start here** — this is the current theme system.
- **`themes/`** — the older colour themes (a single JSON of accent colours + a `layout`). Legacy.

The raw `index.json` for this repo is:

```
https://raw.githubusercontent.com/cubman3134/mymediavault-themes/main/index.json
```

## Install a `themes2` theme
Each theme is a **folder** under `themes2/`. To use one, copy its whole folder into your app's `themes2/`
directory (next to `MyMediaVault.exe`, e.g. `C:\MyMediaVault-app\themes2\<Theme>\`), then pick it in
**Settings → Appearance**. Editing a theme's `theme.json` updates the home live (hot-reload).

## Contribute a `themes2` theme
1. Copy your theme **folder** (a `theme.json` plus any assets it references — background image, icons, `sounds/…`)
   into `themes2/<YourTheme>/`.
2. Add an entry to the **`themes2`** array in `index.json`:

   ```json
   { "name": "My Theme", "author": "you", "description": "One line about the look.", "dir": "themes2/MyTheme" }
   ```
3. Open a pull request.

See **[`THEME_FORMAT.md`](THEME_FORMAT.md)** for the full element/layout reference, and copy any of the shipped
folders (`Default`, `Grid`, `Lumen`, `Midnight`, `Triple`) as a starting point.

## Contribute a legacy `themes/` colour theme
1. Add your theme JSON under `themes/` (and any background image / icons it references).
2. Add an entry to `index.json`:

   ```json
   {
     "name": "My Theme",
     "author": "you",
     "description": "One line about the look.",
     "file": "themes/MyTheme.json",
     "assets": ["themes/my-bg.png"]
   }
   ```
   - `file`     the theme JSON (downloaded into the app's `themes/` folder).
   - `assets`   any images the theme references (background, icons) — also downloaded into `themes/`.
3. Open a pull request.

### Theme file format
See `themes/Aurora.json` for a full example. Supported keys: `name`, `accentFollowsTab`, `accent`,
`neutralTab`, `tabColors`, `fontFamily`, `fontScale`, `cornerRadius`, `background`, `backgroundDim`,
`icons`, and `detail` (`image`: left/top/hidden, `imageWidth`, `order`).
