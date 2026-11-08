# Warcraft DB Forever item nodes + tabs for the low-level extension. Same cache format as scripts/crawl_items.py
# (tooltip endpoint skipped: nothing downstream reads it).
import json, subprocess, os, time, concurrent.futures as cf
SUB_OK = {'Cloth', 'Leather', 'Mail', 'Miscellaneous', 'Shield', 'Dagger', 'Staff', 'One-Handed Mace', 'Two-Handed Mace', 'Two-Handed Axe', 'One-Handed Axe', 'Fist Weapon', 'Totem'}
SLOT_BAD = {'Shirt', 'Tabard', None}
B = "https://forever.warcraftdb.com"
def get(url):
    code = None
    for a in range(5):
        r = subprocess.run(["curl", "-sS", "-m", "60", "-w", "\n%{http_code}", url], capture_output=True, text=True)
        body, _, code = r.stdout.rpartition("\n")
        if code == "200":
            try: return json.loads(body)
            except Exception: pass
        elif code == "404": return None
        time.sleep(1.5 * (a + 1))
    return {"__error__": code}
def work(row):
    i = row['item_id']; p = f"/home/claude/cache/items/{i}.json"
    if os.path.exists(p): return i, 'cached'
    node = get(f"{B}/api/data/node/item/{i}"); time.sleep(0.1)
    tabs = {}
    if node and 'tabs' in node:
        for t in node['tabs']:
            if t['slug'] in ('screenshots', 'comments') or not t.get('count'): continue
            rows = []; page = 1
            while True:
                d = get(f"{B}/api/data/node/item/{i}/tab/{t['slug']}?page={page}"); time.sleep(0.1)
                if not d or '__error__' in d: rows.append({'__error__': True}); break
                rows += d.get('rows', [])
                if page >= d.get('pages', 1) or page >= 5: break
                page += 1
            tabs[t['slug']] = rows
    json.dump({'list': row, 'tooltip': None, 'node': node, 'tabs': tabs, 'fetched': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())}, open(p, 'w'))
    return i, 'ok'
d = json.load(open('/home/claude/cache/list/lists_low.json'))
targets = set(json.load(open('/home/claude/cache/target_ids_all.json')))
m = {}
for r in d['q_req_low'] + d['q_ilvl_low']: m[r['item_id']] = r
keep = [r for r in m.values() if r['item_subtype'] in SUB_OK and r['slot'] not in SLOT_BAD
        and (r['required_level'] is None or r['required_level'] <= 60)
        and ((r['quality'] or 0) >= 2 or (r['quality'] == 1 and r['item_id'] in targets))]
todo = [r for r in keep if not os.path.exists(f"/home/claude/cache/items/{r['item_id']}.json")]
print('keep', len(keep), 'todo', len(todo), flush=True)
n = 0; t0 = time.time()
with cf.ThreadPoolExecutor(4) as ex:
    for i, s in ex.map(work, todo):
        n += 1
        if n % 250 == 0: print(n, round(time.time() - t0), flush=True)
print('done', n, round(time.time() - t0), flush=True)
