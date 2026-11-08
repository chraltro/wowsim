# Build /home/claude/data/items_forever.json from the wowsims/forever item DB (primary),
# QuestieDB-Forever (quest levels/zones), Wowhead Forever tooltips (drop chance, effect text, requirements)
# and Warcraft DB Forever (recipe skill, vendor cost, crowd-sourced drop chance).
import json, os, re, html, glob, collections, time

R = '/home/claude/data/repos/wowsims-forever/assets/'
C = '/home/claude/cache/'
db = json.load(open(R + 'database/db.json'))
lo = json.load(open(R + 'database/leftover_db.json'))
al = {it['id']: it for it in json.load(open(R + 'db_inputs/atlasloot_db.json'))['items']}
qs = {it['id']: it for it in json.load(open(R + 'db_inputs/questie_db.json'))['items']}
qf = json.load(open(C + 'questie_forever.json'))
QUESTS = {int(k): v for k, v in qf['quests'].items()}
QNPCS = {int(k): v for k, v in qf['npcs'].items()}

items = {}
for it in lo['items']:
    it['_db'] = 'leftover_db.json'; items[it['id']] = it
for it in db['items']:
    it['_db'] = 'db.json'; items[it['id']] = it

ZONES = {z['id']: z['name'] for z in db['zones']}
for z in json.load(open(R + 'db_inputs/atlasloot_db.json'))['zones']:
    ZONES.setdefault(z['id'], z['name'])
NPCS = {}
for src in (json.load(open(R + 'db_inputs/questie_db.json'))['npcs'], json.load(open(R + 'db_inputs/atlasloot_db.json'))['npcs'], db['npcs']):
    for n in src: NPCS[n['id']] = n
FACTIONS = {f['id']: f['name'] for f in db['factions'] + lo['factions']}
DUNGEON_ZONES = {209, 491, 717, 718, 719, 721, 722, 796, 1176, 1337, 1477, 1581, 1583, 1584, 2017, 2057, 2100, 2437, 2557, 16919, 17191, 16620}
RAID_ZONES = {1977, 2159, 2677, 2717, 3428, 3429, 3456, 16076}
QUEST_SORTS = {-364: 'Darkmoon Faire', -284: 'Special', -1: 'Epic', -101: 'Fishing', -181: 'Alchemy', -121: 'Blacksmithing',
               -182: 'Leatherworking', -201: 'Engineering', -264: 'Tailoring', -304: 'Cooking', -324: 'First Aid',
               -82: 'Shaman', -365: "Ahn'Qiraj War", -366: 'Lunar Festival', -22: 'Seasonal', -25: 'Battlegrounds'}

AREA = {1: 'Forest/Grassland', 2: 'Mountainous', 3: 'Snowy', 4: 'Desert', 5: 'Swamp', 6: 'Wasteland', 7: 'Haunted', 8: 'Cavernous', 9: 'Volcanic', 10: 'Strongholds/Cities'}
STAT = {0: 'str', 1: 'agi', 2: 'sta', 3: 'int', 4: 'healing', 5: 'spellDamage', 6: 'arcaneDamage', 7: 'fireDamage',
        8: 'frostDamage', 9: 'holyDamage', 10: 'natureDamage', 11: 'shadowDamage', 12: 'spellPen', 13: 'spi',
        14: 'ap', 15: 'rangedAp', 16: 'feralAp', 17: 'hitRating', 18: 'critRating', 19: 'hasteRating', 20: 'armorPen',
        21: 'expertiseRating', 22: 'defenseRating', 23: 'blockRating', 24: 'blockValue', 25: 'dodgeRating',
        26: 'parryRating', 27: 'armor', 28: 'bonusArmor', 29: 'health', 30: 'mana', 31: 'mp5', 32: 'arcaneRes',
        33: 'fireRes', 34: 'frostRes', 35: 'natureRes', 36: 'shadowRes'}
TYPE = {1: 'Head', 2: 'Neck', 3: 'Shoulder', 4: 'Back', 5: 'Chest', 6: 'Wrist', 7: 'Hands', 8: 'Waist', 9: 'Legs',
        10: 'Feet', 11: 'Finger', 12: 'Trinket', 13: 'Weapon', 14: 'Ranged/Relic'}
