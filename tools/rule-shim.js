// Run the APP'S OWN themeAsset() against a list of candidate paths.
//
// Theme.js is a QML JS library: plain ES5 except for the `.pragma` / `.import` directives at the
// top, which the QML engine consumes and a bare JS parser does not. They are blanked (not dropped)
// so any error line number still points at the real line. This is the same treatment the app's own
// probe_themeview gives the file before evaluating it, for the same reason.
//
// stdin : {"rule": "<path to Theme.js>", "base": "<sentinel>", "paths": ["bg.jpg", ...]}
// stdout: {"ok": true, "results": {"bg.jpg": "<sentinel>/bg.jpg", "../x": ""}}
// A failure to load or a missing themeAsset is reported as ok:false with a reason — never as an
// empty result set, which would read as "every path was refused" and pass a broken gate as a strict one.
'use strict';
const fs = require('fs');
const vm = require('vm');

let input = '';
process.stdin.on('data', d => input += d);
process.stdin.on('end', () => {
    let req;
    try { req = JSON.parse(input); }
    catch (e) { out({ ok: false, reason: 'bad request json: ' + e.message }); return; }

    let src;
    try { src = fs.readFileSync(req.rule, 'utf8'); }
    catch (e) { out({ ok: false, reason: 'cannot read rule file: ' + e.message }); return; }

    const cleaned = src.split('\n')
        .map(l => (/^\s*\.(pragma|import)\b/.test(l) ? '' : l))
        .join('\n');

    const ctx = { console: console };
    try { vm.runInNewContext(cleaned, ctx, { filename: 'Theme.js' }); }
    catch (e) { out({ ok: false, reason: 'Theme.js did not evaluate: ' + e.message }); return; }

    if (typeof ctx.themeAsset !== 'function') {
        out({ ok: false, reason: 'Theme.js defines no themeAsset() — the app renamed or moved the rule' });
        return;
    }

    const results = {};
    for (const p of req.paths) {
        try { results[p] = ctx.themeAsset(req.base, p); }
        catch (e) { out({ ok: false, reason: 'themeAsset threw on ' + JSON.stringify(p) + ': ' + e.message }); return; }
    }
    out({ ok: true, results: results });
});

function out(o) { process.stdout.write(JSON.stringify(o)); }
