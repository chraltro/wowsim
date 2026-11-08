# Step 2: add Forever items that Warcraft DB lists but the wowsims db omits (stats from the Wowhead Forever tooltip),
# for every equippable subtype. Generalizes ../supplement.py (scope 'all'): the Shaman version skipped any tooltip with a
# "Classes:" line that did not name Shaman; here that line becomes the record's classAllowlist (class ids as in wowsims).
# In:  cache/allclass/items_stage1.json   Out: cache/allclass/items_stage2.json
import json, glob, os, re, subprocess, time, collections
from common import CACHE, WORK, DBDIR, NAME_TO_ID, load_build_dataset
from crawl_wdb_allclass import SUB_ALL, SLOT_BAD

b = load_build_dataset()
allw = set(it['id'] for f in ['db.json', 'leftover_db.json'] for it in json.load(open(os.path.join(DBDIR, f)))['items'])
JUNK = re.compile(r"\[PH\]|\[TMP\]|UNUSED|DEP$|^Monster - |^Test |^QA ")
HORDE_PVP = re.compile(r"^(Premier )?(Scout|Grunt|Senior Sergeant|First Sergeant|Stone Guard|Blood Guard|Legionnaire|Centurion|Champion|Lieutenant General|General|Warlord|High Warlord)'s ")
# Warcraft DB subtype -> (armorType, weaponType, default hand); hand otherwise comes from the Warcraft DB slot
SUBMAP = {'Cloth': ('Cloth', None, None), 'Leather': ('Leather', None, None), 'Mail': ('Mail', None, None), 'Plate': ('Plate', None, None),
          'Miscellaneous': (None, None, None), 'Shield': (None, 'Shield', None), 'Dagger': (None, 'Dagger', None), 'Staff': (None, 'Staff', 'Two-Hand'),
          'One-Handed Mace': (None, 'Mace', None), 'Two-Handed Mace': (None, 'Mace', 'Two-Hand'), 'Two-Handed Axe': (None, 'Axe', 'Two-Hand'),
          'One-Handed Axe': (None, 'Axe', None), 'One-Handed Sword': (None, 'Sword', None), 'Two-Handed Sword': (None, 'Sword', 'Two-Hand'),
          'Polearm': (None, 'Polearm', 'Two-Hand'), 'Fist Weapon': (None, 'Fist Weapon', None),
          'Bow': (None, 'Bow', None), 'Gun': (None, 'Gun', None), 'Crossbow': (None, 'Crossbow', None), 'Thrown': (None, 'Thrown', None), 'Wand': (None, 'Wand', None),
          'Totem': (None, 'Totem', None), 'Idol': (None, 'Idol', None), 'Libram': (None, 'Libram', None)}
CN = '(?:Warrior|Paladin|Hunter|Rogue|Priest|Shaman|Mage|Warlock|Druid)'
CLASSES_RE = re.compile(r'Classes: (' + CN + '(?:, ' + CN + ')*)')
RANGED = {'Bow', 'Gun', 'Crossbow', 'Thrown', 'Wand'}; RELIC = {'Totem', 'Idol', 'Libram'}
SLOT_ITYPE = {'Head': 'Head', 'Neck': 'Neck', 'Shoulder': 'Shoulder', 'Back': 'Back', 'Chest': 'Chest', 'Wrist': 'Wrist', 'Hands': 'Hands', 'Waist': 'Waist',
              'Legs': 'Legs', 'Feet': 'Feet', 'Finger': 'Finger', 'Trinket': 'Trinket', 'One-Hand': 'Weapon', 'Main Hand': 'Weapon', 'Off Hand': 'Weapon',
              'Two-Hand': 'Weapon', 'Shield': 'Weapon', 'Held In Off-hand': 'Weapon', 'Ranged': 'Ranged/Relic', 'Thrown': 'Ranged/Relic', 'Relic': 'Ranged/Relic'}
DMG = re.compile(r'^(\d+)(?: - (\d+))? (?:(Arcane|Fire|Frost|Holy|Nature|Shadow) )?Damage')   # Wowhead prints one number when min == max ("46 Damage")
RACE_A = 1 | 4 | 8 | 64 | 1024; RACE_H = 2 | 16 | 32 | 128 | 512
BYNAME = {}
for nid, n in b.QNPCS.items():
    if n.get('name'): BYNAME.setdefault(n['name'].lower(), []).append((nid, n))

skipped = collections.Counter()
cands = []
for p in glob.glob(os.path.join(CACHE, 'items', '*.json')):
    d = json.load(open(p)); r = d['list']
    rl = r.get('required_level')
    if not (2 <= (r.get('quality') or 0) <= 5) or r['item_id'] in allw or not (rl is None or rl <= 60): continue
    if r.get('item_subtype') not in SUB_ALL or r.get('slot') in SLOT_BAD: skipped['subtype/slot not equippable gear'] += 1; continue
    if JUNK.search(r['name']) or HORDE_PVP.search(r['name']): skipped['placeholder or Horde PvP name'] += 1; continue
    cands.append(d)
for d in cands:   # tooltips should already be cached by wh_fetch_allclass.py; fetch any stragglers
    i = d['list']['item_id']; pth = os.path.join(CACHE, 'wh', f'{i}.json')
    if not os.path.exists(pth):
        r = subprocess.run(['curl', '-sS', '-m', '30', '-A', 'Mozilla/5.0', '-w', '\n%{http_code}', f'https://nether.wowhead.com/forever/tooltip/item/{i}'], capture_output=True, text=True)
        body, _, code = r.stdout.rpartition('\n')
        if code in ('200', '404'): open(pth, 'w').write(body if code == '200' else '{"__404__":true}')
        time.sleep(0.2)
