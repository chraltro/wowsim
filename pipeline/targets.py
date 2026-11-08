import json
R='/home/claude/data/repos/wowsims-forever/assets/database/'
db=json.load(open(R+'db.json')); lo=json.load(open(R+'leftover_db.json'))
items={}
for it in lo['items']: it['_db']='leftover_db.json'; items[it['id']]=it
for it in db['items']: it['_db']='db.json'; items[it['id']]=it   # main wins
WOK={1,2,3,4,5,7,8}
def usable(it):
    t=it.get('type',0)
    if it.get('classAllowlist') and 7 not in it['classAllowlist']: return False
    if it.get('factionRestriction')==2: return False
    if t in (1,3,5,6,7,8,9,10): return it.get('armorType',0) in (0,1,2,3)
    if t in (2,4,11,12): return it.get('armorType',0) in (0,1,2,3)
    if t==13: return it.get('weaponType',0) in WOK
    if t==14: return it.get('rangedWeaponType',0)==8
    return False
out=[]
for it in items.values():
    if not (2 <= it.get('quality',0) <= 5) or not usable(it): continue
    so=it['scalingOptions'].get('0') or list(it['scalingOptions'].values())[0]
    ilvl=so.get('ilvl',0); r=it.get('reqLvl')
    if r is not None:
        if not (40<=r<=60): continue
    else:
        if ilvl<35: continue
    out.append(it['id'])
json.dump(sorted(out),open('/home/claude/cache/target_ids.json','w'))
print(len(out))
