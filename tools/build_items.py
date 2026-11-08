#!/usr/bin/env python3
"""Compact the Forever item dataset into the shape the simulator page embeds."""
import json, re, sys

import os
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, 'data/items_forever_all.json')
PRE = os.path.join(ROOT, 'data/presets/shaman_presets_resolved.json')
OUT = os.path.join(ROOT, 'src/items.js')

NOT_IN_FOREVER = {"Molten Core", "Blackwing Lair", "Zul'Gurub", "Ahn'Qiraj", "Ruins of Ahn'Qiraj",
                  "Temple of Ahn'Qiraj", "Naxxramas", "Gates of Ahn'Qiraj"}
NOT_IN_FOREVER_Q = NOT_IN_FOREVER | {"Blackwing Lair"}
AQ_QUESTS = {"Armaments of War","Champion's Battlegear","Stalwart's Battlegear","Veteran's Battlegear","Volunteer's Battlegear",
             "The Perfect Poison","Treasure of the Timeless One","Brann Bronzebeard's Lost Letter","Into The Maw of Madness",
             "The Only Prescription","Waking Legends","A Humble Offering"}
AQ_REP_IDS = {910, 609}
PVP_VENDORS = {"Samuel Hawke","Illiyana Moonblaze","Gaelden Hammersmith","Lieutenant Jackspring","Master Sergeant Biggins","Officer Areyn"}
PVP_FACTIONS = {"The League of Arathor","Silverwing Sentinels","Stormpike Guard"}
NOT_IN_FOREVER_REP = {"Brood of Nozdormu","Zandalar Tribe","Cenarion Circle"}
PVP_NAME = re.compile(r"^(Grand Marshal's|Field Marshal's|Marshal's|Commander's|Lieutenant Commander's|Knight-Captain's|Knight-Lieutenant's|Knight's|Sergeant Major's|Master Sergeant's|Sergeant's|Corporal's|Private's|Legionnaire's|Champion's|Blood Guard's|Warlord's|High Warlord's|General's|Lieutenant General's|Arathor|Highlander's|Defiler's|Sentinel's|Silverwing|Stormpike|Frostwolf)")
KEEP = ['int','spi','sta','str','agi','healing','spellDamage','natureDamage','mp5','critRating','hitRating','ap','armor']
SLOTMAP = {'Head':'head','Neck':'neck','Shoulder':'shoulder','Back':'back','Chest':'chest','Wrist':'wrist','Hands':'hands',
           'Waist':'waist','Legs':'legs','Feet':'feet','Finger':'finger','Trinket':'trinket','One-Hand':'mainhand',
           'Main Hand':'mainhand','Two-Hand':'mainhand','Shield':'offhand','Held In Off-hand':'offhand','Off Hand':'offhand',
           'Relic (Totem)':'relic'}

SET_PATTERNS = [
    (r'\+(\d+) Spirit', 'spi'), (r'\+(\d+) Intellect', 'int'), (r'\+(\d+) Stamina', 'sta'), (r'\+(\d+) Strength', 'str'),
    (r'\+(\d+) Agility', 'agi'), (r'\+(\d+) Attack Power', 'ap'),
    (r'[Ii]ncreases healing done by spells and effects by up to (\d+)', 'healing'),
    (r'damage done by spells and effects by up to (\d+)', 'spellDamage'),
    (r'[Ii]ncreases damage and healing done by magical spells and effects by up to (\d+)', 'both'),
    (r'[Rr]estores (\d+) mana per 5 sec', 'mp5'),
]

