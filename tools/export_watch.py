#!/usr/bin/env python3
"""Turn ClaudeExport saves into text files.

The ClaudeExport addon cannot write files itself: a WoW addon can only put data in
its SavedVariables file, which the game writes on /reload or logout. This script
watches those files and writes each new export as a .txt.

    python tools/export_watch.py --wow "C:\\Program Files (x86)\\World of Warcraft" --out C:\\Gits\\wow\\pastes

In game: /claudeexport  (saves and reloads the UI). A file appears a second or two later:
    <out>/<Character>_<date>_<time>.txt   and   <out>/latest.txt

Standard library only. Ctrl+C to stop. --once checks a single time and exits.
"""
import argparse, re, sys, time
from pathlib import Path

STRING = r'"((?:[^"\\]|\\.)*)"'

def unescape(s):
    def rep(m):
        c = m.group(1)
        if c.isdigit():
            return chr(int(c))
        return {"n": "\n", "r": "", "t": "\t", "\n": "\n"}.get(c, c)
    # decimal escapes are bytes; pass them through latin-1 so UTF-8 sequences survive
    out = re.sub(r"\\(\d{1,3}|.)", rep, s, flags=re.S)
    try:
        return out.encode("latin-1").decode("utf-8")
    except (UnicodeEncodeError, UnicodeDecodeError):
        return out

def field(text, key):
    m = re.search(r'\["%s"\]\s*=\s*%s' % (re.escape(key), STRING), text, flags=re.S)
    return unescape(m.group(1)) if m else None

def find(wow):
    return [p for p in wow.glob("*/WTF/Account/*/*/*/SavedVariables/ClaudeExport.lua")] + \
           [p for p in wow.glob("WTF/Account/*/*/*/SavedVariables/ClaudeExport.lua")]

def check(wow, out, seen):
    wrote = []
    for p in find(wow):
        try:
            mtime = p.stat().st_mtime
            if seen.get(p) == mtime:
                continue
            raw = p.read_bytes().decode("utf-8", errors="replace")
        except OSError:
            continue          # the game is mid-write; next pass gets it
        seen[p] = mtime
        text, stamp = field(raw, "export"), field(raw, "exportTime")
        if not text or not stamp:
            continue
        char = p.parent.parent.name
        name = "%s_%s.txt" % (re.sub(r"[^\w-]", "", char), re.sub(r"[^\d]+", "-", stamp).strip("-"))
        target = out / name
        if target.exists():
            continue
        out.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding="utf-8")
        (out / "latest.txt").write_text(text, encoding="utf-8")
        wrote.append(target)
        print("wrote", target, flush=True)
    return wrote

def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--wow", default=r"C:\Program Files (x86)\World of Warcraft", help="WoW install folder")
    ap.add_argument("--out", default=r"C:\Gits\wow\pastes", help="folder for the text files")
    ap.add_argument("--once", action="store_true")
    a = ap.parse_args()
    wow, out = Path(a.wow), Path(a.out)
    if not wow.is_dir():
        sys.exit("WoW folder not found: %s (pass --wow)" % wow)
    seen = {}
    check(wow, out, seen)
    if a.once:
        return
    print("watching %s -> %s" % (wow, out), flush=True)
    if not find(wow):
        print("no ClaudeExport.lua yet: run /claudeexport in game once", flush=True)
    try:
        while True:
            time.sleep(1)
            check(wow, out, seen)
    except KeyboardInterrupt:
        pass

if __name__ == "__main__":
    main()
