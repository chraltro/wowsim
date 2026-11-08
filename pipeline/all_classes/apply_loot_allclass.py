# Step 3: apply wowtbc.gg WoW Forever dungeon loot tables (page-data JSON, all dungeons) to the all-classes item file.
# Copy of ../all/apply_loot_all.py; changed: paths (cache/allclass/items_stage2.json -> items_stage3.json), and
# wowtbc_item() accepts every class's armor/weapon/ranged/relic types and keeps a wowtbc class list as classAllowlist.
#  - adds a boss/trash drop source when no equivalent (same npc + same dungeon) drop source exists
#  - enriches an equivalent existing source with dungeonLevel / drop chance / provenance
#  - adds items missing from the dataset when wowtbc gives full stats (dataOrigin "wowtbc")
import json, glob, os, re, collections, subprocess, time
from common import CACHE, WORK, DBDIR, NAME_TO_ID, load_build_dataset
b = load_build_dataset()
P = os.path.join(WORK, 'items_stage2.json'); POUT = os.path.join(WORK, 'items_stage3.json')
D = json.load(open(P))
ids = {i['id']: i for i in D['items']}
allw = set(it['id'] for f in ['db.json', 'leftover_db.json'] for it in json.load(open(os.path.join(DBDIR, f)))['items'])
wdb_cached = set(int(os.path.basename(p)[:-5]) for p in glob.glob(os.path.join(CACHE, 'items', '*.json')))
BLIZZ = 'https://news.blizzard.com/en-us/article/24301455'
OFFICIAL = {'Hall of Thanes': '13-18', 'Ruins of Lordaeron': '15-20', 'Excavation Site: Wetlands': '24-29', 'City of Dalaran': '28-33',
            'The Drowned City': '35-40', "Krol'dok Stronghold": '40-45', 'Alcaz Prison': '48-53', 'Blackmaw Hold': '55-60', "Shaper's Terrace": '58-60'}
ACCESS = {'Ragefire Chasm': 'Entrance is inside Orgrimmar (Horde capital); an Alliance group has to get into a hostile city to reach it.',
          'Ruins of Lordaeron': "Entrance is in the ruined city above the Undercity, Tirisfal Glades; Blizzard: 'Alliance groups will need to venture into Horde territory' (" + BLIZZ + ').'}
SKIP_FILES = {'pd_drowned.json'}   # byte-identical duplicate of pd_the-drowned-city.json


def zkey(z):
    z = re.sub(r'^the ', '', (z or '').lower()).split(':')[0].strip()
    return {"temple of atal'hakkar": 'sunken temple', 'stormwind stockade': 'stockade', 'excavation site': 'excavation site'}.get(z, z)


def same_zone(a, b_):
    """Base dungeon must match; if both names carry a wing (after ':'), the wing must match too."""
    if zkey(a) != zkey(b_): return False
    fa = re.sub(r'^the ', '', (a or '').lower()); fb = re.sub(r'^the ', '', (b_ or '').lower())
    return fa == fb if (':' in fa and ':' in fb) else True


def nkey(n): return re.sub(r'[^a-z0-9]', '', (n or '').lower())


BYNAME = collections.defaultdict(set)
for nid, n in b.QNPCS.items():
    if n.get('name'): BYNAME[nkey(n['name'])].add(nid)

NEW_DUNGEON_ZONES = {16544, 16550, 16554, 16611, 16667, 16732, 16842}
ZONE_IDS = collections.defaultdict(set)   # zkey -> wowsims zone ids
for zid, zn in b.ZONES.items():
    if zn: ZONE_IDS[zkey(zn)].add(zid)
rows = []
LOOT = os.path.join(CACHE, 'loot', 'tbc')
for f in sorted(glob.glob(os.path.join(LOOT, 'pd_*.json'))):
    if os.path.basename(f) in SKIP_FILES: continue
    slug = os.path.basename(f)[3:-5]
    pc = json.load(open(f))['result']['pageContext']
    gear = {g['id']: g for g in pc.get('gearData', [])}
    for L in pc['loot']:
        bosses = {nkey(x['name']) for x in L['bosses'] if x['name'] != 'Trash'}
        for bo in L['bosses']:
            for iid in bo['items']:
                rows.append(dict(slug=slug, dungeon=L['dungeon'], levels=L.get('levels'), new=bool(L.get('new')), boss=bo['name'], id=iid,
                                 g=gear.get(iid, {}), bosses=bosses, sets=pc.get('setsData') or []))

