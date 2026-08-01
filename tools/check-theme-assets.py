#!/usr/bin/env python3
"""Registry gate: a theme may only name asset files INSIDE its own folder.

Every path a theme.json declares — background images, element `path`/`fallback`, `fontFile`, a
particles `image`, `sounds`, `music` — is resolved by the app relative to that theme's own folder,
and the app REFUSES anything landing outside it. A refused path is not trimmed back inside; it
resolves to nothing and the element draws its placeholder or the sound stays silent. So a theme
published here naming `../OtherTheme/bg.jpg`, `C:/Users/me/art.png` or `https://my-cdn/bg.jpg`
renders blank for everyone who installs it, with nothing on screen to say why. This rejects it at
submission instead, while the author is still here to fix it.

Remote URLs deserve their own sentence, because they are the one shape that used to WORK. The app
fetched them, and stopped: a theme.json here is a third-party document, and one pulling artwork from
a server would contact that server every time somebody's home screen drew, could show different art
after review than during it, and would render blank for anyone offline. Ship the file in the folder.

THIS FILE CONTAINS NO COPY OF THE RULE.

That is the whole design. The rule lives in the app, twice (`native/src/core/ThemeAssetPath.h` and
`native/src/theme2/qml/Theme.js`), and a third hand-maintained copy here would be a gate that
silently stops matching what it gates — reporting on a rule nothing uses. Instead this fetches the
app's shipped Theme.js and RUNS IT, via node, on every invocation. The verdicts below are produced
by the same bytes the app ships, so there is nothing to drift.

What that trades away, stated plainly: this gate now needs the network and needs node, and a change
to the app's rule takes effect here the moment it lands on EverythingBox `main` — no version pin.
That is deliberate (a pin is drift with extra steps), but it means a registry PR can go red because
the app changed rather than because the theme did. The fetched file's sha256 is printed on every run
so that case is diagnosable at a glance. Every failure to obtain the real rule — no node, no network,
a Theme.js that will not evaluate, a Theme.js with no themeAsset() — exits 2 and blocks. It never
degrades to "assume fine".

Usage:
  tools/check-theme-assets.py               # fetch the rule, then gate every theme under themes2/
  tools/check-theme-assets.py --rule FILE   # use an already-fetched Theme.js (what CI does)
  tools/check-theme-assets.py --rule-check  # only prove the real rule can be obtained and run
"""
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile

try:
    from urllib.request import urlopen
except ImportError:                                     # pragma: no cover - py2 safety net
    from urllib2 import urlopen

HERE = os.path.dirname(os.path.abspath(__file__))
THEMES = os.path.normpath(os.path.join(HERE, os.pardir, "themes2"))
SHIM = os.path.join(HERE, "rule-shim.js")

RULE_URL = ("https://raw.githubusercontent.com/cubman3134/EverythingBox/main/"
            "native/src/theme2/qml/Theme.js")

# A sentinel standing in for the theme folder. themeAsset returns "<base>/<cleaned path>", so this
# is stripped back off to recover the relative path for the on-disk check. It is not a real URL and
# never touches the filesystem.
BASE = "THEMEROOT"

# Artwork ROLES the app resolves from the item's own metadata. A `fallback` naming one of these is
# not a file path — the app looks the role up first and only treats the word as a literal path when
# the item has no such art, which then just shows the placeholder. Not a break, so not gated.
ROLE_WORDS = {"poster", "box", "thumb", "hero", "banner", "logo", "fanart", "background",
              "screenshot", "image", "clearlogo", "art", "wide", "tile", "icon", "cover"}

ASSET_EXT = (".png", ".jpg", ".jpeg", ".webp", ".gif", ".svg", ".bmp",
             ".wav", ".mp3", ".ogg", ".flac", ".m4a",
             ".ttf", ".otf", ".woff", ".woff2", ".mp4", ".webm", ".mkv")

# Not a copy of the rule — a LOAD SANITY check. It asks only "is the thing we just evaluated
# actually the asset rule?", so that fetching a redirect page, an empty file or some unrelated
# refactor of Theme.js fails loudly instead of producing verdicts nobody should trust. Anything
# finer-grained would be a second implementation of the rule, which is what this design removes.
SANITY = [("bg.jpg", True), ("art/icons/movie.png", True),
          ("../Other/bg.jpg", False), ("https://example.com/x.png", False)]


class RuleError(Exception):
    pass


def fetch_rule(dest):
    """Download the app's Theme.js. Any failure raises — this never falls back to a local copy."""
    try:
        conn = urlopen(RULE_URL, timeout=30)
        data = conn.read()
    except Exception as e:
        raise RuleError("could not fetch the app's rule from %s\n    %s\n"
                        "    The gate needs the real rule and will not guess at it." % (RULE_URL, e))
    if not data:
        raise RuleError("fetched an EMPTY Theme.js from %s" % RULE_URL)
    with open(dest, "wb") as f:
        f.write(data)
    return dest