ARMOR = {0: None, 1: 'Cloth', 2: 'Leather', 3: 'Mail', 4: 'Plate'}
WEAPON = {1: 'Axe', 2: 'Dagger', 3: 'Fist Weapon', 4: 'Mace', 5: 'Held In Off-hand', 7: 'Shield', 8: 'Staff'}
HAND = {1: 'Main Hand', 2: 'One-Hand', 3: 'Off Hand', 4: 'Two-Hand'}
PROF = {1: 'Alchemy', 2: 'Blacksmithing', 3: 'Enchanting', 4: 'Engineering', 5: 'Herbalism', 6: 'Inscription',
        8: 'Leatherworking', 9: 'Mining', 10: 'Skinning', 11: 'Tailoring'}
REP = {1: 'Hated', 2: 'Hostile', 3: 'Unfriendly', 4: 'Neutral', 5: 'Friendly', 6: 'Honored', 7: 'Revered', 8: 'Exalted'}
SIDE = {0: 'Both', 1: 'Alliance', 2: 'Horde'}
QUAL = {2: 'Uncommon', 3: 'Rare', 4: 'Epic', 5: 'Legendary'}
PVP_A = {'Private': 1, 'Corporal': 2, 'Sergeant': 3, 'Master Sergeant': 4, 'Sergeant Major': 5, 'Knight': 6,
         'Knight-Lieutenant': 7, 'Knight-Captain': 8, 'Knight-Champion': 9, 'Lieutenant Commander': 10,
         'Commander': 11, 'Marshal': 12, 'Field Marshal': 13, 'Grand Marshal': 14}
PVP_H = {'Scout': 1, 'Grunt': 2, 'Senior Sergeant': 4, 'First Sergeant': 5, 'Stone Guard': 6, 'Blood Guard': 7,
         'Legionnaire': 8, 'Centurion': 9, 'Champion': 10, 'Lieutenant General': 11, 'General': 12, 'Warlord': 13,
         'High Warlord': 14}


def wh_lines(i):
    p = f'{C}wh/{i}.json'
    if not os.path.exists(p): return None
    d = json.load(open(p))
    if '__404__' in d: return None
    t = d['tooltip']
    t = re.sub(r'<br\s*/?>', '\n', t); t = re.sub(r'</(tr|div|table)>', '\n', t)
    t = re.sub(r'<[^>]+>', ' ', t); t = html.unescape(t)
    return [l for l in (re.sub(r'\s+', ' ', x).strip() for x in t.split('\n')) if l]