DLEVEL = {}
for r_ in rows:
    if r_['dungeon'] in OFFICIAL: DLEVEL[r_['dungeon']] = tuple(int(v) for v in OFFICIAL[r_['dungeon']].split('-'))
    elif r_.get('levels'): DLEVEL[r_['dungeon']] = tuple(r_['levels'])
stats = collections.Counter(); per_dungeon = collections.defaultdict(collections.Counter); name_mismatch = []; missing = {}
added_items = []


def chance_from(r):
    g = r['g']; c = g.get('drop_chance')
    if c is None: return None
    src = g.get('source')
    if r['boss'] == 'Trash':
        return round(c * 100, 2) if src and (src == 'Trash drop' or nkey(src) not in r['bosses']) else None
    return round(c * 100, 2) if src == r['boss'] else None


def other_chance(iid, npc):
    """Drop chance for this npc from the Wowhead Forever tooltip, else Warcraft DB dropped-by tab."""
    if not npc: return None, None
    lines = b.wh_lines(iid)
    if lines:
        w = b.wh_parse(lines)
        if w.get('droppedBy') and nkey(w['droppedBy']) == nkey(npc) and w.get('dropChancePct') is not None:
            return w['dropChancePct'], 'wowhead-forever tooltip'
    wd = b.wdb(iid)
    if wd:
        for t in wd.get('tabs', {}).get('dropped-by', []):
            if nkey(t.get('name')) == nkey(npc) and t.get('chance') is not None:
                return t['chance'], f"warcraftdb-forever (sample {t.get('sample')})"
    return None, None