def parse_bonus(text):
    m = re.match(r'\((\d+)\) Set: (.*)', text)
    if not m: return None
    n, body = int(m.group(1)), m.group(2)
    st = {}
    for pat, key in SET_PATTERNS:
        for v in re.findall(pat, body):
            if key == 'both':
                st['healing'] = st.get('healing',0)+int(v); st['spellDamage'] = st.get('spellDamage',0)+int(v)
            else:
                st[key] = st.get(key,0)+int(v)
    crit = re.search(r'critical strike[^.]*by (\d+)%', body)
    if crit: st['critRating'] = st.get('critRating',0)+int(crit.group(1))*14
    return {'n':n, 's':st, 't':body, 'ok':bool(st)}

def src_compact(s):
    t = s['type']
    if t == 'drop':
        z = s.get('zone'); inst = s.get('instanceType')
        if z in NOT_IN_FOREVER: return None
        kind = 'dungeon' if inst == 'dungeon' else ('raid' if inst == 'raid' else ('npc' if (not z and not inst and s.get('npc')) else 'world'))
        r = {'t':kind, 'npc':s.get('npc'), 'z':z, 'p':s.get('dropChancePct'), 'lv':s.get('dungeonLevel')}
        if s.get('other') == 'Trash': r['trash'] = 1
        if s.get('accessNote'): r['acc'] = 1
        if s.get('zoneWowtbc'): r['wing'] = s.get('zoneWowtbc')
        return {k:v for k,v in r.items() if v is not None}
    if t == 'quest':
        if s.get('zone') in NOT_IN_FOREVER_Q: return None
        if s.get('quest') in AQ_QUESTS: return None
        rr = s.get('requiredRep')
        if isinstance(rr, list) and rr and rr[0] in AQ_REP_IDS: return None
        return {'t':'quest', 'q':s.get('quest'), 'z':s.get('zone'), 'lv':s.get('questLevel'), 'note':s.get('sideNote')}
    if t == 'crafted':
        if any(r.get('id') in {17010,17011,17012,17203,18562} for r in (s.get('reagents') or [])): return None
        return {'t':'crafted', 'prof':s.get('profession'), 'skill':s.get('skill')}
    if t == 'vendor':
        if s.get('npc') in PVP_VENDORS: return {'t':'pvp', 'npc':s.get('npc')}
        return {'t':'vendor', 'npc':s.get('npc'), 'z':s.get('zone')}
    if t == 'reputation':
        if s.get('faction') in NOT_IN_FOREVER_REP: return None
        if s.get('faction') in PVP_FACTIONS: return {'t':'pvp', 'f':s.get('faction'), 'st':s.get('standing')}
        return {'t':'rep', 'f':s.get('faction'), 'st':s.get('standing')}
    if t == 'pvp':
        return {'t':'pvp', 'rank':s.get('rankFromName')}
    return None

