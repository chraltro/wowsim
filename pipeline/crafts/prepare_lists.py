"""Write the lists of items to look up: mb_list.tsv (MetaBot vendor pages) and ahl_need.txt (AHledger sell prices
for items missing from ItemSparse). Run from fetch_inputs.sh after the AHledger and client tables are in raw/."""
import json, csv, glob, re, os, sys
csv.field_size_limit(10**9)
RAW = sys.argv[1]
MARKET = 'forever.rppvp.alliance.eu'
os.chdir(RAW)
sp = {int(r['ID']): r for r in csv.DictReader(open('ItemSparse.csv', encoding='utf-8', errors='ignore'))}
cls = {int(r['ID']): (int(r['ClassID']), int(r['SubclassID'])) for r in csv.DictReader(open('Item.csv', encoding='utf-8', errors='ignore'))}
recs = []
for f in sorted(glob.glob('crafting_*.json')):
    recs += json.load(open(f))['recipes']
results = set(x['result']['id'] for x in recs if x['result'])
reag = set(g['id'] for x in recs for g in x['reagents'])
names = {i: r['Display_lang'] for i, r in sp.items()}
for x in recs:
    names.setdefault(x['result']['id'], x['result']['name'])
    for g in x['reagents']:
        names.setdefault(g['id'], g['name'])
mine = [int(l.split(':')[0]) for l in open('pt/' + MARKET + '.txt').read().strip().split('\n')[1:]]
# Vendor candidates: bought reagents (not herbs, enchanting or elemental materials, not quest items), and items on the
# house's auction house of the kinds vendors sell (recipes, consumables, ammo, bags, trade goods, reagents, misc).
gathered = {(7, 9), (7, 12), (7, 10)}
cand = {i for i in reag if i not in results and cls.get(i, (0, 0)) not in gathered and cls.get(i, (0, 0))[0] != 12}
kinds = lambda c: c[0] in (9, 0, 6, 1, 15, 5) or (c[0] == 7 and c[1] in (11, 1, 2, 3, 5, 8))
cand |= {i for i in mine if i not in results and kinds(cls.get(i, (99, 99)))}
slug = lambda n: re.sub(r'[^a-z0-9]+', '-', n.lower().replace("'", '')).strip('-')
rows = [f"{i}\t{slug(names[i])}" for i in sorted(cand) if names.get(i)]
open('mb_list.tsv', 'w').write('\n'.join(rows) + '\n')
need = (results | reag | set(mine)) - set(sp)
open('ahl_need.txt', 'w').write('\n'.join(map(str, sorted(need))) + '\n')
print(len(rows), 'MetaBot pages,', len(need), 'AHledger items')
