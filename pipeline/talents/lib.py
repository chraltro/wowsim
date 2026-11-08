# Shared helpers: talent ids, calculator code order, code decode/encode and leveling-order legality checks.
import json, re, unicodedata

CLIENT = '/home/claude/work/talents/client_trees.json'
SHAMAN_META = '/home/claude/wowsim/opt/talents_meta.json'
SHAMAN_TREE_KEYS = ['ele', 'enh', 'res']   # src/data.js TREE_ORDER keys
CLASSES = ['druid', 'hunter', 'mage', 'paladin', 'priest', 'rogue', 'shaman', 'warlock', 'warrior']

def slug(name):
    s = unicodedata.normalize('NFKD', name).encode('ascii', 'ignore').decode()
    s = s.replace("'", '').lower()
    return re.sub(r'[^a-z0-9]+', '_', s).strip('_')

def load_classes():
    C = json.load(open(CLIENT))['classes']
    meta = json.load(open(SHAMAN_META))
    sham_id = {(m['tree'], m['name']): m['id'] for m in meta}
    out = {}
    for cls in CLASSES:
        tabs = []
        used = set()
        for ti, tab in enumerate(C[cls]['tabs']):
            tkey = SHAMAN_TREE_KEYS[ti] if cls == 'shaman' else slug(tab['name'])
            tals = []
            for t in tab['talents']:
                if cls == 'shaman':
                    tid = sham_id[(tkey, t['name'])]
                else:
                    tid = slug(t['name'])
                    if tid in used:
                        tid = tkey + '_' + tid
                used.add(tid)
                tals.append(dict(t, id=tid, tree=tkey))
            # prereq id
            pos = {(t['row'], t['col']): t['id'] for t in tals}
            for t in tals:
                t['prereq_id'] = pos[tuple(t['prereq'])] if t['prereq'] else None
            tabs.append({'key': tkey, 'name': tab['name'], 'talent_tab_id': tab['talent_tab_id'], 'talents': tals})
        out[cls] = tabs
    return out

def code_order(tabs):
    # Calculator order: within each tree, talents by row then column (wowsims newTalentsConfig enforces the same order).
    return [[t['id'] for t in sorted(tab['talents'], key=lambda t: (t['row'], t['col']))] for tab in tabs]

def decode(tabs, code):
    code = code.strip()
    parts = code.split('-')
    order = code_order(tabs)
    alloc = {}
    errors = []
    for ti, part in enumerate(parts):
        if ti >= len(order):
            if part: errors.append('extra tree segment ' + part)
            continue
        for i, ch in enumerate(part):
            if i >= len(order[ti]):
                errors.append(f'tree {ti} has {len(part)} digits but {len(order[ti])} talents'); break
            r = int(ch)
            if r:
                alloc[order[ti][i]] = r
    return alloc, errors

def encode(tabs, alloc):
    order = code_order(tabs)
    segs = []
    for ids in order:
        s = ''.join(str(alloc.get(i, 0)) for i in ids).rstrip('0')
        segs.append(s)
    return '-'.join(segs).rstrip('-')

def by_id(tabs):
    return {t['id']: t for tab in tabs for t in tab['talents']}

def tree_of(tabs):
    return {t['id']: ti for ti, tab in enumerate(tabs) for t in tab['talents']}

def check_alloc(tabs, alloc):
    """Final-build legality: max ranks, tier gating (5 x row points above), prereq at max rank."""
    B = by_id(tabs); T = tree_of(tabs); errs = []
    for tid, r in alloc.items():
        t = B[tid]
        if r > t['max']: errs.append(f'{t["name"]} {r}/{t["max"]} over max')
        above = sum(rr for k, rr in alloc.items() if T[k] == T[tid] and B[k]['row'] < t['row'])
        if above < 5 * t['row']: errs.append(f'{t["name"]} (row {t["row"]+1}) needs {5*t["row"]} points above, has {above}')
        if t['prereq_id'] and alloc.get(t['prereq_id'], 0) < B[t['prereq_id']]['max']:
            errs.append(f'{t["name"]} needs {B[t["prereq_id"]]["name"]} at max rank')
    if sum(alloc.values()) > 51: errs.append('more than 51 points')
    return errs

def check_order(tabs, seq):
    """Point-by-point legality of an ordered list of talent ids (one point each, from level 10)."""
    B = by_id(tabs); T = tree_of(tabs); alloc = {}; errs = []
    for i, tid in enumerate(seq):
        t = B[tid]
        lvl = 10 + i
        if alloc.get(tid, 0) + 1 > t['max']:
            errs.append(f'L{lvl}: {t["name"]} over max')
        above = sum(rr for k, rr in alloc.items() if T[k] == T[tid] and B[k]['row'] < t['row'])
        if above < 5 * t['row']:
            errs.append(f'L{lvl}: {t["name"]} row {t["row"]+1} needs {5*t["row"]} above, has {above}')
        if t['prereq_id'] and alloc.get(t['prereq_id'], 0) < B[t['prereq_id']]['max']:
            errs.append(f'L{lvl}: {t["name"]} before {B[t["prereq_id"]]["name"]} is maxed')
        alloc[tid] = alloc.get(tid, 0) + 1
    return alloc, errs

def split(tabs, alloc):
    T = tree_of(tabs)
    s = [0, 0, 0]
    for k, v in alloc.items(): s[T[k]] += v
    return '/'.join(map(str, s))

def decode_wdb_ordered(tabs, t):
    """Warcraft DB / Warcraft Tavern '#?t=' build: A/B/C pick the tree, then one character per point,
    value = tier*4 + column (0-9 then a-z). Returns the ordered list of talent ids and unknown characters."""
    pos = {(ti, t2['row'], t2['col']): t2['id'] for ti, tab in enumerate(tabs) for t2 in tab['talents']}
    tree = -1; seq = []; bad = []
    for ch in t:
        if ch in 'ABC':
            tree = 'ABC'.index(ch); continue
        if tree < 0 or not re.match(r'[0-9a-z]', ch):
            bad.append(ch); continue
        v = ord(ch) - 48 if ch <= '9' else ord(ch) - 87
        k = (tree, v // 4, v % 4)
        if k in pos: seq.append(pos[k])
        else: bad.append(ch)
    return seq, bad