out = []
for d in sorted(cands, key=lambda d: d['list']['item_id']):
    r = d['list']; i = r['item_id']
    lines = b.wh_lines(i)
    if not lines: skipped['no Wowhead Forever tooltip'] += 1; continue
    w = b.wh_parse(lines)
    txt = ' '.join(lines)
    if 'Requires Horde' in txt: skipped['Requires Horde (Wowhead)'] += 1; continue
    allow = None
    cl = CLASSES_RE.search(txt)   # wh_lines() can glue "Classes: X" onto the previous line, so search the joined text
    if cl:
        allow = sorted(NAME_TO_ID[n.strip().lower()] for n in cl.group(1).split(','))
    elif 'Classes:' in txt: skipped['Classes line names no known class'] += 1; continue
    armor, wtype, hand = SUBMAP[r['item_subtype']]
    slot = r.get('slot')
    if wtype and wtype not in RANGED | RELIC and not hand: hand = {'One-Hand': 'One-Hand', 'Main Hand': 'Main Hand', 'Off Hand': 'Off Hand', 'Two-Hand': 'Two-Hand'}.get(slot)
    if r['item_subtype'] == 'Miscellaneous' and slot == 'Held In Off-hand': wtype = 'Held In Off-hand'
    st = {k: v for k, v in w['stats'].items() if k not in ('critPct', 'hitPct') and v}
    if w['stats'].get('critPct'): st['critRating'] = round(w['stats']['critPct'] * 14)
    if w['stats'].get('hitPct'): st['hitRating'] = round(w['stats']['hitPct'] * 10)
    raw = json.load(open(os.path.join(CACHE, 'wh', f'{i}.json')))['tooltip']
    m = re.search(r'<!--amr-->(\d+) Armor', raw)          # base armor (../supplement.py took the first "N Armor", which can be a green "+N Armor")
    if m: st['armor'] = int(m.group(1))
    bonus = sum(int(z) for l in lines for z in re.findall(r'(?:^| )\+(\d+) Armor(?:$| )', l))
    if bonus: st['bonusArmor'] = bonus                      # green "+N Armor" = wowsims bonusArmor (tools/database/dbc/maps.go ITEM_MOD_EXTRA_ARMOR)
    for l in lines:   # resistances (../supplement.py did not read them); stat keys as in build_dataset.STAT
        for n, sch in re.findall(r'(?:^| )\+(\d+) (Arcane|Fire|Frost|Nature|Shadow) Resistance', l):
            st[sch.lower() + 'Res'] = st.get(sch.lower() + 'Res', 0) + int(n)
        for n in re.findall(r'(?:^| )\+(\d+) All Resistances', l):
            for sch in ('arcane', 'fire', 'frost', 'nature', 'shadow'): st[sch + 'Res'] = st.get(sch + 'Res', 0) + int(n)
    sp = re.search(r'Speed ([\d.]+)', txt)
    out_slot = f'Relic ({wtype})' if wtype in RELIC else ('Ranged' if wtype in RANGED else slot)
    rec = {'id': i, 'name': r['name'], 'slot': out_slot, 'itemType': SLOT_ITYPE.get(slot), 'armorType': armor if slot not in ('Back', 'Neck', 'Finger', 'Trinket') else None,
           'weaponType': wtype, 'hand': hand if wtype not in ('Shield', 'Held In Off-hand') and wtype not in RANGED | RELIC else None,
           'reqLvl': r.get('required_level'), 'ilvl': r.get('item_level'), 'quality': r.get('quality'),
           'qualityName': b.QUAL.get(r.get('quality')), 'unique': 'Unique' in txt, 'stats': st,
           'derived': {'hitPct': round(st.get('hitRating', 0) / 10, 2), 'critPct': round(st.get('critRating', 0) / 14, 2), 'hastePct': 0},
           'effectsText': w['effects'], 'setBonuses': w['setBonuses'], 'requiresText': w['requires'],
           'dataOrigin': 'NOT in wowsims db: stats parsed from Wowhead Forever tooltip; slot/ilvl/reqLvl from Warcraft DB list (lower confidence)'}
    if allow: rec['classAllowlist'] = allow; rec['classAllowlistSource'] = 'Wowhead Forever tooltip "Classes:" line'
    if wtype and wtype not in ('Shield', 'Held In Off-hand') and wtype not in RELIC:
        dm = next((DMG.match(l) for l in lines if DMG.match(l)), None)
        if dm:
            lo_, hi_ = int(dm.group(1)), int(dm.group(2) or dm.group(1))
            rec['weapon'] = {'min': lo_, 'max': hi_, 'speed': float(sp.group(1)) if sp else None,
                             'dps': round((lo_ + hi_) / 2 / float(sp.group(1)), 2) if sp else None}
            if dm.group(3): rec['weapon']['damageSchoolWowhead'] = dm.group(3)
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
    if horde_dropped and not srcs: skipped['only Horde sources'] += 1; continue
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
D = json.load(open(os.path.join(WORK, 'items_stage1.json')))
D['items'] = [x for x in D['items'] if not str(x.get('dataOrigin', '')).startswith('NOT in wowsims')] + out
D['meta']['supplement'] = (f'{len(out)} items listed by Warcraft DB Forever but absent from the wowsims db were added from Wowhead Forever tooltips (field dataOrigin marks them). '
                           'Placeholder ([PH], UNUSED, DEP, Monster) and Horde PvP names skipped. A Wowhead "Classes:" line becomes classAllowlist (classAllowlistSource marks it).')
D['meta']['supplementSkipped'] = dict(skipped)
D['meta']['count'] = len(D['items'])
json.dump(D, open(os.path.join(WORK, 'items_stage2.json'), 'w'), indent=1)
print(len(cands), len(out), dict(skipped))
