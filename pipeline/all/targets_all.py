# Target ids for the level 1-60 dataset (items_forever_all.json).
# Same usability rules as scripts/targets.py; scope: quality 2-5 with reqLvl 1-60 or no reqLvl (any ilvl),
# plus quality-1 (white) weapons and shields with the same level rule.
import json
R = '/home/claude/data/repos/wowsims-forever/assets/database/'
db = json.load(open(R + 'db.json')); lo = json.load(open(R + 'leftover_db.json'))
items = {}
for it in lo['items']: it['_db'] = 'leftover_db.json'; items[it['id']] = it
for it in db['items']: it['_db'] = 'db.json'; items[it['id']] = it   # main wins
WOK = {1, 2, 3, 4, 5, 7, 8}
def usable(it):
    t = it.get('type', 0)
    if it.get('classAllowlist') and 7 not in it['classAllowlist']: return False
    if it.get('factionRestriction') == 2: return False
    if t in (1, 3, 5, 6, 7, 8, 9, 10): return it.get('armorType', 0) in (0, 1, 2, 3)
    if t in (2, 4, 11, 12): return it.get('armorType', 0) in (0, 1, 2, 3)
    if t == 13: return it.get('weaponType', 0) in WOK
    if t == 14: return it.get('rangedWeaponType', 0) == 8
    return False
out = []; whites = 0
for it in items.values():
    q = it.get('quality', 0)
    white_weapon = q == 1 and it.get('type') == 13
    if not (2 <= q <= 5 or white_weapon) or not usable(it): continue
    r = it.get('reqLvl')
    if r is not None and not (1 <= r <= 60): continue
    out.append(it['id']); whites += white_weapon
json.dump(sorted(out), open('/home/claude/cache/target_ids_all.json', 'w'))
print(len(out), 'whites', whites)
