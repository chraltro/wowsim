# Final cleanup of items_forever_all.json (things the old ilvl>=35 floor used to hide):
#  - Horde-only PvP insignias that the wowsims db does not mark with factionRestriction
#  - named developer/placeholder items (ilvl 1, no source)
#  - copy Wowhead's "Added in Season of Discovery. May not be in WoW: Forever." note onto the record
import json, re, importlib.util, collections
spec = importlib.util.spec_from_file_location('b', '/home/claude/scripts/build_dataset.py'); b = importlib.util.module_from_spec(spec); spec.loader.exec_module(b)
P = '/home/claude/data/items_forever_all.json'
D = json.load(open(P))
HORDE = re.compile(r"^(Greater )?Insignia of the Horde$")
DEV = re.compile(r"\(DND\)|^Hidden (Shoulder|Bracers)$|^Invisible Dagger$|^Durability Shoulderpads$|^Tyler's Balanced Bobble$")
keep = []; ex = collections.Counter(); removed = []
for x in D['items']:
    if HORDE.search(x['name']): ex['horde-only insignia (name)'] += 1; removed.append((x['id'], x['name'])); continue
    if DEV.search(x['name']) and (x['ilvl'] or 0) <= 1 and not x['sources']: ex['developer/placeholder item (name, ilvl 1, no source)'] += 1; removed.append((x['id'], x['name'])); continue
    for l in b.wh_lines(x['id']) or []:
        if 'May not be in WoW: Forever' in l: x['wowheadNote'] = l
    keep.append(x)
D['items'] = keep
D['meta']['excludedCounts'].update(dict(ex))
D['meta']['finalize'] = {'removed': removed, 'wowheadNoteCount': sum(1 for x in keep if x.get('wowheadNote')),
                         'wowheadNote': 'wowheadNote copies the Wowhead Forever tooltip line "Added in Season of Discovery. May not be in WoW: Forever." when present; those items may not exist in Forever.'}
D['meta']['count'] = len(keep)
json.dump(D, open(P, 'w'), indent=1, ensure_ascii=False)
print(len(keep), dict(ex), removed, D['meta']['finalize']['wowheadNoteCount'])
