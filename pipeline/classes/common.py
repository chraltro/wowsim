"""Shared paths and loaders for the per-class generators.

ROOT defaults to /home/claude; set WOWSIM_ROOT to move the tree. Every path below is relative to it.
"""
import csv
import json
import os
import re
import struct

ROOT = os.environ.get("WOWSIM_ROOT", "/home/claude")
P = lambda *a: os.path.join(ROOT, *a)

WS_REPO = P("data/repos/wowsims-forever")
MS_REPO = P("data/repos/mythicsim-forever-engine")
WORK = P("work/classes")
OUT = P("wowsim/data/classes")
SPELLS_JSON = P("work/classes/spells_all.json")      # parse_spells.py output (wowsims spell store)
CM_JSON = P("work/classes/cm_tables.json")          # extract_cmangos.py output
CM_INSERTS = P("ext/cmangos_tables/inserts.sql")
PES_CSV = P("ext/wago/PlayerExpectedStat_70862.csv")
AC_SQL = P("ext/ac/player_class_stats.sql")

CLASS_IDS = {"warrior": 1, "paladin": 2, "hunter": 3, "rogue": 4, "priest": 5, "shaman": 7, "mage": 8, "warlock": 9, "druid": 11}
RACE_IDS = {"human": 1, "orc": 2, "dwarf": 3, "night_elf": 4, "undead": 5, "tauren": 6, "gnome": 7, "troll": 8}

f32 = lambda x: struct.unpack('f', struct.pack('f', float(x)))[0]


def rnd(x, n=4):
    if x is None:
        return None
    x = float(x)
    return int(x) if x.is_integer() else round(x, n)


def E(L, v, status, source, **kw):
    d = {"level": L, "value": v, "status": status, "source": source}
    d.update(kw)
    return d


def cm_inserts(table):
    """Integer rows of one INSERT in ext/cmangos_tables/inserts.sql."""
    txt = open(CM_INSERTS).read()
    m = re.search(r"INSERT INTO `%s` VALUES (.*);" % table, txt)
    return [tuple(map(int, t.split(','))) for t in re.findall(r"\(([\d,-]+)\)", m.group(1))]


def pes(class_id):
    return {int(r['Level']): r for r in csv.DictReader(open(PES_CSV))
            if r['ClassID'] == str(class_id) and r['ContentSetID'] == '0'}


def ac_rows(class_id):
    """AzerothCore player_class_stats rows: (class, level, basehp, basemana, str, agi, sta, int, spi)."""
    out = {}
    for t in re.findall(r"\((\d+,\d+,[\d,]+)\)", open(AC_SQL).read()):
        v = tuple(map(int, t.split(',')))
        if v[0] == class_id:
            out[v[1]] = v
    return out


_SPELLS = None


def spells():
    global _SPELLS
    if _SPELLS is None:
        _SPELLS = json.load(open(SPELLS_JSON))
    return _SPELLS


def ladders(cls):
    """{key: (kind, [ids])} from sim/<class>/spell_data_auto_gen.go."""
    src = open(os.path.join(WS_REPO, "sim", cls, "spell_data_auto_gen.go")).read()
    out = {}
    for m in re.finditer(r"^\t(\w+):\s+spelldata\.(Ranked|Talent)\(([^)]*)\)", src, re.M):
        out[m.group(1)] = (m.group(2), [int(x) for x in m.group(3).replace(' ', '').split(',')])
    return out


def book_ranks():
    """sim/core/spelldata/book_ranks.go: {spell id: comment/name} when listed."""
    src = open(os.path.join(WS_REPO, "sim/core/spelldata/book_ranks.go")).read()
    return src


_CM = None


def cm():
    global _CM
    if _CM is None:
        _CM = json.load(open(CM_JSON))
    return _CM