def apply(it, r):
    url = f"https://wowtbc.gg/warcraftforever/loot-tables/dungeons/{r['slug']}/"
    trash = r['boss'] == 'Trash'
    g = r['g']
    npc = (g.get('source') if trash and g.get('source') and g.get('source') != 'Trash drop' and nkey(g['source']) not in r['bosses'] else None) if trash else r['boss']
    lv_wt = f"{r['levels'][0]}-{r['levels'][1]}" if r.get('levels') else None
    lv = OFFICIAL.get(r['dungeon'], lv_wt)
    prov = [f'wowtbc.gg loot table {url}'] + ([f"Blizzard dungeon level range {BLIZZ}"] if r['dungeon'] in OFFICIAL else [])
    ch = chance_from(r)
    zk = zkey(r['dungeon'])
    # equivalent existing drop source?
    eq = None
    for s in it['sources']:
        if s.get('type') != 'drop': continue
        if s.get('zone') is not None and not same_zone(s.get('zone'), r['dungeon']): continue
        if npc and nkey(s.get('npc')) == nkey(npc): eq = s; break
        if trash and not npc and s.get('zone') is not None and nkey(s.get('npc')) not in r['bosses']: eq = s; break
    if eq is not None:
        changed = False
        if eq.get('zone') is None:
            eq['zone'] = r['dungeon']; eq['instanceType'] = 'dungeon'; changed = True
        if eq.get('zone') != r['dungeon'] and ':' in r['dungeon'] and ':' not in (eq.get('zone') or ''):
            w = eq.setdefault('zoneWowtbc', [])
            if r['dungeon'] not in w:
                w.append(r['dungeon']); changed = True
                rng = [DLEVEL[x] for x in w if x in DLEVEL]   # level span across all wings the item is listed in
                if rng and (not eq.get('dungeonLevel') or len(w) > 1):
                    eq['dungeonLevel'] = f"{min(a_ for a_, _ in rng)}-{max(b2 for _, b2 in rng)}"
        if not eq.get('dungeonLevel') and lv:
            eq['dungeonLevel'] = lv; changed = True
        if ch is not None:
            if eq.get('dropChancePct') is None:
                eq['dropChancePct'] = ch; eq['dropChanceSource'] = 'wowtbc.gg'; changed = True
            elif abs(eq['dropChancePct'] - ch) > 0.005 and eq.get('dropChanceSource') != 'wowtbc.gg':
                eq['dropChancePctWowtbc'] = ch; changed = True
        if r['dungeon'] in ACCESS and not eq.get('accessNote'):
            eq['accessNote'] = ACCESS[r['dungeon']]; changed = True
        if prov[0] not in eq.get('provenance', []):
            eq.setdefault('provenance', []).extend(p for p in prov if p not in eq.get('provenance', [])); changed = True
        return 'enriched' if changed else 'already present'
    src = {'type': 'drop', 'npc': npc, 'zone': r['dungeon'], 'instanceType': 'dungeon', 'dropChancePct': ch, 'dungeonLevel': lv, 'provenance': prov}
    if trash: src['other'] = 'Trash'
    if ch is not None:
        src['dropChanceSource'] = 'wowtbc.gg'
        oc, osrc = other_chance(it['id'], npc)
        if oc is not None and abs(oc - ch) > 0.005: src['dropChancePctWowhead' if osrc.startswith('wowhead') else 'dropChancePctWarcraftDB'] = oc
    else:
        oc, osrc = other_chance(it['id'], npc)
        if oc is not None: src['dropChancePct'] = oc; src['dropChanceSource'] = osrc
    if lv_wt and lv_wt != lv: src['dungeonLevelWowtbc'] = lv_wt
    if npc and len(BYNAME.get(nkey(npc), ())) == 1:   # attach Questie npc only if the name is unique and its zone agrees
        nid = next(iter(BYNAME[nkey(npc)])); q = b.QNPCS[nid]; qz = q.get('zoneID')
        other_instance = qz in (b.DUNGEON_ZONES | b.RAID_ZONES | NEW_DUNGEON_ZONES) and qz not in ZONE_IDS.get(zk, set())
        if not other_instance:   # same dungeon, parent zone (e.g. Alterac Mountains for City of Dalaran) or unnamed area id
            src['npcId'] = nid; src['npcLevel'] = q.get('maxLevel')
            src['npcRank'] = {0: 'normal', 1: 'elite', 2: 'rare elite', 3: 'boss', 4: 'rare'}.get(q.get('rank'), q.get('rank'))
        else:
            src['npcZoneNote'] = f"Questie Forever v1.0.9 has one NPC named '{npc}' (id {nid}) and places it in {b.ZONES.get(qz, qz)} (another instance); this {r['dungeon']} attribution comes only from wowtbc.gg."
    if r['dungeon'] in ACCESS: src['accessNote'] = ACCESS[r['dungeon']]
    it['sources'].append(src)
    if 'drop' not in it['sourceTypes']: it['sourceTypes'] = sorted(set(it['sourceTypes']) | {'drop'})
    return 'added'


# ---- wowtbc-only items (not in wowsims db, not a Warcraft DB-cached candidate) ----
SLOT = {'head': 'Head', 'neck': 'Neck', 'shoulder': 'Shoulder', 'back': 'Back', 'chest': 'Chest', 'wrist': 'Wrist', 'hands': 'Hands', 'waist': 'Waist',
        'legs': 'Legs', 'feet': 'Feet', 'finger': 'Finger', 'trinket': 'Trinket', 'one-hand': 'One-Hand', 'main hand': 'Main Hand', 'off hand': 'Off Hand',
        'held in off-hand': 'Held In Off-hand', 'two-hand': 'Two-Hand', 'relic': 'Relic', 'ranged': 'Ranged', 'thrown': 'Ranged'}
ITYPE = {'Head': 'Head', 'Neck': 'Neck', 'Shoulder': 'Shoulder', 'Back': 'Back', 'Chest': 'Chest', 'Wrist': 'Wrist', 'Hands': 'Hands', 'Waist': 'Waist',
         'Legs': 'Legs', 'Feet': 'Feet', 'Finger': 'Finger', 'Trinket': 'Trinket', 'Relic': 'Ranged/Relic', 'Ranged': 'Ranged/Relic'}
ARM = {'cloth': 'Cloth', 'leather': 'Leather', 'mail': 'Mail', 'plate': 'Plate'}
WEAP = {'mace': 'Mace', 'axe': 'Axe', 'dagger': 'Dagger', 'fist weapon': 'Fist Weapon', 'staff': 'Staff', 'shield': 'Shield', 'sword': 'Sword', 'polearm': 'Polearm',
        'bow': 'Bow', 'gun': 'Gun', 'crossbow': 'Crossbow', 'thrown': 'Thrown', 'wand': 'Wand', 'totem': 'Totem', 'idol': 'Idol', 'libram': 'Libram'}
