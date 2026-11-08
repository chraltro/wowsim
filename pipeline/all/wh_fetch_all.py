# Wowhead Forever tooltips for the 1-60 dataset: wowsims targets + Warcraft DB-only low-level candidates.
import json, subprocess, os, time, concurrent.futures as cf
R = '/home/claude/data/repos/wowsims-forever/assets/database/'
allw = set(it['id'] for f in ['db.json', 'leftover_db.json'] for it in json.load(open(R + f))['items'])
SUB_OK = {'Cloth', 'Leather', 'Mail', 'Miscellaneous', 'Shield', 'Dagger', 'Staff', 'One-Handed Mace', 'Two-Handed Mace', 'Two-Handed Axe', 'One-Handed Axe', 'Fist Weapon', 'Totem'}
ids = set(json.load(open('/home/claude/cache/target_ids_all.json')))
d = json.load(open('/home/claude/cache/list/lists_low.json'))
for r in d['q_req_low'] + d['q_ilvl_low']:
    if (r['quality'] or 0) >= 2 and r['item_id'] not in allw and r['item_subtype'] in SUB_OK and r['slot'] not in ('Shirt', 'Tabard', None) \
            and (r['required_level'] is None or r['required_level'] <= 60):
        ids.add(r['item_id'])
todo = sorted(i for i in ids if not os.path.exists(f'/home/claude/cache/wh/{i}.json'))
print('ids', len(ids), 'todo', len(todo), flush=True)
st = {'200': 0, '404': 0, 'fail': 0}
def work(i):
    p = f'/home/claude/cache/wh/{i}.json'
    for a in range(4):
        r = subprocess.run(["curl", "-sS", "-m", "30", "-A", "Mozilla/5.0", "-w", "\n%{http_code}", f"https://nether.wowhead.com/forever/tooltip/item/{i}"], capture_output=True, text=True)
        body, _, code = r.stdout.rpartition("\n")
        time.sleep(0.15)
        if code == '200':
            open(p, 'w').write(body); st['200'] += 1; return
        if code == '404':
            open(p, 'w').write('{"__404__":true}'); st['404'] += 1; return
        time.sleep(2 * (a + 1))
    st['fail'] += 1
t0 = time.time(); n = 0
with cf.ThreadPoolExecutor(4) as ex:
    for _ in ex.map(work, todo):
        n += 1
        if n % 500 == 0: print(n, round(time.time() - t0), st, flush=True)
print('done', n, round(time.time() - t0), st, flush=True)
