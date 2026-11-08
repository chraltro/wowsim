# Step 1 of the merge: run the Shaman build code path (../build_dataset.py build()) on the all-classes target ids,
# then add what the Shaman build never needed: polearm/sword names, ranged and relic subtypes, ranged weapon damage.
# Class fields (usableBy, equipSlots, weaponSubtype, rangedType) are added for every record in finalize_allclass.py.
# Output: cache/allclass/items_stage1.json
import json, os, re, time
from common import WORK, SHAMAN_FILE, RT, load_build_dataset, load_wowsims_items

b = load_build_dataset()
b.QUAL[1] = 'Common'
b.DUNGEON_ZONES.update({16544, 16550, 16554, 16611, 16667, 16732, 16842})   # same additions as ../all/build_all.py
b.WEAPON.update({6: 'Polearm', 9: 'Sword'})                               # proto/common.proto WeaponType 6, 9 (not Shaman-usable, absent from build_dataset.WEAPON)
items = load_wowsims_items()
RANGED_WEAPONS = {'Bow', 'Gun', 'Crossbow', 'Thrown', 'Wand'}
SCHOOL = {0: 'Physical', 1: 'Arcane', 2: 'Fire', 3: 'Frost', 4: 'Holy', 5: 'Nature', 6: 'Shadow'}   # proto/common.proto SpellSchool
DMG = re.compile(r'^(\d+)(?: - (\d+))? (?:(Arcane|Fire|Frost|Holy|Nature|Shadow) )?Damage')   # wands carry a school ("41 - 77 Fire Damage"); min == max prints one number ("46 Damage")


def wh_weapon(i):
    lines = b.wh_lines(i) or []
    for l in lines:
        m = DMG.match(l)
        if m: return int(m.group(1)), int(m.group(2) or m.group(1)), m.group(3)
    return None


def fix_ranged(rec):
    it = items[rec['id']]
    rt = RT.get(it.get('rangedWeaponType'))
    if not rt: return
    rec['weaponType'] = rt
    rec['slot'] = 'Ranged' if rt in RANGED_WEAPONS else f'Relic ({rt})'
    if rt in RANGED_WEAPONS:
        so = it['scalingOptions'].get('0') or list(it['scalingOptions'].values())[0]
        if so.get('weaponDamageMin') is not None or it.get('weaponSpeed'):
            rec['weapon'] = {'min': so.get('weaponDamageMin'), 'max': so.get('weaponDamageMax'), 'speed': it.get('weaponSpeed'),
                             'dps': round(so['unroundedDps'], 2) if so.get('unroundedDps') else None}
            if it.get('spellSchool') is not None: rec['weapon']['spellSchool'] = SCHOOL.get(it['spellSchool'], it['spellSchool'])
        w = wh_weapon(rec['id'])
        if w and 'weapon' in rec:
            if w[2]: rec['weapon']['damageSchoolWowhead'] = w[2]
            if [rec['weapon']['min'], rec['weapon']['max']] != [w[0], w[1]]:
                cc = rec['crossCheckWowhead'] if isinstance(rec['crossCheckWowhead'], dict) else {}
                cc['weapon'] = {'wowsims': [rec['weapon']['min'], rec['weapon']['max']], 'wowhead': [w[0], w[1]]}
                rec['crossCheckWowhead'] = cc


def armor_check(rec):
    """Add base/bonus armor to the Wowhead cross-check (build_dataset.build() compares primary stats, healing, mp5, ap, hit, crit, weapon damage only)."""
    p = os.path.join(b.C, 'wh', f"{rec['id']}.json")
    if not os.path.exists(p): return
    d = json.load(open(p))
    if '__404__' in d: return
    m = re.search(r'<!--amr-->(\d+) Armor', d['tooltip'])
    base = int(m.group(1)) if m else 0
    bonus = sum(int(z) for l in b.wh_lines(rec['id']) or [] for z in re.findall(r'(?:^| )\+(\d+) Armor(?:$| )', l))
    diffs = {}
    if rec['stats'].get('armor', 0) != base: diffs['armor'] = {'wowsims': rec['stats'].get('armor', 0), 'wowhead': base}
    if rec['stats'].get('bonusArmor', 0) != bonus: diffs['bonusArmor'] = {'wowsims': rec['stats'].get('bonusArmor', 0), 'wowhead': bonus}
    if diffs:
        cc = rec['crossCheckWowhead'] if isinstance(rec['crossCheckWowhead'], dict) else {}
        cc.update(diffs); rec['crossCheckWowhead'] = cc


if __name__ == '__main__':
    res, excluded = b.build('allclass/target_ids.json')       # build() reads <cache>/<arg>
    for rec in res:
        if rec['itemType'] == 'Ranged/Relic': fix_ranged(rec)
        armor_check(rec)
    old = json.load(open(SHAMAN_FILE))['meta']
    meta = {'generated': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()), 'primarySource': old['primarySource'],
            'secondarySources': old['secondarySources'], 'statKeys': old['statKeys'], 'excludedCounts': dict(excluded), 'count': len(res)}
    json.dump({'meta': meta, 'items': res}, open(os.path.join(WORK, 'items_stage1.json'), 'w'), indent=1)
    print(len(res), dict(excluded))
