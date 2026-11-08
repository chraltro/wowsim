import json
P = '/home/claude/data/items_forever.json'
D = json.load(open(P))
ids = {i['id']: i for i in D['items']}
rows = json.load(open('/home/claude/cache/loot/tbc/rows.json'))
ZONE = {'krol-dok-stronghold': "Krol'dok Stronghold", 'alcaz-prison': 'Alcaz Prison'}
targets = {i['id'] for i in D['items'] if not i['sources'] and i['quality'] >= 3 and i['id'] >= 240000}
added = []
for r in rows:
    if r['id'] not in targets or r['slug'] not in ZONE:
        continue
    it = ids[r['id']]
    assert it['name'].lower() == (r['name'] or '').lower()
    assert r['source'] == r['boss'] and r['source_type'] == ZONE[r['slug']]
    url = f"https://wowtbc.gg/warcraftforever/loot-tables/dungeons/{r['slug']}/"
    src = {"type": "drop", "npc": r['boss'], "zone": ZONE[r['slug']], "instanceType": "dungeon",
           "dropChancePct": None, "dungeonLevel": f"{r['levels'][0]}-{r['levels'][1]}",
           "provenance": [f"wowtbc.gg loot table {url}"]}
    if any(s.get('type') == 'drop' and s.get('npc') == src['npc'] for s in it['sources']):
        continue
    it['sources'].append(src)
    if 'drop' not in it['sourceTypes']:
        it['sourceTypes'].append('drop')
    added.append((it['id'], it['name'], r['boss'], ZONE[r['slug']]))
D['meta']['lootSupplement'] = {
    "added": "2026-11-08",
    "count": len(added),
    "note": "Boss drop sources for new WoW Forever dungeon items, matched by item id and exact name to wowtbc.gg Forever loot tables (page-data JSON). Level range from the same page; matches Blizzard's 'Explore the New Dungeons' article (https://news.blizzard.com/en-us/article/24301455). No drop chances published.",
    "sources": ["https://wowtbc.gg/warcraftforever/loot-tables/dungeons/krol-dok-stronghold/",
                "https://wowtbc.gg/warcraftforever/loot-tables/dungeons/alcaz-prison/"]}
json.dump(D, open(P, 'w'), indent=1, ensure_ascii=False)
for a in added: print(a)
left = [i for i in D['items'] if not i['sources'] and i['quality'] >= 3 and i['id'] >= 240000]
print('added', len(added), 'remaining without source', len(left))
