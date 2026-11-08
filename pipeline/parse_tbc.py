import json, glob, os, sys
D = json.load(open('/home/claude/data/items_forever.json'))
ids = {i['id']: i for i in D['items']}
names = {}
for i in D['items']:
    names.setdefault(i['name'].lower(), []).append(i)
targets = {i['id'] for i in D['items'] if not i['sources'] and i['quality'] >= 3 and i['id'] >= 240000}
allempty = {i['id'] for i in D['items'] if not i['sources'] and i['quality'] >= 3}
rows = []
for f in sorted(glob.glob('/home/claude/cache/loot/tbc/pd_*.json')):
    slug = os.path.basename(f)[3:-5]
    pc = json.load(open(f))['result']['pageContext']
    gear = {g['id']: g for g in pc.get('gearData', [])}
    for L in pc['loot']:
        for b in L['bosses']:
            for iid in b['items']:
                g = gear.get(iid, {})
                rows.append(dict(slug=slug, dungeon=L['dungeon'], levels=L.get('levels'), new=L.get('new'), boss=b['name'], id=iid,
                                 name=g.get('name'), discovered=g.get('discovered'), source=g.get('source'), source_type=g.get('source_type'),
                                 ilvl=g.get('ilvl'), rarity=g.get('rarity'), g=g))
json.dump(rows, open('/home/claude/cache/loot/tbc/rows.json', 'w'), indent=1)
print('rows', len(rows))
hit = [r for r in rows if r['id'] in targets]
print('target hits by id', len(hit), 'unique', len({r['id'] for r in hit}))
for r in hit:
    print(r['slug'], '|', r['boss'], '|', r['id'], r['name'], '| disc', r['discovered'], '| src', r['source'], '/', r['source_type'], '| lv', r['levels'], '| dsname', ids[r['id']]['name'])
other = [r for r in rows if r['id'] in allempty and r['id'] not in targets]
print('non-target empty hits', len(other))
for r in other: print('  ', r['slug'], r['boss'], r['id'], r['name'], r['discovered'])
# name matches with different id
nm = [r for r in rows if r['name'] and r['name'].lower() in names and r['id'] not in ids]
print('name-only matches', len(nm))
for r in nm: print('  ', r['slug'], r['boss'], r['id'], r['name'], [x['id'] for x in names[r['name'].lower()]])
