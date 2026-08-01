#!/usr/bin/env python3
"""Registry gate: a theme may only name asset files INSIDE its own folder.

Every path a theme.json declares — background images, element `path`/`fallback`, `fontFile`,
a particles `image`, `sounds`, `music` — is resolved by the app relative to that theme's own
folder, and the app REFUSES anything that lands outside it. A refused path is not trimmed back
inside; it resolves to nothing and the element draws its placeholder or the sound stays silent.

So a theme published here that names `../OtherTheme/bg.jpg`, `C:/Users/me/art.png` or
`https://my-cdn.example/bg.jpg` is not "slightly wrong" — it is a theme that renders blank for
everyone who installs it, with nothing on screen to say why. This gate rejects it at submission
instead, while the author is still here to fix it.

Remote URLs deserve their own sentence, because they are the one shape that used to WORK. The app
fetched them, and stopped: a theme.json here is a third-party document, and one that pulls its
artwork from a server would contact that server every time somebody's home screen drew, could show
different art after review than during it, and would render blank for anyone offline. Ship the file
in the theme folder.

THIS RULE EXISTS THREE TIMES and they must agree:
  * native/src/core/ThemeAssetPath.h     (app, C++)   — pinned by probe_theme section 8
  * native/src/theme2/qml/Theme.js       (app, QML)   — pinned by probe_themeview section 9
  * here                                 (registry)   — pinned by --self-test below
The self-test runs FIRST on every invocation and is the same case table the app's probes use. If
this file ever drifts from the app, the gate fails loudly rather than quietly passing everything.
(The one intended difference from the C++ half: absolute paths are refused outright rather than
judged by containment. An absolute path in a published theme is unportable by construction.)

Usage:
  tools/check-theme-assets.py              # gate every theme under themes2/ (exit 1 on a problem)
  tools/check-theme-assets.py --self-test  # just prove the rule still matches the app's
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
THEMES = os.path.join(HERE, os.pardir, "themes2")

# Artwork ROLES the app resolves from the item's own metadata. A `fallback` naming one of these is
# not a file path at all — the app looks the role up first and only treats the word as a literal
# path if the item has no such art, which then simply shows the placeholder. Not a break.
ROLE_WORDS = {"poster", "box", "thumb", "hero", "banner", "logo", "fanart", "background",
              "screenshot", "image", "clearlogo", "art", "wide", "tile", "icon", "cover"}

ASSET_EXT = (".png", ".jpg", ".jpeg", ".webp", ".gif", ".svg", ".bmp",
             ".wav", ".mp3", ".ogg", ".flac", ".m4a",
             ".ttf", ".otf", ".woff", ".woff2", ".mp4", ".webm", ".mkv")


def clean_rel(p):
    """Fold '.' and '..' segments of a relative path. '' if it climbs above the root or lands on it.

    Walks SEGMENTS rather than comparing string prefixes, so a sibling whose name merely extends
    this folder's ("NightMare" beside "Night") can never come out of it.
    """
    out = []
    for seg in p.split("/"):
        if seg in ("", "."):
            continue
        if seg == "..":
            if not out:
                return ""
            out.pop()
            continue
        out.append(seg)
    return "/".join(out)


def theme_asset(p):
    """(ok, detail). ok=False means the app will refuse this path; detail says why, or is the
    cleaned relative path when ok=True."""
    if not p:
        return False, "empty"
    if "://" in p:
        return False, "remote URL - ship the file in the theme folder instead"
    if "\\" in p:
        return False, "backslash - use '/' (refused on every platform, not just Windows)"
    if ":" in p:
        return False, "colon - drive-relative or a URL scheme"
    if p.startswith("/"):
        return False, "absolute path - it only exists on the author's machine"
    rel = clean_rel(p)
    if not rel:
        return False, "leaves the theme's own folder"
    return True, rel


def collect(theme):
    """(json_path, value, kind) for every asset path a theme.json declares."""
    found = []

    def add(where, value, kind="path"):
        if isinstance(value, str) and value:
            found.append((where, value, kind))

    for view_name, view in (theme.get("views") or {}).items():
        if not isinstance(view, dict):
            continue
        bg = view.get("background")
        if isinstance(bg, dict):
            add("views.%s.background.image" % view_name, bg.get("image"))
        for i, el in enumerate(view.get("elements") or []):
            if not isinstance(el, dict):
                continue
            where = "views.%s.elements[%d](%s)" % (view_name, i, el.get("type", "?"))
            for key in ("path", "fontFile", "image"):
                add("%s.%s" % (where, key), el.get(key))
            fb = el.get("fallback")
            if isinstance(fb, str) and fb:
                is_role = fb in ROLE_WORDS or ("/" not in fb and "." not in fb)
                add("%s.fallback" % where, fb, "role" if is_role else "path")

    sounds = theme.get("sounds")
    if isinstance(sounds, dict):
        for k, v in sounds.items():
            if k != "volume":
                add("sounds.%s" % k, v)
    add("music", theme.get("music"))
    return found


def all_strings(o, path=""):
    if isinstance(o, dict):
        for k, v in o.items():
            for r in all_strings(v, "%s.%s" % (path, k)):
                yield r
    elif isinstance(o, list):
        for i, v in enumerate(o):
            for r in all_strings(v, "%s[%d]" % (path, i)):
                yield r
    elif isinstance(o, str):
        yield path, o


# --- the case table, shared with the app's probes -------------------------------------------------
SELF_TEST = [
    (r"bg.jpg", True), (r"art/icons/movie.png", True), (r"art/../bg.jpg", True),
    (r"./bg.jpg", True), (r"art//bg.jpg", True), (r"sounds/move.wav", True),
    (r"../Channels/bg.jpg", False), (r"../../../secret.png", False),
    (r"..", False), (r".", False),
    (r"../NightMare/bg.jpg", False), (r"art/../../NightMare/bg.jpg", False),
    (r"..\..\secret.png", False), (r"art\bg.jpg", False), (r"C:secret.png", False),
    (r"https://attacker.example/x.png", False), (r"http://a/b.png", False),
    (r"file:///C:/Users/x/secret.png", False),
    (r"/etc/passwd", False), (r"C:/Users/x/secret.png", False),
    (r"/C:/app/themes2/Night/bg.jpg", False),
    (r"", False),
]


def self_test():
    bad = 0
    for p, want in SELF_TEST:
        if theme_asset(p)[0] != want:
            print("SELF-TEST FAIL: %r -> %s, expected %s" % (p, theme_asset(p)[0], want))
            bad += 1
    if bad:
        print("\n%d case(s) disagree with the app's rule. This gate is NOT trustworthy until the\n"
              "table above and theme_asset() are brought back in line with ThemeAssetPath.h /\n"
              "Theme.js in the EverythingBox repo." % bad)
        return False
    return True


def main(argv):
    if not self_test():
        return 2
    if "--self-test" in argv:
        print("self-test: all %d cases match the app's rule" % len(SELF_TEST))
        return 0

    root = os.path.normpath(THEMES)
    if not os.path.isdir(root):
        print("no themes2/ directory at %s" % root)
        return 2

    problems = 0
    for name in sorted(d for d in os.listdir(root) if os.path.isdir(os.path.join(root, d))):
        tj = os.path.join(root, name, "theme.json")
        if not os.path.isfile(tj):
            print("%s: no theme.json" % name)
            problems += 1
            continue
        try:
            with open(tj, encoding="utf-8") as f:
                theme = json.load(f)
        except ValueError as e:
            print("%s: theme.json is not valid JSON - %s" % (name, e))
            problems += 1
            continue

        rows = collect(theme)
        # Completeness guard: anything that LOOKS like a file but no rule collected is a field this
        # gate does not know about. Report it rather than let the theme through unchecked.
        collected = {v for _, v, _ in rows}
        for where, v in all_strings(theme):
            if v.lower().endswith(ASSET_EXT) and v not in collected:
                print("%s: %s = %r looks like a file but is in a field this gate does not check.\n"
                      "    Add it to collect() (or confirm the app does not resolve it)." % (name, where, v))
                problems += 1

        for where, value, kind in rows:
            ok, detail = theme_asset(value)
            if kind == "role":
                continue  # an artwork role, resolved from item metadata - not a path
            if not ok:
                print("%s: %s = %r\n    REFUSED by the app: %s" % (name, where, value, detail))
                problems += 1
                continue
            if not os.path.isfile(os.path.join(root, name, detail.replace("/", os.sep))):
                print("%s: %s = %r\n    resolves, but no such file in the theme folder "
                      "(check spelling and CASE - themes are served to case-sensitive systems)"
                      % (name, where, value))
                problems += 1

    if problems:
        print("\n%d problem(s). See THEME_FORMAT.md, 'Where your files may live'." % problems)
        return 1
    print("theme assets: every declared path stays inside its own theme folder and exists")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
