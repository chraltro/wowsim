#!/usr/bin/env python3
"""Download the QuestieDB Forever release and turn it into local/cache/quests.json.

    python tools/fetch_quests.py              # download the pinned release and build the cache
    python tools/fetch_quests.py --zip X.zip  # build from a zip you already have

QuestieDB is not ours to republish (GPLv3 and "all rights reserved" parts, see its
LICENSE.md), and this repo is public. So the quest data is never committed: this
script builds it on your machine, under local/, which git ignores. tools/check.js
reads it from there.

Each quest keeps: name, level, minimum level, race and class masks, zone, the quests
that must be done first, the quests it excludes, the next quest in its chain, who
starts it and where, and Classic's XP for it (Forever pays more for many quests, so
that number is a floor, not a fact).

Standard library only.
"""
import argparse, base64, io, json, os, re, struct, sys, time, urllib.request, zipfile, zlib

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VERSION = "v1.0.9"
URL = "https://github.com/Questie/QuestieDB/releases/download/%s/QuestieDB-Forever.zip" % VERSION
OUT = os.path.join(ROOT, "local", "cache", "quests.json")


def cbor(b, i=0):
    ib = b[i]; mt = ib >> 5; ai = ib & 31; i += 1
    if mt == 7:
        if ai == 20: return False, i
        if ai == 21: return True, i
        if ai in (22, 23): return None, i
        if ai == 25: return struct.unpack(">e", b[i:i + 2])[0], i + 2
        if ai == 26: return struct.unpack(">f", b[i:i + 4])[0], i + 4
        if ai == 27: return struct.unpack(">d", b[i:i + 8])[0], i + 8
        raise ValueError("cbor simple %d" % ai)
    if ai < 24: n = ai
    elif ai == 24: n = b[i]; i += 1
    elif ai == 25: n = struct.unpack(">H", b[i:i + 2])[0]; i += 2
    elif ai == 26: n = struct.unpack(">I", b[i:i + 4])[0]; i += 4
    elif ai == 27: n = struct.unpack(">Q", b[i:i + 8])[0]; i += 8
    else: raise ValueError("cbor arg %d" % ai)
    if mt == 0: return n, i
    if mt == 1: return -1 - n, i
    if mt == 2:
        bs = b[i:i + n]
        try: return bs.decode("utf-8"), i + n
        except UnicodeDecodeError: return bs.hex(), i + n
    if mt == 3: return b[i:i + n].decode("utf-8", "replace"), i + n
    if mt == 4:
        out = []
        for _ in range(n):
            v, i = cbor(b, i); out.append(v)
        return out, i
    if mt == 5:
        out = {}
        for _ in range(n):
            k, i = cbor(b, i); v, i = cbor(b, i); out[k] = v
        return out, i
    if mt == 6: return cbor(b, i)
    raise ValueError("cbor major %d" % mt)


class Store:
    """The TOC keeps every record as '## X-<Kind>-<id>-<field>: <base64 cbor>' lines."""

    def __init__(self, toc_text):
        self.s = {}
        for line in toc_text.splitlines():
            line = line.rstrip("\r")
            if line.startswith("## X-") and ": " in line:
                k, v = line.split(": ", 1)
                self.s[k[5:]] = v

    def raw(self, key):
        v = self.s.get(key)
        if v is None: return None
        m = re.match(r"^~(\d+)~$", v)          # a long value split over numbered lines
        if m: v = "".join(self.s["%s-%d" % (key, i)] for i in range(1, int(m.group(1)) + 1))
        return base64.b64decode(v)

    def val(self, key):
        d = self.raw(key)
        return None if d is None else cbor(d)[0]

    def ids(self, kind):
        return cbor(zlib.decompress(self.raw(kind + "-IDS")))[0]

    def row(self, kind, i):
        v = self.val("%s-%d-S" % (kind, i))
        if v is None: return None
        f = {}
        if isinstance(v, list):
            for j, x in enumerate(v): f[j + 1] = x
        else:
            for k, x in v.items():
                if isinstance(k, int): f[k] = x
                elif k == "p": f["p"] = x
        return f

    def field(self, kind, i, f, idx):
        if idx in f: return f[idx]
        p = f.get("p", 0)
        if p and (p >> (idx - 1)) & 1: return self.val("%s-%d-%d" % (kind, i, idx))
        return None


def ints(v):
    """Questie stores id lists as lists, single ids or nil. Always give a list of ints."""
    if v is None: return []
    if isinstance(v, int): return [v]
    out = []
    if isinstance(v, dict): v = list(v.values())
    for x in v:
        if isinstance(x, int): out.append(x)
        elif isinstance(x, (list, dict)): out.extend(ints(x))
    return out


def zone_names(lua):
    names = {}
    for m in re.finditer(r"^\s*([A-Z][A-Z0-9_]+)\s*=\s*(\d+)\s*,", lua, flags=re.M):
        small = {"Of", "The", "And", "In"}
        words = [w.capitalize() for w in m.group(1).split("_")]
        words = [w.lower() if i and w in small else w for i, w in enumerate(words)]
        names.setdefault(int(m.group(2)), " ".join(words))
    return names


def sort_names(lua):
    """Quest categories that are not a zone (class, profession, holiday), keyed by their negative id."""
    m = re.search(r"sortKeys\s*=\s*\{(.*?)\n\}", lua, flags=re.S)
    out = {}
    for x in re.finditer(r"([A-Z][A-Z0-9_]+)\s*=\s*(-\d+)", m.group(1) if m else ""):
        out[int(x.group(2))] = " ".join(w.capitalize() for w in x.group(1).split("_"))
    return out


