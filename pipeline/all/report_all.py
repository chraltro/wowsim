# Coverage report for items_forever_all.json (+ regression check against items_forever.json).
import json, collections, os
D = json.load(open('/home/claude/data/items_forever_all.json'))
O = json.load(open('/home/claude/data/items_forever.json'))
it = D['items']
def br(x):
    r = x.get('reqLvl')
    if r is None: return 'none'
    return '1-9' if r < 10 else '10-19' if r < 20 else '20-29' if r < 30 else '30-39' if r < 40 else '40-49' if r < 50 else '50-60'
B = ['1-9', '10-19', '20-29', '30-39', '40-49', '50-60', 'none']
print('TOTAL', len(it), 'meta.count', D['meta']['count'])
print('by origin', collections.Counter('wowtbc' if x.get('dataOrigin') == 'wowtbc' else 'warcraftdb+wowhead' if x.get('dataOrigin') else 'wowsims' for x in it))
print('by quality', sorted(collections.Counter(x['quality'] for x in it).items()))
print('\nPER SLOT x BRACKET')
slots = collections.Counter(x['slot'] for x in it)
print(f"{'slot':<18}" + ''.join(f'{b:>7}' for b in B) + f"{'total':>7}")
for s, n in slots.most_common():
    c = collections.Counter(br(x) for x in it if x['slot'] == s)
    print(f'{s:<18}' + ''.join(f'{c[b]:>7}' for b in B) + f'{n:>7}')
c = collections.Counter(br(x) for x in it)
print(f"{'ALL':<18}" + ''.join(f'{c[b]:>7}' for b in B) + f'{len(it):>7}')
print('\nNO-reqLvl items by ilvl band', sorted(collections.Counter(((x['ilvl'] or 0) // 10 * 10) for x in it if x.get('reqLvl') is None).items()))
print('\nSOURCE TYPES (items having >=1 source of type) x BRACKET')
types = ['drop', 'quest', 'crafted', 'vendor', 'reputation', 'pvp']
print(f"{'type':<12}" + ''.join(f'{b:>7}' for b in B) + f"{'total':>7}")
for t in types + ['(none)']:
    cc = collections.Counter(br(x) for x in it if (t in x['sourceTypes'] if t != '(none)' else not x['sources']))
    print(f'{t:<12}' + ''.join(f'{cc[b]:>7}' for b in B) + f'{sum(cc.values()):>7}')
print('source records by type', collections.Counter(s['type'] for x in it for s in x['sources']))
print('\nDROP SOURCES')
ds = [(x, s) for x in it for s in x['sources'] if s['type'] == 'drop']
print('drop source records', len(ds), 'with dropChancePct', sum(s.get('dropChancePct') is not None for _, s in ds))
print('  chance origin', collections.Counter('no chance' if s.get('dropChancePct') is None else (s.get('dropChanceSource') or '|'.join(s.get('provenance', []))).split(' (')[0] for _, s in ds))
print('  by instanceType', collections.Counter(s.get('instanceType') for _, s in ds))
dropitems = [x for x in it if 'drop' in x['sourceTypes']]
print('items with a drop source', len(dropitems), 'with >=1 drop chance', sum(any(s.get('dropChancePct') is not None for s in x['sources'] if s['type'] == 'drop') for x in dropitems))
cc = collections.Counter(); tt = collections.Counter()
for x in dropitems:
    tt[br(x)] += 1; cc[br(x)] += any(s.get('dropChancePct') is not None for s in x['sources'] if s['type'] == 'drop')
print('  drop-chance coverage per bracket', {b: f'{cc[b]}/{tt[b]}' for b in B})
w = [s for _, s in ds if any('wowtbc' in p for p in s.get('provenance', []))]
print('drop sources carrying wowtbc provenance', len(w), 'with chance', sum(s.get('dropChancePct') is not None for s in w))
print('\nWOWHEAD TOOLTIP COVERAGE')
print(collections.Counter('no tooltip' if x.get('crossCheckWowhead') == 'no wowhead tooltip' else 'match' if x.get('crossCheckWowhead') in ('match', 'is the wowhead parse') else 'diff' for x in it))
print('\nREGRESSION vs items_forever.json (reqLvl 40-60, or none with ilvl>=35)')
old = {x['id']: x for x in O['items']}
sub = {x['id']: x for x in it if (x.get('reqLvl') is not None and 40 <= x['reqLvl'] <= 60) or (x.get('reqLvl') is None and (x['ilvl'] or 0) >= 35)}
print('old', len(old), 'new subset', len(sub), 'old-only', len(set(old) - set(sub)), 'new-only', len(set(sub) - set(old)))
print('  old-only sample', [(i, old[i]['name'], old[i].get('reqLvl'), old[i].get('ilvl'), old[i].get('dataOrigin', '')[:10]) for i in list(set(old) - set(sub))[:10]])
print('  new-only sample', [(i, sub[i]['name'], sub[i].get('reqLvl'), sub[i].get('ilvl'), (sub[i].get('dataOrigin') or '')[:10], sub[i]['sourceTypes']) for i in list(set(sub) - set(old))[:15]])
same = sum(1 for i in set(old) & set(sub) if old[i]['stats'] == sub[i]['stats'])
print('  shared ids with identical stats', same, 'of', len(set(old) & set(sub)))

print('\nHORDE CHECK')
print('sources with side Horde', collections.Counter((s['type'], s.get('sideNote', '')[:40]) for x in it for s in x['sources'] if s.get('side') == 'Horde'))
print('items factionRestriction', collections.Counter(x.get('factionRestriction') for x in it))
print('accessNote sources', collections.Counter(s['zone'] for x in it for s in x['sources'] if s.get('accessNote')))
print('wowheadNote items', sum(1 for x in it if x.get('wowheadNote')), 'by bracket', collections.Counter(br(x) for x in it if x.get('wowheadNote')))
print('no-source items by quality', collections.Counter(x['quality'] for x in it if not x['sources']), 'randomSuffix', sum(bool(x.get('randomSuffix')) for x in it if not x['sources']))