def wh_parse(lines):
    o = {'effects': [], 'setBonuses': [], 'requires': [], 'stats': collections.Counter(), 'setName': None}
    for l in lines:
        l2 = l.replace(' .', '.').replace(' %', '%')
        l2 = re.sub(r'\+ (\d)', r'+\1', l2)
        if l2.startswith(('Equip:', 'Use:', 'Chance on hit:')) or re.match(r'^Restores \+?\d+ mana per 5 sec', l2):
            o['effects'].append(l2)
            if l2.startswith(('Use:', 'Chance on hit:')):
                continue
            m = re.search(r'Increases healing done by up to (\d+) and damage done by up to (\d+)', l2)
            if m: o['stats']['healing'] += int(m.group(1)); o['stats']['spellDamage'] += int(m.group(2))
            m = re.search(r'Increases damage and healing done by magical spells and effects by up to (\d+)', l2)
            if m: o['stats']['healing'] += int(m.group(1)); o['stats']['spellDamage'] += int(m.group(1))
            m = re.search(r'Increases healing done by (?:magical )?spells and effects by up to (\d+)', l2)
            if m: o['stats']['healing'] += int(m.group(1))
            m = re.search(r'Restores \+?(\d+) mana per 5 sec', l2)
            if m: o['stats']['mp5'] += int(m.group(1))
            m = re.search(r'critical strike by ([\d.]+)%', l2)
            if m: o['stats']['critPct'] += float(m.group(1))
            m = re.search(r'chance to hit by ([\d.]+)%', l2)
            if m: o['stats']['hitPct'] += float(m.group(1))
            m = re.search(r'\+(\d+) Attack Power\.?$', l2) or re.search(r'Increases attack power by (\d+)\.?$', l2)
            if m: o['stats']['ap'] += int(m.group(1))
        elif re.match(r'^\(\d\) Set ?:', l2):
            o['setBonuses'].append(re.sub(r'Set ?:', 'Set:', l2))
        elif l2.startswith('Requires') and not l2.startswith('Requires Level'):
            o['requires'].append(l2)
        elif l2.startswith('Dropped by:'):
            o['droppedBy'] = l2.split(':', 1)[1].strip()
        elif l2.startswith('Drop Chance:'):
            m = re.search(r'([\d.]+)%', l2)
            if m: o['dropChancePct'] = float(m.group(1))
        else:
            m = re.match(r'^\+ ?(\d+) (Stamina|Intellect|Spirit|Strength|Agility)\b', l2)
            if m: o['stats'][{'Stamina': 'sta', 'Intellect': 'int', 'Spirit': 'spi', 'Strength': 'str', 'Agility': 'agi'}[m.group(2)]] += int(m.group(1))
            m = re.match(r'^(\d+) - (\d+) Damage', l2)
            if m: o['wmin'] = int(m.group(1)); o['wmax'] = int(m.group(2))
    return o


def wdb(i):
    p = f'{C}items/{i}.json'
    return json.load(open(p)) if os.path.exists(p) else None


def spell_skill(sid):
    p = f'{C}spell/{sid}.json'
    if not os.path.exists(p): return None, None
    d = json.load(open(p))
    if '__404__' in d or 'data' not in d: return None, None
    prof = d['data'].get('profession') or ''
    m = re.search(r'>([^<(]+)\((\d+)\)<', prof)
    focus = d['data'].get('requires_focus')
    return (int(m.group(2)) if m else None), focus


def drop_source(s, it, wh, wd):
    z = s.get('zoneId'); n = s.get('npcId')
    out = {'type': 'drop'}
    if n:
        npc = NPCS.get(n) or {}
        out['npcId'] = n; out['npc'] = npc.get('name') or (QNPCS.get(n) or {}).get('name')
        z = z or npc.get('zoneId')
        qn = QNPCS.get(n)
        if qn: out['npcLevel'] = qn.get('maxLevel'); out['npcRank'] = {0: 'normal', 1: 'elite', 2: 'rare elite', 3: 'boss', 4: 'rare'}.get(qn.get('rank'), qn.get('rank'))
    if s.get('otherName'): out['other'] = s['otherName']
    out['zoneId'] = z; out['zone'] = ZONES.get(z)
    diff = s.get('difficulty')
    out['instanceType'] = 'raid' if (diff == 2 or z in RAID_ZONES) else 'dungeon' if (diff == 1 or z in DUNGEON_ZONES) else ('world' if z or n else 'world drop')
    if s.get('category'): out['category'] = s['category']
    # provenance
    prov = []
    if any('drop' in x and x['drop'].get('npcId') == n and (x['drop'].get('zoneId') in (z, None)) for x in (qs.get(it['id']) or {}).get('sources', [])): prov.append('questie-forever')
    if any('drop' in x and x['drop'].get('npcId') == n and x['drop'].get('zoneId') == s.get('zoneId') for x in (al.get(it['id']) or {}).get('sources', [])): prov.append('atlasloot-mop')
    out['provenance'] = prov or ['wowsims-db']
    # drop chance
    if wh and wh.get('droppedBy') and out.get('npc') and wh['droppedBy'].lower() == out['npc'].lower():
        out['dropChancePct'] = wh.get('dropChancePct'); out['dropChanceSource'] = 'wowhead-forever tooltip'
    elif wd:
        for r in wd.get('tabs', {}).get('dropped-by', []):
            if r.get('source_id') == n and r.get('chance') is not None:
                out['dropChancePct'] = r['chance']; out['dropChanceSource'] = f"warcraftdb-forever (sample {r.get('sample')})"
    return out