RANGED_T = {'bow', 'gun', 'crossbow', 'thrown', 'wand'}; RELIC_T = {'totem', 'idol', 'libram'}
QUAL = {'uncommon': 2, 'rare': 3, 'epic': 4, 'legendary': 5}
PRIM = {'stamina': 'sta', 'spirit': 'spi', 'strength': 'str', 'intellect': 'int', 'agility': 'agi', 'shadow_resistance': 'shadowRes', 'nature_resistance': 'natureRes',
        'fire_resistance': 'fireRes', 'frost_resistance': 'frostRes', 'arcane_resistance': 'arcaneRes'}
SECD = {'spell_healing': 'healing', 'spell_damage': 'spellDamage', 'mp5': 'mp5', 'attack_power': 'ap', 'defense': 'defenseRating', 'spell_penetration': 'spellPen',
        'shadow_damage': 'shadowDamage', 'fire_damage': 'fireDamage', 'frost_damage': 'frostDamage', 'nature_damage': 'natureDamage', 'arcane_damage': 'arcaneDamage',
        'block_value': 'blockValue'}   # each validated against wowsims on overlapping items (see report)


def wowtbc_item(g):
    """Return (record, None) or (None, reason)."""
    if g.get('hidden') or not g.get('rarity') or g.get('ilvl') is None: return None, 'no stats in wowtbc (hidden/undiscovered)'
    slot = SLOT.get(g.get('slot')); typ = g.get('type')
    if not slot: return None, 'slot not equippable'
    if slot == 'Ranged' and typ not in RANGED_T: return None, 'ranged slot with unknown type'
    if slot == 'Relic':
        if typ not in RELIC_T: return None, 'relic of unknown type'
        slot = f'Relic ({WEAP[typ]})'
    cls = (g.get('other_stats') or {}).get('classes')
    allow = sorted(NAME_TO_ID[c.lower()] for c in cls if c.lower() in NAME_TO_ID) if cls else None
    if cls and not allow: return None, 'class list names no known class'
    q = QUAL.get(g['rarity'])
    if not q: return None, 'quality < 2'
    lvl = (g.get('other_stats') or {}).get('min_level')
    if lvl is not None and lvl > 60: return None, 'reqLvl > 60'
    sp = g.get('special_stats') or {}
    if slot == 'Off Hand' and typ == 'shield': slot = 'Shield'
    weapon = typ in ('mace', 'axe', 'dagger', 'fist weapon', 'staff', 'sword', 'polearm') or typ in RANGED_T
    if slot in ('Head', 'Shoulder', 'Chest', 'Wrist', 'Hands', 'Waist', 'Legs', 'Feet', 'Back', 'Shield') and 'armor' not in sp: return None, 'incomplete stats (no armor value)'
    if weapon and not (sp.get('weapon_damage') and sp.get('weapon_speed')): return None, 'incomplete stats (no weapon damage)'
    if slot in ('Head', 'Shoulder', 'Chest', 'Wrist', 'Hands', 'Waist', 'Legs', 'Feet') and typ not in ARM: return None, 'armor type unknown/unusable'
    st = {}; raw = {}; eff = []
    for k, v in (g.get('primary_stats') or {}).items(): st[PRIM[k]] = st.get(PRIM[k], 0) + v
    for k, v in (g.get('secondary_stats') or {}).items():
        if k == 'spell_power': st['healing'] = st.get('healing', 0) + v; st['spellDamage'] = st.get('spellDamage', 0) + v
        elif k == 'hit': st['hitRating'] = round(v * 10)
        elif k == 'crit': st['critRating'] = round(v * 14)
        elif k in SECD: st[SECD[k]] = st.get(SECD[k], 0) + v
        elif re.match(r'^(use|equip|onhit)_\d+$', k):
            eff.append({'use': 'Use: ', 'equip': 'Equip: ', 'onhit': 'Chance on hit: '}[k.split('_')[0]] + str(v))
        else: raw[k] = v
    if 'armor' in sp: st['armor'] = sp['armor']
    if 'block' in sp: st['blockValue'] = st.get('blockValue', 0) + sp['block']
    ranged = typ in RANGED_T or typ in RELIC_T
    rec = {'id': g['id'], 'name': g['name'], 'slot': slot, 'itemType': 'Ranged/Relic' if ranged else 'Weapon' if (weapon or slot in ('Shield', 'Held In Off-hand')) else ITYPE.get(slot),
           'armorType': ARM.get(typ) if typ in ARM else None, 'weaponType': 'Held In Off-hand' if slot == 'Held In Off-hand' else WEAP.get(typ),
           'hand': slot if weapon and not ranged else None, 'reqLvl': lvl, 'ilvl': g['ilvl'], 'quality': q, 'qualityName': b.QUAL.get(q), 'unique': bool(g.get('unique')),
           'limitCategory': None, 'stats': st,
           'derived': {'hitPct': round(st.get('hitRating', 0) / 10.0, 2), 'critPct': round(st.get('critRating', 0) / 14.0, 2), 'hastePct': 0.0},
           'areaStats': None, 'setName': g.get('set'), 'setId': g.get('set_id'), 'classAllowlist': allow, 'requiredProfession': None, 'factionRestriction': None,
           'randomSuffix': False, 'phase': None, 'dbFile': None, 'effectsSim': [], 'effectsText': eff, 'setBonuses': [], 'requiresText': [],
           'bind': {'bop': 'Binds when picked up', 'boe': 'Binds when equipped'}.get(g.get('bind'), g.get('bind'))}
    if raw: rec['wowtbcUnmappedStats'] = raw
    if weapon:
        m = re.match(r'(\d+)\D+(\d+)', str(sp['weapon_damage']))
        rec['weapon'] = {'min': int(m.group(1)) if m else None, 'max': int(m.group(2)) if m else None, 'speed': float(sp['weapon_speed']),
                         'dps': float(sp['weapon_dps']) if sp.get('weapon_dps') is not None else None}
    return rec, None


