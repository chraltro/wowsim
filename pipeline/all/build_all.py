# Build /home/claude/data/items_forever_all.json (levels 1-60) with the same code path as scripts/build_dataset.py.
import json, os, time, importlib.util
spec = importlib.util.spec_from_file_location('b', '/home/claude/scripts/build_dataset.py'); b = importlib.util.module_from_spec(spec); spec.loader.exec_module(b)
b.QUAL[1] = 'Common'
# new Forever dungeon zone ids missing from build_dataset.DUNGEON_ZONES (City of Dalaran, Drowned City, Blackmaw Hold, Ruins of Lordaeron, Shaper's Terrace, Excavation Site: Wetlands, Krol'dok Stronghold)
b.DUNGEON_ZONES.update({16544, 16550, 16554, 16611, 16667, 16732, 16842})
OUT = '/home/claude/data/items_forever_all.json'
old = json.load(open('/home/claude/data/items_forever.json'))['meta']
res, excluded = b.build('target_ids_all.json')
meta = {
    'generated': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
    'scope': 'Items an Alliance Shaman can equip while leveling 1-60; quality>=2 with reqLvl 1-60, or no reqLvl at any ilvl; plus quality-1 (white) weapons and shields from the wowsims db under the same level rule. Cloth/leather/mail armor, back/neck/finger/trinket, shields, held-in-off-hand, 1H/2H axes and maces, daggers, fist weapons, staves, totems. Horde-only items and Horde-only sources removed.',
    'sameSchemaAs': '/home/claude/data/items_forever.json (reqLvl 40-60 build); that file is unchanged',
    'primarySource': old['primarySource'],
    'secondarySources': old['secondarySources'],
    'statKeys': old['statKeys'],
    'excludedCounts': dict(excluded), 'count': len(res)}
json.dump({'meta': meta, 'items': res}, open(OUT, 'w'), indent=1)
print(len(res), dict(excluded))