def build(ids_file='target_ids.json'):
    ids = json.load(open(C + ids_file))
    res = []; excluded = collections.Counter()
    for i in ids:
        it = items[i]
        so = it['scalingOptions'].get('0') or list(it['scalingOptions'].values())[0]
        st = {STAT[int(k)]: v for k, v in so.get('stats', {}).items() if int(k) in STAT}
        t = it.get('type'); wt = it.get('weaponType'); ht = it.get('handType')
        if t == 13:
            slot = 'Shield' if wt == 7 else ('Held In Off-hand' if wt == 5 else HAND.get(ht, 'Weapon'))
        elif t == 14:
            slot = 'Relic (Totem)'
        else:
            slot = TYPE.get(t)
        lines = wh_lines(i); wh = wh_parse(lines) if lines else None
        wd = wdb(i)
        rec = {'id': i, 'name': it['name'], 'slot': slot, 'itemType': TYPE.get(t),
               'armorType': ARMOR.get(it.get('armorType', 0)) if t not in (2, 11, 12, 13, 14) or it.get('armorType') else None,
               'weaponType': WEAPON.get(wt) if t == 13 else ('Totem' if t == 14 else None),
               'hand': HAND.get(ht) if t == 13 and wt not in (5, 7) else None,
               'reqLvl': it.get('reqLvl'), 'ilvl': so.get('ilvl'), 'quality': it.get('quality'), 'qualityName': QUAL.get(it.get('quality')),
               'unique': bool(it.get('unique')), 'limitCategory': it.get('limitCategory'),
               'stats': st,
               'derived': {'hitPct': round(st.get('hitRating', 0) / 10.0, 2), 'critPct': round(st.get('critRating', 0) / 14.0, 2),
                           'hastePct': round(st.get('hasteRating', 0) / 10.0, 2)},
               'areaStats': [{'areaType': AREA.get(a.get('areaType'), a.get('areaType')), 'stats': {STAT[int(k)]: v for k, v in a.get('stats', {}).items() if int(k) in STAT}} for a in so.get('areaStats', [])] or None,
               'setName': it.get('setName'), 'setId': it.get('setId'),
               'classAllowlist': it.get('classAllowlist'), 'requiredProfession': PROF.get(it.get('requiredProfession')) if it.get('requiredProfession') else None,
               'factionRestriction': {1: 'Alliance', 2: 'Horde'}.get(it.get('factionRestriction')),
               'randomSuffix': bool(it.get('randomSuffixOptions')),
               'phase': it.get('phase'), 'dbFile': it['_db']}
        if t == 13 and wt not in (5, 7):
            rec['weapon'] = {'min': so.get('weaponDamageMin'), 'max': so.get('weaponDamageMax'), 'speed': it.get('weaponSpeed'),
                             'dps': round(so['unroundedDps'], 2) if so.get('unroundedDps') else None}
            if so.get('reducedCasterWeaponDamage'): rec['weapon']['reducedCaster'] = so['reducedCasterWeaponDamage']
        rec['effectsSim'] = [{'name': e.get('buffName'), 'spellId': e.get('buffId'), 'kind': 'onUse' if 'onUse' in e else ('proc' if 'proc' in e else 'aura'),
                              'cooldownMs': (e.get('onUse') or {}).get('cooldownMs'), 'ppm': (e.get('proc') or {}).get('ppm'),
                              'durationMs': e.get('effectDurationMs')} for e in it.get('itemEffects', [])]
        if wh:
            rec['effectsText'] = wh['effects']; rec['setBonuses'] = wh['setBonuses']; rec['requiresText'] = wh['requires']
        # sources
        srcs = []
        for s in it.get('sources', []):
            if 'drop' in s:
                srcs.append(drop_source(s['drop'], it, wh, wd))
            elif 'quest' in s:
                q = s['quest']; side = SIDE.get(q.get('faction', 0), 'Both')
                qq = QUESTS.get(q.get('id')) or {}
                shaman_q = side == 'Horde' and qq.get('requiredClasses') == 64
                if side == 'Horde' and not shaman_q: excluded['horde quest source'] += 1; continue
                zs = qq.get('zoneOrSort')
                zname = ZONES.get(zs) if isinstance(zs, int) and zs > 0 else QUEST_SORTS.get(zs)
                srcs.append({'type': 'quest', 'questId': q.get('id'), 'quest': q.get('name'), 'side': side,
                             'questLevel': qq.get('questLevel'), 'questMinLevel': qq.get('requiredLevel'),
                             'zoneOrSortId': zs, 'zone': zname, 'requiredRep': qq.get('requiredMinRep'),
                             'provenance': ['questie-forever']})
                if shaman_q:
                    excluded['horde shaman-class quest kept (side uncertain)'] += 1
                    srcs[-1]['sideNote'] = 'Questie Forever v1.0.9 lists only a Horde (Orgrimmar) version of this Shaman-only quest, a vanilla leftover. An Alliance Shaman version is not confirmed in the data.'
            elif 'crafted' in s:
                c = s['crafted']; skill, focus = spell_skill(c.get('spellId'))
                cr = {'type': 'crafted', 'profession': PROF.get(c.get('profession')), 'spellId': c.get('spellId'), 'skill': skill,
                      'provenance': ['client-db2']}
                if focus: cr['requiresFocus'] = focus
                if wd:
                    for r in wd.get('tabs', {}).get('created-by', []):
                        if r.get('ID') == c.get('spellId'): cr['reagents'] = r.get('reagents')
                srcs.append(cr)
            elif 'soldBy' in s:
                v = s['soldBy']; side = SIDE.get(v.get('faction', 0), 'Both')
                if side == 'Horde': excluded['horde vendor source'] += 1; continue
                so2 = {'type': 'vendor', 'npcId': v.get('npcId'), 'npc': v.get('npcName'), 'zoneId': v.get('zoneId'), 'zone': ZONES.get(v.get('zoneId')),
                       'side': side, 'provenance': ['questie-forever']}
                if wd:
                    for r in wd.get('tabs', {}).get('sold-by', []):
                        if r.get('npc_id') == v.get('npcId'): so2['costCopper'] = r.get('buy_price'); so2['costTokens'] = (r.get('cost') or {}).get('tokens')
                srcs.append(so2)
            elif 'rep' in s:
                r = s['rep']; side = SIDE.get(r.get('factionId', 0), 'Both')
                if side == 'Horde': excluded['horde rep source'] += 1; continue
                srcs.append({'type': 'reputation', 'factionId': r.get('repFactionId'), 'faction': FACTIONS.get(r.get('repFactionId')),
                             'standing': REP.get(r.get('repLevel')), 'side': side, 'provenance': ['client-db2']})
            elif 'pvp' in s:
                rank = None; side = None
                for title, rk in sorted(PVP_A.items(), key=lambda x: -len(x[0])):
                    if it['name'].startswith(title + "'s") or it['name'].startswith('Premier ' + title + "'s"): rank, side = rk, 'Alliance'; break
                if not rank:
                    for title, rk in sorted(PVP_H.items(), key=lambda x: -len(x[0])):
                        if it['name'].startswith(title + "'s") or it['name'].startswith('Premier ' + title + "'s"): rank, side = rk, 'Horde'; break
                if side == 'Horde' or it.get('factionRestriction') == 2: excluded['horde pvp source'] += 1; continue
                reqt = [x for x in (wh or {}).get('requires', []) if 'Requires' in x]
                srcs.append({'type': 'pvp', 'rankFromName': rank, 'side': side or 'unknown', 'requiresText': reqt,
                             'provenance': ['wowsims-db (name heuristic)']})
        # Wowhead-only drop info when no drop source in wowsims
        if wh and wh.get('droppedBy') and not any(s['type'] == 'drop' for s in srcs):
            srcs.append({'type': 'drop', 'npc': wh['droppedBy'], 'dropChancePct': wh.get('dropChancePct'), 'zone': None,
                         'instanceType': None, 'provenance': ['wowhead-forever tooltip only']})
        had_sources = bool(it.get('sources'))
        if had_sources and not srcs:
            excluded['item has Horde-only sources'] += 1; continue
        rec['sources'] = srcs
        rec['sourceTypes'] = sorted({s['type'] for s in srcs})
        # cross-check vs wowhead tooltip
        if wh:
            diffs = {}
            for k in ('int', 'spi', 'sta', 'str', 'agi', 'healing', 'mp5', 'ap'):
                a = st.get(k, 0); b = wh['stats'].get(k, 0)
                if abs(a - b) > 0.5: diffs[k] = {'wowsims': a, 'wowhead': b}
            if abs(st.get('critRating', 0) / 14 - wh['stats'].get('critPct', 0)) > 0.06: diffs['crit'] = {'wowsimsRating': st.get('critRating', 0), 'wowheadPct': wh['stats'].get('critPct', 0)}
            if abs(st.get('hitRating', 0) / 10 - wh['stats'].get('hitPct', 0)) > 0.06: diffs['hit'] = {'wowsimsRating': st.get('hitRating', 0), 'wowheadPct': wh['stats'].get('hitPct', 0)}
            if 'weapon' in rec and wh.get('wmin') is not None and (rec['weapon']['min'] != wh['wmin'] or rec['weapon']['max'] != wh['wmax']):
                diffs['weapon'] = {'wowsims': [rec['weapon']['min'], rec['weapon']['max']], 'wowhead': [wh['wmin'], wh['wmax']]}
            rec['crossCheckWowhead'] = 'match' if not diffs else diffs
        else:
            rec['crossCheckWowhead'] = 'no wowhead tooltip'
        res.append(rec)
    return res, excluded


