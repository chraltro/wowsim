# Add Forever items that Warcraft DB lists but the wowsims DB omits, using the Wowhead Forever tooltip for stats.
import json, glob, os, re, subprocess, time, html, importlib.util, sys
# usage: supplement.py [dataset path] [scope]; scope '40-60' (default, original items_forever.json rule) or 'all' (reqLvl <= 60 or none)
PATH = sys.argv[1] if len(sys.argv) > 1 else '/home/claude/data/items_forever.json'
SCOPE = sys.argv[2] if len(sys.argv) > 2 else '40-60'
def in_scope(r):
    rl = r.get('required_level')
    if SCOPE == 'all': return rl is None or rl <= 60
    return (rl is not None and 40 <= rl <= 60) or (rl is None and (r.get('item_level') or 0) >= 45)
spec = importlib.util.spec_from_file_location('b', '/home/claude/scripts/build_dataset.py'); b = importlib.util.module_from_spec(spec); spec.loader.exec_module(b)
R = '/home/claude/data/repos/wowsims-forever/assets/database/'
allw = set(it['id'] for f in ['db.json', 'leftover_db.json'] for it in json.load(open(R + f))['items'])
JUNK = re.compile(r"\[PH\]|\[TMP\]|UNUSED|DEP$|^Monster - |^Test |^QA ")
HORDE_PVP = re.compile(r"^(Premier )?(Scout|Grunt|Senior Sergeant|First Sergeant|Stone Guard|Blood Guard|Legionnaire|Centurion|Champion|Lieutenant General|General|Warlord|High Warlord)'s ")
SUBMAP = {'Cloth': ('Cloth', None, None), 'Leather': ('Leather', None, None), 'Mail': ('Mail', None, None), 'Miscellaneous': (None, None, None),
          'Shield': (None, 'Shield', None), 'Dagger': (None, 'Dagger', None), 'Staff': (None, 'Staff', 'Two-Hand'), 'One-Handed Mace': (None, 'Mace', None),
          'Two-Handed Mace': (None, 'Mace', 'Two-Hand'), 'Two-Handed Axe': (None, 'Axe', 'Two-Hand'), 'One-Handed Axe': (None, 'Axe', None),
          'Fist Weapon': (None, 'Fist Weapon', None), 'Totem': (None, 'Totem', None)}
RACE_A = 1 | 4 | 8 | 64 | 1024; RACE_H = 2 | 16 | 32 | 128 | 512
BYNAME = {}
for nid, n in b.QNPCS.items():
    if n.get('name'): BYNAME.setdefault(n['name'].lower(), []).append((nid, n))
cands = []
for p in glob.glob('/home/claude/cache/items/*.json'):
    d = json.load(open(p)); r = d['list']
    if not (2 <= (r.get('quality') or 0) <= 5) or r['item_id'] in allw or not in_scope(r): continue   # quality 6 = dev/artifact items
    if JUNK.search(r['name']) or HORDE_PVP.search(r['name']): continue
    cands.append(d)
for d in cands:
    i = d['list']['item_id']; pth = f'/home/claude/cache/wh/{i}.json'
    if not os.path.exists(pth):
        r = subprocess.run(['curl', '-sS', '-m', '30', '-A', 'Mozilla/5.0', '-w', '\n%{http_code}', f'https://nether.wowhead.com/forever/tooltip/item/{i}'], capture_output=True, text=True)
        body, _, code = r.stdout.rpartition('\n')
        open(pth, 'w').write(body if code == '200' else '{"__404__":true}'); time.sleep(0.2)