def crosscheck(rec):
    lines = b.wh_lines(rec['id'])
    if not lines: return 'no wowhead tooltip'
    w = b.wh_parse(lines); st = rec['stats']; diffs = {}
    for k in ('int', 'spi', 'sta', 'str', 'agi', 'healing', 'mp5', 'ap'):
        a = st.get(k, 0); c = w['stats'].get(k, 0)
        if abs(a - c) > 0.5: diffs[k] = {'wowtbc': a, 'wowhead': c}
    if abs(st.get('critRating', 0) / 14 - w['stats'].get('critPct', 0)) > 0.06: diffs['crit'] = {'wowtbcRating': st.get('critRating', 0), 'wowheadPct': w['stats'].get('critPct', 0)}
    if abs(st.get('hitRating', 0) / 10 - w['stats'].get('hitPct', 0)) > 0.06: diffs['hit'] = {'wowtbcRating': st.get('hitRating', 0), 'wowheadPct': w['stats'].get('hitPct', 0)}
    if rec.get('weapon') and w.get('wmin') is not None and (rec['weapon']['min'] != w['wmin'] or rec['weapon']['max'] != w['wmax']):
        diffs['weapon'] = {'wowtbc': [rec['weapon']['min'], rec['weapon']['max']], 'wowhead': [w['wmin'], w['wmax']]}
    if w['effects'] and not rec['effectsText']: rec['effectsText'] = w['effects']
    if w['setBonuses']: rec['setBonuses'] = w['setBonuses']
    if w['requires']: rec['requiresText'] = w['requires']
    return 'match' if not diffs else diffs


def ensure_wh(i):
    p = os.path.join(CACHE, 'wh', f'{i}.json')
    if os.path.exists(p): return
    r = subprocess.run(['curl', '-sS', '-m', '30', '-A', 'Mozilla/5.0', '-w', '\n%{http_code}', f'https://nether.wowhead.com/forever/tooltip/item/{i}'], capture_output=True, text=True)
    body, _, code = r.stdout.rpartition('\n')
    if code in ('200', '404'): open(p, 'w').write(body if code == '200' else '{"__404__":true}')
    time.sleep(0.2)