if __name__ == '__main__':
    res, excluded = build()
    meta = {
        'generated': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
        'scope': 'Items a level-60 Alliance Shaman can equip; quality>=2; reqLvl 40-60, or no reqLvl with ilvl>=35. Cloth/leather/mail armor, back/neck/finger/trinket, shields, held-in-off-hand, 1H/2H axes and maces, daggers, fist weapons, staves, totems. Horde-only items and Horde-only sources removed.',
        'primarySource': {'repo': 'https://github.com/wowsims/forever', 'files': ['assets/database/db.json', 'assets/database/leftover_db.json'],
                          'commit': '125e534558b5b5588f26aae393894c6ea80bba5e', 'commitDate': '2026-11-08T11:22:51+01:00',
                          'origin': 'Generated by tools/database/gen_db from the WoW Forever client DB2 tables (product "wowf"), plus AtlasLoot (MoP data) and QuestieDB-Forever for sources'},
                          'secondarySources': {
            'questie': 'https://github.com/Questie/QuestieDB/releases/download/v1.0.9/QuestieDB-Forever.zip (quest level, min level, zone)',
            'wowhead': 'https://nether.wowhead.com/forever/tooltip/item/<id> (fetched 2026-11-08; top drop source + drop chance, effect text, set bonuses, cross-check)',
            'warcraftdb': 'https://forever.warcraftdb.com/api/data/node/item/<id>, /tab/<slug>, /api/data/node/spell/<id> (fetched 2026-11-08; recipe skill, reagents, vendor cost, crowd-sourced drop chance)'},
        'statKeys': 'stats use names resolved from proto/common.proto Stat enum. healing = bonus healing; spellDamage = bonus spell damage (all schools). hitRating/critRating/hasteRating are ratings: 10 hit = 1%, 14 crit = 1%, 10 haste = 1% at level 60 (sim/core/base_stats_auto_gen.go). Hit and crit ratings apply to melee, ranged and spells (sim/core/unit.go RatingChannelTable).',
        'excludedCounts': dict(excluded), 'count': len(res)}
    os.makedirs('/home/claude/data', exist_ok=True)
    json.dump({'meta': meta, 'items': res}, open('/home/claude/data/items_forever.json', 'w'), indent=1)
    print(len(res), dict(excluded))
