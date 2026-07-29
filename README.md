# EverythingBox — Themes

A community registry of themes for **EverythingBox**. A theme is a **folder** under `themes2/` with a
`theme.json` that lays out the home screen from elements: carousels, grids, the PlayStation-style XMB cross,
particles, a wave, sounds, … You pick one in **Settings → Appearance**.

The raw `index.json` for this repo is:

```
https://raw.githubusercontent.com/cubman3134/everythingbox-themes/main/index.json
```

## Install a theme

The easy way is from inside the app: **Settings → Appearance → Theme…**, which browses this registry
and installs in a couple of presses.

To install by hand instead, copy the theme's whole folder into your app's `themes2/` directory — the
one next to `EverythingBox.exe` — so you end up with `…/themes2/<Theme>/theme.json`, then pick it in
**Settings → Appearance**. Editing a theme's `theme.json` updates the home live (hot-reload).

## Contribute a theme
1. Copy your theme **folder** (a `theme.json` plus any assets it references — background image, icons, `sounds/…`)
   into `themes2/<YourTheme>/`.
2. Add an entry to the **`themes2`** array in `index.json`:

   ```json
   { "name": "My Theme", "author": "you", "description": "One line about the look.", "dir": "themes2/MyTheme" }
   ```
3. Open a pull request.

See **[`THEME_FORMAT.md`](THEME_FORMAT.md)** for the full element/layout reference, and copy any folder in
this repo (`Default`, `Grid`, `Lumen`, `Midnight`, `Triple`, `Channels`) as a starting point. `Triple` and
`Channels` are the two that ship with the app; the rest install from here.