def main():
    d = json.load(open(SRC))
    items = {}
    sets = {}
    dropped_raid = 0
    for i in d['items']:
        slot = SLOTMAP.get(i['slot'])
        if not slot: continue
        raw = i.get('sources') or []
        srcs = [x for x in (src_compact(s) for s in raw) if x]
        if PVP_NAME.match(i['name']): srcs = [{'t':'pvp'}] if srcs else srcs
        if raw and not srcs:
            dropped_raid += 1
            continue  # only obtainable from raids that are not in Forever
        st = {k:v for k,v in (i.get('stats') or {}).items() if k in KEEP and v}
        rec = {'n':i['name'], 'sl':slot, 'q':i['quality'], 'il':i.get('ilvl'), 'rl':i.get('reqLvl'), 's':st}
        if i['slot'] == 'Two-Hand': rec['two'] = 1
        if i.get('armorType'): rec['at'] = i['armorType']
        if i.get('weaponType'): rec['wt'] = i['weaponType']
        if i.get('weapon'): rec['w'] = {'min':i['weapon']['min'], 'max':i['weapon']['max'], 'speed':i['weapon']['speed']}
        if srcs: rec['src'] = srcs
        if i.get('unique'): rec['u'] = 1
        fx = [e for e in (i.get('effectsText') or []) if not re.match(r'^(Equip: )?(Increases healing|Restores \+?\d+ mana per 5|Increases damage and healing|Improves your chance|Increases your chance to hit|Increases damage done by|\+\d+ Attack Power)', e)]
        if fx: rec['fx'] = fx[:2]
        if i.get('dataOrigin'): rec['lowconf'] = 1
        if i.get('wowheadNote'): rec['sod'] = 1
        if i.get('setName'):
            rec['set'] = i['setName']
            if i['setName'] not in sets and i.get('setBonuses'):
                sets[i['setName']] = [b for b in (parse_bonus(t) for t in i['setBonuses']) if b]
        items[i['id']] = rec
    presets = {}
    p = json.load(open(PRE))
    names = {'resto_timesaver':'Timesaver pre-raid (Resto, level 60)','resto_timesaver_l55':'Timesaver level 55 (Resto)',
             'resto_wowgg':'wow.gg Resto list (9 slots)','enh_timesaver':'Timesaver pre-raid (Enhancement)'}
    for key, label in names.items():
        if key not in p: continue
        g = {}; f = 0; t = 0
        for r in p[key]['rows']:
            iid = r.get('id')
            if iid not in items:
                st = {k:v for k,v in (r.get('stats') or {}).items() if k in KEEP and v}
                slotname = r['slot']
                sl = 'finger' if slotname.startswith('Finger') else 'trinket' if slotname.startswith('Trinket') else SLOTMAP.get(slotname, 'mainhand' if 'Hand' in slotname and 'Off' not in slotname else 'offhand' if 'Off' in slotname else slotname.lower())
                rec = {'n':r['name'], 'sl':sl, 'q':3, 'il':r.get('ilvl'), 'rl':r.get('reqLvl'), 's':st, 'scope':0}
                if r.get('weapon'): rec['w'] = {'min':r['weapon']['min'], 'max':r['weapon']['max'], 'speed':r['weapon']['speed']}
                srcs = [x for x in (src_compact(dict(x, type=x.get('type'))) for x in (r.get('source') or [])) if x]
                if srcs: rec['src'] = srcs
                if r.get('set'): rec['set'] = r['set']
                items[iid] = rec
            s = r['slot']
            if s.startswith('Finger'): k = 'finger1' if f == 0 else 'finger2'; f += 1
            elif s.startswith('Trinket'): k = 'trinket1' if t == 0 else 'trinket2'; t += 1
            elif s in ('Main Hand','Two-Hand','One-Hand'): k = 'mainhand'
            elif s in ('Off Hand','Shield','Held In Off-hand'): k = 'offhand'
            elif s == 'Relic': k = 'relic'
            else: k = s.lower()
            g[k] = iid
        presets[key] = {'label':label, 'title':p[key]['title'], 'gear':g}
    js = 'const ITEMS = ' + json.dumps(items, separators=(',',':')) + ';\n'
    js += 'const SETS = ' + json.dumps(sets, separators=(',',':')) + ';\n'
    js += 'const PRESETS = ' + json.dumps(presets, separators=(',',':')) + ';\n'
    js += 'const ITEMS_META = ' + json.dumps({'count':len(items), 'source':d['meta'].get('primarySource',{}).get('repo'), 'commit':d['meta'].get('primarySource',{}).get('commit','')[:7], 'generated':d['meta'].get('generated'), 'droppedRaidOnly':dropped_raid}) + ';\n'
    js += "if(typeof module !== 'undefined' && module.exports) module.exports = {ITEMS, SETS, PRESETS, ITEMS_META};\n"
    open(OUT,'w').write(js)
    print('items', len(items), 'sets', len(sets), 'presets', {k:len(v['gear']) for k,v in presets.items()}, 'dropped raid-only', dropped_raid, 'bytes', len(js))
    unparsed = sum(1 for s in sets.values() for b in s if not b['ok'])
    print('set bonuses not parsed:', unparsed)

if __name__ == '__main__':
    main()
