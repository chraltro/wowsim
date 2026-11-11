#!/usr/bin/env python3
"""See whether the pages Blizzard posts changes on have changed since the last look.

    python tools/watch_sources.py            # check, update docs/kb/watch_state.json, list what changed
    python tools/watch_sources.py --dry      # check and list, write nothing
    python tools/watch_sources.py --out F    # also write the list as Markdown to F (empty file when nothing changed)

The sources are in docs/kb/watch.json. A Blizzard forum thread is read through the forum's own JSON
(post count and time of the last post). Any other page is fetched and its text compared.
An "index" entry is a news index: it is read for links that carry a word (Forever), so a new article shows up as a new link.
A source seen for the first time is recorded and not reported. A source that cannot be fetched is
left as it was and named under "could not be read", so a blocked request never looks like a change.

.github/workflows/watch.yml runs this every morning and opens an issue when something changed.
Standard library only.
"""
import argparse, hashlib, html, json, os, re, sys, time, urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WATCH = os.path.join(ROOT, "docs", "kb", "watch.json")
STATE = os.path.join(ROOT, "docs", "kb", "watch_state.json")
UA = "Mozilla/5.0 (compatible; wowsim-watch; +https://github.com/chraltro/wowsim)"


def get(url, timeout=30):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept-Language": "en-US,en;q=0.8"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read().decode("utf-8", "replace")


def page_text(raw):
    """The words a reader sees: scripts, styles and tags out, whitespace collapsed."""
    raw = re.sub(r"(?is)<(script|style|noscript|svg|template)\b.*?</\1>", " ", raw)
    raw = re.sub(r"(?s)<!--.*?-->", " ", raw)
    main = re.search(r"(?is)<(main|article)\b.*?</\1>", raw)      # the article itself when the page marks it
    raw = main.group(0) if main else raw
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", raw))).strip()


def signature(src):
    if src["kind"] == "forum":
        m = re.search(r"/t/(?:[^/]+/)?(\d+)", src["url"])
        d = json.loads(get(src["url"].split("/t/")[0] + "/t/%s.json" % m.group(1)))
        return {"sig": "%s posts, last %s" % (d.get("posts_count"), d.get("last_posted_at")),
                "detail": "%s posts, last one %s" % (d.get("posts_count"), (d.get("last_posted_at") or "")[:10])}
    if src["kind"] == "index":
        # A news index: only the articles whose link carries the word we care about. A new one is a new link.
        word = src.get("match", "forever").lower()
        hrefs = sorted({h for h in re.findall(r'(?i)<a\b[^>]*href="([^"#?]+)', get(src["url"])) if word in h.lower()})
        if not hrefs: raise ValueError("no links with '%s' on the page" % word)
        return {"sig": hashlib.sha256("\n".join(hrefs).encode()).hexdigest()[:16], "detail": "%d articles" % len(hrefs), "links": hrefs}
    text = page_text(get(src["url"]))
    if len(text) < 200: raise ValueError("page came back nearly empty (%d characters)" % len(text))
    return {"sig": hashlib.sha256(text.encode()).hexdigest()[:16], "detail": "%d characters of text" % len(text)}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dry", action="store_true")
    ap.add_argument("--out")
    a = ap.parse_args()
    sources = json.load(open(WATCH, encoding="utf-8"))["sources"]
    state = json.load(open(STATE, encoding="utf-8")) if os.path.exists(STATE) else {}
    today = time.strftime("%Y-%m-%d", time.gmtime())
    changed, failed, new = [], [], []
    for src in sources:
        old = state.get(src["id"])
        try:
            now = signature(src)
        except Exception as e:  # noqa: BLE001 - one bad source must not stop the others
            failed.append((src, str(e)[:120]))
            continue
        if old is None: new.append(src)
        elif old.get("sig") != now["sig"]: changed.append((src, old, now))
        if old is None or old.get("sig") != now["sig"]:
            state[src["id"]] = {"sig": now["sig"], "detail": now["detail"], "seen": today}
            if "links" in now:
                state[src["id"]]["links"] = now["links"]
                fresh = [h for h in now["links"] if h not in (old or {}).get("links", [])]
                if old is not None and fresh: now["detail"] += ", new: " + ", ".join(fresh)
        time.sleep(1)
    lines = []
    for src, old, now in changed:
        lines.append("- **%s** changed: %s (was: %s, seen %s). Pages to revisit: %s. %s" % (
            src["title"], now["detail"], old.get("detail", "?"), old.get("seen", "?"), ", ".join(src.get("pages", [])) or "none listed", src["url"]))
    for src, old, now in changed: print("changed:", src["id"], "|", now["detail"])
    for src in new: print("recorded for the first time:", src["id"])
    for src, err in failed: print("could not be read:", src["id"], "|", err)
    if not changed: print("nothing changed among %d sources" % (len(sources) - len(failed)))
    if a.out:
        body = ""
        if changed:
            body = "Checked %s. In Claude Code, `/update-knowledge` reads these and proposes the edits.\n\n" % today + "\n".join(lines) + "\n"
            if failed: body += "\nCould not be read this time: " + ", ".join(s["title"] for s, _ in failed) + ".\n"
        open(a.out, "w", encoding="utf-8").write(body)
    if not a.dry:
        with open(STATE, "w", encoding="utf-8") as fh:
            json.dump(state, fh, indent=1, sort_keys=True); fh.write("\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
