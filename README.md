# My Media Vault — Themes

A community registry of themes for **My Media Vault**. A theme is a **folder** under `themes2/` with a
`theme.json` that lays out the home screen from elements: carousels, grids, the PlayStation-style XMB cross,
particles, a wave, sounds, … You pick one in **Settings → Appearance**.

The raw `index.json` for this repo is:

```
https://raw.githubusercontent.com/cubman3134/mymediavault-themes/main/index.json
```

## Install a theme
Each theme is a **folder** under `themes2/`. To use one, copy its whole folder into your app's `themes2/`
directory (next to `MyMediaVault.exe`, e.g. `C:\MyMediaVault-app\themes2\<Theme>\`), then pick it in
**Settings → Appearance**. Editing a theme's `theme.json` updates the home live (hot-reload).

## Contribute a theme
1. Copy your theme **folder** (a `theme.json` plus any assets it references — background image, icons, `sounds/…`)
   into `themes2/<YourTheme>/`.
2. Add an entry to the **`themes2`** array in `index.json`:

   ```json
   { "name": "My Theme", "author": "you", "description": "One line about the look.", "dir": "themes2/MyTheme" }
   ```
3. Open a pull request.

See **[`THEME_FORMAT.md`](THEME_FORMAT.md)** for the full element/layout reference, and copy any of the shipped
folders (`Default`, `Grid`, `Lumen`, `Midnight`, `Triple`, `Channels`) as a starting point.