out = []
for d in cands:
    r = d['list']; i = r['item_id']
    lines = b.wh_lines(i)
    if not lines: continue
    w = b.wh_parse(lines)
    txt = ' '.join(lines)
    if 'Requires Horde' in txt or re.search(r'Classes: (?!.*Shaman)', txt): continue
    armor, wtype, hand = SUBMAP.get(r['item_subtype'], (None, None, None))
    slot = r.get('slot')
    if wtype and not hand: hand = {'One-Hand': 'One-Hand', 'Main Hand': 'Main Hand', 'Off Hand': 'Off Hand', 'Two-Hand': 'Two-Hand'}.get(slot)
    st = {k: v for k, v in w['stats'].items() if k not in ('critPct', 'hitPct') and v}
    if w['stats'].get('critPct'): st['critRating'] = round(w['stats']['critPct'] * 14)
    if w['stats'].get('hitPct'): st['hitRating'] = round(w['stats']['hitPct'] * 10)
    m = re.search(r'(\d+) Armor', txt)
    if m: st['armor'] = int(m.group(1))
    sp = re.search(r'Speed ([\d.]+)', txt)
    rec = {'id': i, 'name': r['name'], 'slot': 'Relic (Totem)' if wtype == 'Totem' else slot, 'itemType': None, 'armorType': armor if slot not in ('Back', 'Neck', 'Finger', 'Trinket') else None,
           'weaponType': wtype, 'hand': hand if wtype not in ('Shield', 'Totem') else None, 'reqLvl': r.get('required_level'), 'ilvl': r.get('item_level'), 'quality': r.get('quality'),
           'qualityName': b.QUAL.get(r.get('quality')), 'unique': 'Unique' in txt, 'stats': st,
           'derived': {'hitPct': round(st.get('hitRating', 0) / 10, 2), 'critPct': round(st.get('critRating', 0) / 14, 2), 'hastePct': 0},
           'effectsText': w['effects'], 'setBonuses': w['setBonuses'], 'requiresText': w['requires'],
           'dataOrigin': 'NOT in wowsims db: stats parsed from Wowhead Forever tooltip; slot/ilvl/reqLvl from Warcraft DB list (lower confidence)'}
    if wtype and wtype not in ('Shield', 'Totem') and w.get('wmin') is not None:
        rec['weapon'] = {'min': w['wmin'], 'max': w['wmax'], 'speed': float(sp.group(1)) if sp else None,
                         'dps': round((w['wmin'] + w['wmax']) / 2 / float(sp.group(1)), 2) if sp else None}
    srcs = []
    if w.get('droppedBy'):
        srcs.append({'type': 'drop', 'npc': w['droppedBy'], 'dropChancePct': w.get('dropChancePct'), 'zone': None, 'instanceType': None, 'provenance': ['wowhead-forever tooltip only']})
    for t in d['tabs'].get('dropped-by', []):
        if t.get('name') and not any(s.get('npc') == t['name'] for s in srcs):
            srcs.append({'type': 'drop', 'npcId': t.get('source_id'), 'npc': t['name'], 'dropChancePct': t.get('chance'), 'dropChanceSource': f"warcraftdb-forever (sample {t.get('sample')})", 'provenance': ['warcraftdb-forever']})
    for t in d['tabs'].get('created-by', []):
        sk, focus = b.spell_skill(t.get('ID'))
        srcs.append({'type': 'crafted', 'spellId': t.get('ID'), 'skill': sk, 'reagents': t.get('reagents'), 'provenance': ['warcraftdb-forever']})
    horde_dropped = 0
    for t in d['tabs'].get('reward-from', []):
        if not t.get('id'): continue
        rr = (b.QUESTS.get(t.get('id')) or {}).get('requiredRaces') or 0   # Questie race mask
        side = 'Both' if rr == 0 or (rr & RACE_A and rr & RACE_H) else ('Alliance' if rr & RACE_A else 'Horde')
        if side == 'Horde': horde_dropped += 1; continue
        srcs.append({'type': 'quest', 'questId': t.get('id'), 'quest': t.get('name'), 'zone': t.get('zone'), 'side': side, 'provenance': ['warcraftdb-forever']})
    for t in d['tabs'].get('sold-by', []):
        if not t.get('npc_id'): continue
        f = (b.QNPCS.get(t.get('npc_id')) or {}).get('friendlyToFaction')   # Questie NPC faction
        rx = t.get('reaction') or ''
        if f == 'H' or (f is None and 'faction-horde' in rx and 'faction-alliance' not in rx): horde_dropped += 1; continue
        srcs.append({'type': 'vendor', 'npcId': t.get('npc_id'), 'npc': t.get('name'), 'zone': re.sub(r'<[^>]+>', '', t.get('location') or ''), 'side': {'A': 'Alliance', 'AH': 'Both'}.get(f, 'unknown'), 'costCopper': t.get('buy_price'), 'provenance': ['warcraftdb-forever']})
    if horde_dropped and not srcs: continue   # only Horde sources: excluded, as in build_dataset.py
    for s_ in srcs:
        if s_['type'] == 'drop' and not s_.get('zone') and s_.get('npc'):
            hits = [(nid, n) for nid, n in BYNAME.get(s_['npc'].lower(), [])]
            if len(hits) >= 1:
                nid, n = hits[0]; z = n.get('zoneID')
                s_['npcId'] = s_.get('npcId') or nid; s_['zoneId'] = z; s_['zone'] = b.ZONES.get(z)
                s_['instanceType'] = 'raid' if z in b.RAID_ZONES else 'dungeon' if z in b.DUNGEON_ZONES else 'world'
                s_['npcLevel'] = n.get('maxLevel')
    rec['sources'] = srcs; rec['sourceTypes'] = sorted({s['type'] for s in srcs}); rec['crossCheckWowhead'] = 'is the wowhead parse'
    out.append(rec)
D = json.load(open(PATH))
D['items'] = [x for x in D['items'] if not str(x.get('dataOrigin', '')).startswith('NOT in wowsims')] + out
D['meta']['supplement'] = f'{len(out)} items listed by Warcraft DB Forever but absent from the wowsims db were added from Wowhead Forever tooltips (field dataOrigin marks them). Placeholder ([PH], UNUSED, DEP, Monster) and Horde PvP names skipped.'
D['meta']['count'] = len(D['items'])
json.dump(D, open(PATH, 'w'), indent=1)
print(len(cands), len(out))
