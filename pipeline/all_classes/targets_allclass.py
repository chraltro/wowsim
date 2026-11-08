# Target ids for the all-classes 1-60 item file: wowsims Forever item db items that at least one class can equip on an
# Alliance character. Same scope rule as ../all/targets_all.py (quality 2-5 with reqLvl 1-60 or no reqLvl, any ilvl),
# with the white (quality 1) allowance widened from melee weapons and shields to ranged weapons and relics as well.
import json, os, collections
from common import WORK, CLASS_IDS, WT, RT, ARM, HAND, rules, usable_by, load_wowsims_items

R = rules()
items = load_wowsims_items()


def item_usable(it):
    allow = None
    if it.get('classAllowlist'):
        allow = [CLASS_IDS[c] for c in it['classAllowlist'] if c in CLASS_IDS]
        if not allow: return []
    t = it.get('type')
    if not t: return []
    return usable_by(R, item_type=t, armor=ARM.get(it.get('armorType', 0)), weapon_type=WT.get(it.get('weaponType')), hand=HAND.get(it.get('handType')),
                     ranged=RT.get(it.get('rangedWeaponType')), allow=allow, faction={1: 'Alliance', 2: 'Horde'}.get(it.get('factionRestriction')))


if __name__ == '__main__':
    out = {}; why = collections.Counter(); whites = collections.Counter()
    for it in items.values():
        q = it.get('quality', 0); t = it.get('type')
        white = q == 1 and t in (13, 14)
        if not (2 <= q <= 5 or white): why['quality out of scope'] += 1; continue
        r = it.get('reqLvl')
        if r is not None and not (1 <= r <= 60): why['reqLvl out of 1-60'] += 1; continue
        if it.get('factionRestriction') == 2: why['Horde-only item'] += 1; continue
        u = item_usable(it)
        if not u: why['no class can equip (type/subtype/allowlist)'] += 1; continue
        out[it['id']] = u; whites[t] += white
    json.dump(sorted(out), open(os.path.join(WORK, 'target_ids.json'), 'w'))
    json.dump({str(k): v for k, v in sorted(out.items())}, open(os.path.join(WORK, 'target_usable.json'), 'w'))
    per = collections.Counter(e['class'] for u in out.values() for e in u)
    print(len(out), 'whites', dict(whites), dict(why)); print(dict(per))