def dungeon_names(lua):
    return {int(m.group(1)): m.group(2) for m in re.finditer(r'\[(\d+)\]\s*=\s*\{\s*"([^"]+)"', lua)}


def classic_xp(lua):
    return {int(m.group(1)): int(m.group(2)) for m in re.finditer(r"\[(\d+)\]\s*=\s*\{\s*\d+\s*,\s*(\d+)\s*\}", lua)}


def spawn(v):
    """First spawn of an NPC or object as [zoneId, x, y]."""
    if not isinstance(v, dict): return None
    for zone, pts in v.items():
        if isinstance(pts, list) and pts and isinstance(pts[0], list) and len(pts[0]) >= 2:
            try: return [int(zone), round(float(pts[0][0]), 1), round(float(pts[0][1]), 1)]
            except (TypeError, ValueError): return None
    return None


def build(zf):
    names = zf.namelist()
    def read(suffix):
        hit = [n for n in names if n.replace("\\", "/").endswith(suffix)]
        return zf.read(hit[0]).decode("utf-8", "replace") if hit else ""
    st = Store(read("QuestieDB_Forever.toc"))
    zones = zone_names(read("enum/zones.lua"))
    dungeons = dungeon_names(read("Zones/dungeons.lua"))
    for z, n in dungeons.items(): zones[z] = n
    sorts = sort_names(read("enum/quests.lua"))
    xp = classic_xp(read("QuestXP/xpDB-classic.lua"))

    npcs = {}
    for n in st.ids("Npc"):
        f = st.row("Npc", n)
        if f is None: continue
        npcs[n] = {"name": st.field("Npc", n, f, 1), "zone": st.field("Npc", n, f, 9),
                   "spawn": spawn(st.field("Npc", n, f, 7)), "side": st.field("Npc", n, f, 13)}
    objs = {}
    try:
        for n in st.ids("Object"):
            f = st.row("Object", n)
            if f is None: continue
            objs[n] = {"name": st.field("Object", n, f, 1), "spawn": spawn(st.field("Object", n, f, 4)),
                       "zone": st.field("Object", n, f, 5)}
    except (KeyError, TypeError, zlib.error):
        pass
    items = {}
    try:
        for n in st.ids("Item"):
            f = st.row("Item", n)
            if f is not None: items[n] = st.field("Item", n, f, 1)
    except (KeyError, TypeError, zlib.error):
        pass

    quests, used_zones = {}, set()
    for q in st.ids("Quest"):
        f = st.row("Quest", q)
        if f is None: continue
        g = lambda idx: st.field("Quest", q, f, idx)
        name = g(1)
        if not name: continue
        started = g(2) or []
        if isinstance(started, dict): started = [started.get(i) for i in (1, 2, 3)]
        started = list(started) + [None] * 3
        start = None
        for kind, table, label in ((0, npcs, "npc"), (1, objs, "object")):
            for i in ints(started[kind]):
                e = table.get(i)
                if e:
                    start = {"t": label, "id": i, "name": e.get("name"), "zone": e.get("zone"), "at": e.get("spawn")}
                    if label == "npc" and e.get("side"): start["side"] = e["side"]
                    break
            if start: break
        if not start:
            it = ints(started[2])
            if it: start = {"t": "item", "id": it[0], "name": items.get(it[0])}
        zone = g(17)
        rec = {
            "n": name, "lv": g(5), "min": g(4), "races": g(6) or 0, "classes": g(7) or 0, "z": zone,
            "pre": ints(g(13)), "preAll": ints(g(12)), "excl": ints(g(16)), "next": g(22) or None,
            "skill": g(18), "flags": g(23) or 0, "special": g(24) or 0, "start": start, "xpClassic": xp.get(q),
        }
        mx = g(34)
        if isinstance(mx, int) and mx > 0: rec["max"] = mx
        quests[q] = {k: v for k, v in rec.items() if v not in (None, [], 0) or k in ("lv", "min")}
        for z in (zone, (start or {}).get("zone")):
            if isinstance(z, int) and z > 0: used_zones.add(z)
        if start and start.get("at"): used_zones.add(start["at"][0])
    return {
        "meta": {"source": URL, "version": VERSION, "built": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                 "note": "Built locally from QuestieDB. Not for redistribution. xpClassic is Classic's XP, a floor for Forever."},
        "zones": {str(z): zones[z] for z in sorted(used_zones) if z in zones},
        "dungeons": sorted(z for z in dungeons if z in used_zones),
        "sorts": {str(k): v for k, v in sorted(sorts.items())},
        "quests": {str(k): v for k, v in quests.items()},
    }


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--zip", help="use this QuestieDB-Forever.zip instead of downloading")
    ap.add_argument("--out", default=OUT)
    a = ap.parse_args()
    if a.zip:
        data = open(a.zip, "rb").read()
    else:
        print("downloading", URL, flush=True)
        req = urllib.request.Request(URL, headers={"User-Agent": "wowsim-fetch-quests"})
        try:
            data = urllib.request.urlopen(req, timeout=120).read()
        except Exception as e:  # noqa: BLE001 - any network failure gets the same advice
            sys.exit("download failed: %s\nGet the zip in a browser and pass it with --zip." % e)
    db = build(zipfile.ZipFile(io.BytesIO(data)))
    os.makedirs(os.path.dirname(a.out), exist_ok=True)
    with open(a.out, "w", encoding="utf-8") as fh:
        json.dump(db, fh, separators=(",", ":"), ensure_ascii=False)
    print("wrote %s: %d quests, %d zones, %.1f MB" % (a.out, len(db["quests"]), len(db["zones"]), os.path.getsize(a.out) / 1e6))


if __name__ == "__main__":
    main()