def run_rule(rule_path, paths):
    """Ask the app's own themeAsset() about each path. Returns {path: resolved-or-empty}."""
    if not shutil.which("node"):
        raise RuleError("node is not installed. This gate RUNS the app's rule rather than "
                        "reimplementing it, so node is required.")
    if not os.path.isfile(SHIM):
        raise RuleError("missing %s" % SHIM)
    req = json.dumps({"rule": rule_path, "base": BASE, "paths": list(paths)})
    try:
        proc = subprocess.Popen([shutil.which("node"), SHIM],
                                stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE)
        out, err = proc.communicate(req.encode("utf-8"), timeout=60)
    except Exception as e:
        raise RuleError("could not run the rule under node: %s" % e)
    if proc.returncode != 0:
        raise RuleError("node exited %d: %s" % (proc.returncode, err.decode("utf-8", "replace")))
    try:
        res = json.loads(out.decode("utf-8"))
    except ValueError:
        raise RuleError("the rule shim returned no usable JSON: %r" % out[:400])
    if not res.get("ok"):
        raise RuleError(res.get("reason", "the rule shim reported an unspecified failure"))
    return res["results"]


def check_sanity(rule_path):
    got = run_rule(rule_path, [p for p, _ in SANITY])
    for p, should_resolve in SANITY:
        if bool(got.get(p)) != should_resolve:
            raise RuleError(
                "the file fetched from the app does not behave like the asset rule "
                "(%r -> %r).\n    Either Theme.js changed shape, or something other than Theme.js "
                "was fetched.\n    Refusing to judge themes against it." % (p, got.get(p)))


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


def load_themes(root):
    """[(name, theme_dict)], plus a problem count for anything unreadable."""
    out, problems = [], 0
    for name in sorted(d for d in os.listdir(root) if os.path.isdir(os.path.join(root, d))):
        tj = os.path.join(root, name, "theme.json")
        if not os.path.isfile(tj):
            print("%s: no theme.json" % name)
            problems += 1
            continue
        try:
            with open(tj, encoding="utf-8") as f:
                out.append((name, json.load(f)))
        except ValueError as e:
            print("%s: theme.json is not valid JSON - %s" % (name, e))
            problems += 1
    return out, problems


def main(argv):
    explicit = None
    if "--rule" in argv:
        explicit = argv[argv.index("--rule") + 1]
    tmp = None
    try:
        if explicit:
            if not os.path.isfile(explicit):
                raise RuleError("--rule %s does not exist" % explicit)
            rule_path = explicit
        else:
            tmp = tempfile.mkdtemp()
            rule_path = fetch_rule(os.path.join(tmp, "Theme.js"))

        with open(rule_path, "rb") as f:
            digest = hashlib.sha256(f.read()).hexdigest()
        print("rule: %s\n      sha256 %s" % (RULE_URL if not explicit else rule_path, digest))
        check_sanity(rule_path)
        print("      loaded and behaves like the asset rule")

        if "--rule-check" in argv:
            return 0

        if not os.path.isdir(THEMES):
            print("no themes2/ directory at %s" % THEMES)
            return 2

        themes, problems = load_themes(THEMES)

        # One node call for every path in every theme, rather than one per path.
        rows = {name: collect(theme) for name, theme in themes}
        wanted = sorted({v for rs in rows.values() for _, v, k in rs if k != "role"})
        verdicts = run_rule(rule_path, wanted) if wanted else {}

        for name, theme in themes:
            # Completeness guard: anything that LOOKS like a file but that no rule collected sits in
            # a field this gate does not know about. Report it rather than pass the theme unchecked.
            collected = {v for _, v, _ in rows[name]}
            for where, v in all_strings(theme):
                if v.lower().endswith(ASSET_EXT) and v not in collected:
                    print("%s: %s = %r looks like a file but is in a field this gate does not "
                          "check.\n    Add it to collect() (or confirm the app does not resolve it)."
                          % (name, where, v))
                    problems += 1

            for where, value, kind in rows[name]:
                if kind == "role":
                    continue
                resolved = verdicts.get(value, "")
                if not resolved:
                    print("%s: %s = %r\n    REFUSED by the app - it leaves the theme's own folder, "
                          "is absolute, or is a remote URL.\n    See THEME_FORMAT.md, 'Where your "
                          "files may live'." % (name, where, value))
                    problems += 1
                    continue
                rel = resolved[len(BASE) + 1:] if resolved.startswith(BASE + "/") else resolved
                if not os.path.isfile(os.path.join(THEMES, name, rel.replace("/", os.sep))):
                    print("%s: %s = %r\n    resolves, but no such file in the theme folder "
                          "(check spelling and CASE - themes are served to case-sensitive systems)"
                          % (name, where, value))
                    problems += 1

        if problems:
            print("\n%d problem(s)." % problems)
            return 1
        print("theme assets: every declared path stays inside its own theme folder and exists")
        return 0

    except RuleError as e:
        print("CANNOT OBTAIN THE APP'S RULE\n    %s" % e)
        print("\nThis gate does not fall back to a local copy of the rule, because a copy is exactly\n"
              "what it exists to avoid. Fix the cause and re-run; nothing is being let through.")
        return 2
    finally:
        if tmp:
            shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