for r in rows:
    iid = r['id']; g = r['g']
    if iid not in ids:
        if iid in missing: rec = missing[iid]
        elif iid in allw: missing[iid] = None; stats['row: item in wowsims db but outside this dataset (no class can equip / Horde-only / quality / level)'] += 1; continue
        elif iid in wdb_cached: missing[iid] = None; stats['row: Warcraft DB candidate excluded by supplement (Horde/class/placeholder/no tooltip)'] += 1; continue
        else:
            rec, why = wowtbc_item(g) if g else (None, 'no gearData entry')
            if rec is None:
                missing[iid] = None; stats[f'row: missing item not added: {why}'] += 1; continue
            if any(x['name'].lower() == rec['name'].lower() for x in D['items']):
                missing[iid] = None; stats['row: missing id but same name already in dataset (skipped)'] += 1; continue
            ensure_wh(iid)
            if b.wh_lines(iid) and 'Requires Horde' in ' '.join(b.wh_lines(iid)):
                missing[iid] = None; stats['row: missing item not added: Horde-only per Wowhead'] += 1; continue
            rec['dataOrigin'] = 'wowtbc'
            rec['dataOriginNote'] = f"NOT in wowsims db or Warcraft DB crawl: stats from wowtbc.gg page-data gearData ({r['dungeon']}); lower confidence"
            rec['sources'] = []; rec['sourceTypes'] = []
            missing[iid] = rec; D['items'].append(rec); ids[iid] = rec; added_items.append(rec)
        if missing[iid] is None: continue
    it = ids[iid]
    if g.get('name') and it['name'].lower() != g['name'].lower():
        name_mismatch.append((iid, it['name'], g['name'], r['dungeon'])); stats['row: name mismatch (skipped)'] += 1; continue
    res = apply(it, r)
    stats['source ' + res] += 1; per_dungeon[r['dungeon']][res] += 1

for rec in added_items:
    rec['crossCheckWowhead'] = crosscheck(rec)

D['meta']['lootSupplementWowtbc'] = {
    'added': '2026-11-08',
    'files': sorted(os.path.basename(f) for f in glob.glob(os.path.join(LOOT, 'pd_*.json')) if os.path.basename(f) not in SKIP_FILES),
    'urlPattern': 'https://wowtbc.gg/page-data/warcraftforever/loot-tables/dungeons/<slug>/page-data.json (page: https://wowtbc.gg/warcraftforever/loot-tables/dungeons/<slug>/)',
    'counts': dict(stats), 'itemsAddedFromWowtbc': len(added_items),
    'note': ('Boss and trash drop sources from wowtbc.gg WoW Forever loot tables, matched by item id (and exact name). A source is added only when no drop source with the same npc and dungeon exists; '
             'otherwise the existing source gets dungeonLevel / drop chance / provenance. dropChancePct = wowtbc drop_chance x 100 when given (dropChanceSource "wowtbc.gg"), else the Wowhead Forever tooltip '
             'or Warcraft DB value for the same npc, else null. dungeonLevel uses Blizzard\'s official ranges for the nine new Forever dungeons (' + BLIZZ + '), wowtbc\'s range otherwise; dungeonLevelWowtbc keeps '
             'wowtbc\'s range where it differs. "other": "Trash" marks trash drops. Items with dataOrigin "wowtbc" are not in the wowsims db or the Warcraft DB crawl; stats mapped from wowtbc keys that were checked against wowsims on overlapping items.')}
D['meta']['count'] = len(D['items'])
json.dump(D, open(POUT, 'w'), indent=1, ensure_ascii=False)
json.dump({'perDungeon': {k: dict(v) for k, v in per_dungeon.items()}, 'nameMismatch': name_mismatch, 'stats': dict(stats),
           'added': [(x['id'], x['name'], x['slot'], x['reqLvl'], x['crossCheckWowhead']) for x in added_items]},
          open(os.path.join(WORK, 'apply_loot_report.json'), 'w'), indent=1, ensure_ascii=False)
print(json.dumps(dict(stats), indent=1)); print('added items', len(added_items)); print('name mismatches', name_mismatch[:20])
for k, v in sorted(per_dungeon.items()): print(f'  {k:<32} {dict(v)}')
