#!/usr/bin/env python3
"""Compact data/items_all.json (every Alliance class, levels 1-60) into src/mc/items.js.

Same filtering and source compaction as tools/build_items.py, plus per-class usability:
"ub" maps class -> [from level (0 = always), paper-doll slots, off hand from level or 0].
"""
import json, os, re, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'tools'))
import build_items as B  # noqa: E402

SRC = os.path.join(ROOT, 'data/items_all.json')
OUT = os.path.join(ROOT, 'src/mc/items.js')
KEEP = B.KEEP + ['bonusArmor', 'blockValue', 'defenseRating', 'dodgeRating', 'parryRating', 'blockRating', 'rangedAp', 'feralAp',
                 'shadowDamage', 'fireDamage', 'frostDamage', 'arcaneDamage', 'holyDamage', 'spellPen', 'hasteRating', 'expertiseRating']
# Paper-doll slot names in the data -> the page's slot keys
PD = {'head': 'head', 'neck': 'neck', 'shoulder': 'shoulder', 'back': 'back', 'chest': 'chest', 'wrist': 'wrist', 'hands': 'hands',
      'waist': 'waist', 'legs': 'legs', 'feet': 'feet', 'finger1': 'finger1', 'finger2': 'finger2', 'trinket1': 'trinket1',
      'trinket2': 'trinket2', 'mainHand': 'mainhand', 'offHand': 'offhand', 'ranged': 'ranged'}


def main():
    d = json.load(open(SRC))
    items, sets, dropped = {}, {}, 0
    for i in d['items']:
        slots = [PD[s] for s in (i.get('equipSlots') or []) if s in PD]
        if not slots:
            continue
        raw = i.get('sources') or []
        srcs = [x for x in (B.src_compact(s) for s in raw) if x]
        if B.PVP_NAME.match(i['name']):
            srcs = [{'t': 'pvp'}] if srcs else srcs
        if raw and not srcs:
            dropped += 1
            continue
        st = {k: v for k, v in (i.get('stats') or {}).items() if k in KEEP and v}
        rec = {'n': i['name'], 'q': i['quality'], 'il': i.get('ilvl'), 'rl': i.get('reqLvl'), 's': st, 'es': slots}
        if i['slot'] == 'Two-Hand':
            rec['two'] = 1
        if i.get('armorType'):
            rec['at'] = i['armorType']
        if i.get('weaponSubtype') or i.get('weaponType'):
            rec['wt'] = i.get('weaponSubtype') or i.get('weaponType')
        if i.get('weapon'):
            rec['w'] = {'min': i['weapon']['min'], 'max': i['weapon']['max'], 'speed': i['weapon']['speed']}
        ub = {}
        for u in i.get('usableBy') or []:
            s2 = [PD[s] for s in u.get('slots') or [] if s in PD]
            ub[u['class']] = [u.get('fromLevel') or 0] + ([s2] if s2 != slots else []) + ([u['offHandFromLevel']] if u.get('offHandFromLevel') else [])
        rec['ub'] = ub
        if srcs:
            rec['src'] = srcs
        if i.get('unique'):
            rec['u'] = 1
        fx = [e for e in (i.get('effectsText') or []) if not re.match(r'^(Equip: )?(Increases healing|Restores \+?\d+ mana per 5|Increases damage and healing|Improves your chance|Increases your chance to hit|Increases damage done by|\+\d+ Attack Power)', e)]
        if fx:
            rec['fx'] = fx[:2]
        if i.get('setName'):
            rec['set'] = i['setName']
            if i['setName'] not in sets and i.get('setBonuses'):
                sets[i['setName']] = [b for b in (B.parse_bonus(t) for t in i['setBonuses']) if b]
        items[i['id']] = rec
    js = 'const ITEMS_ALL = ' + json.dumps(items, separators=(',', ':')) + ';\n'
    js += 'const SETS_ALL = ' + json.dumps(sets, separators=(',', ':')) + ';\n'
    meta = {'count': len(items), 'droppedRaidOnly': dropped, 'generated': d['meta'].get('generated')}
    js += 'const ITEMS_ALL_META = ' + json.dumps(meta) + ';\n'
    js += "if(typeof module !== 'undefined' && module.exports) module.exports = {ITEMS_ALL, SETS_ALL, ITEMS_ALL_META};\n"
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    open(OUT, 'w').write(js)
    print('items', len(items), 'sets', len(sets), 'dropped raid-only', dropped, 'bytes', len(js))


if __name__ == '__main__':
    main()
