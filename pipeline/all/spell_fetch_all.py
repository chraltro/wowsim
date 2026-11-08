# Warcraft DB Forever spell nodes (recipe skill level) for crafted sources in the 1-60 scope.
import json, subprocess, os, time, glob, concurrent.futures as cf
R = '/home/claude/data/repos/wowsims-forever/assets/database/'
ids = set(json.load(open('/home/claude/cache/target_ids_all.json')))
items = {}
for f in ['leftover_db.json', 'db.json']:
    for it in json.load(open(R + f))['items']: items[it['id']] = it
sp = set()
for i in ids:
    for s in items[i].get('sources', []):
        if 'crafted' in s and s['crafted'].get('spellId'): sp.add(s['crafted']['spellId'])
for p in glob.glob('/home/claude/cache/items/*.json'):   # created-by tabs (used by supplement.py)
    for t in json.load(open(p))['tabs'].get('created-by', []):
        if t.get('ID'): sp.add(t['ID'])
todo = sorted(s for s in sp if not os.path.exists(f'/home/claude/cache/spell/{s}.json'))
print(len(sp), 'todo', len(todo), flush=True)
def work(s):
    p = f'/home/claude/cache/spell/{s}.json'
    for a in range(4):
        r = subprocess.run(["curl", "-sS", "-m", "30", "-w", "\n%{http_code}", f"https://forever.warcraftdb.com/api/data/node/spell/{s}"], capture_output=True, text=True)
        body, _, code = r.stdout.rpartition("\n"); time.sleep(0.1)
        if code == '200': open(p, 'w').write(body); return
        if code == '404': open(p, 'w').write('{"__404__":true}'); return
        time.sleep(2 * (a + 1))
with cf.ThreadPoolExecutor(4) as ex: list(ex.map(work, todo))
print('done')
