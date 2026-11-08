# Warcraft DB Forever item nodes + tabs for every item subtype any class can equip. Reuses the list caches written by
# ../list_items.py (cache/list/lists.json) and ../all/list_items_low.py (cache/list/lists_low.json); those lists already
# cover all weapon and armor subtypes. Same per-item cache format as ../all/crawl_items_low.py (cache/items/<id>.json),
# so items the Shaman build fetched are not fetched again. Resumable: an item is skipped once its file exists.
import json, subprocess, os, time, concurrent.futures as cf
from common import CACHE, WORK

SUB_ALL = {'Cloth', 'Leather', 'Mail', 'Plate', 'Miscellaneous', 'Shield', 'Dagger', 'Staff', 'One-Handed Mace', 'Two-Handed Mace', 'Two-Handed Axe',
           'One-Handed Axe', 'One-Handed Sword', 'Two-Handed Sword', 'Polearm', 'Fist Weapon', 'Bow', 'Gun', 'Crossbow', 'Thrown', 'Wand',
           'Totem', 'Idol', 'Libram'}
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
    i = row['item_id']; p = os.path.join(CACHE, 'items', f'{i}.json')
    if os.path.exists(p): return i, 'cached'
    node = get(f"{B}/api/data/node/item/{i}"); time.sleep(0.1)
    if node and '__error__' in node: return i, 'error'          # not cached, retried on the next run
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
    tmp = p + '.part'
    json.dump({'list': row, 'tooltip': None, 'node': node, 'tabs': tabs, 'fetched': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())}, open(tmp, 'w'))
    os.replace(tmp, p)
    return i, 'ok'


def keep_rows():
    targets = set(json.load(open(os.path.join(WORK, 'target_ids.json'))))
    m = {}
    for f in ('lists.json', 'lists_low.json'):
        d = json.load(open(os.path.join(CACHE, 'list', f)))
        for k in ('q_req', 'q_ilvl', 'q_req_low', 'q_ilvl_low'):
            for r in d.get(k, []): m[r['item_id']] = r
    return [r for r in m.values() if r['item_subtype'] in SUB_ALL and r['slot'] not in SLOT_BAD
            and (r['required_level'] is None or r['required_level'] <= 60)
            and ((r['quality'] or 0) >= 2 or (r['quality'] == 1 and r['item_id'] in targets))]


if __name__ == '__main__':
    keep = keep_rows()
    todo = [r for r in keep if not os.path.exists(os.path.join(CACHE, 'items', f"{r['item_id']}.json"))]
    print('keep', len(keep), 'todo', len(todo), flush=True)
    n = 0; t0 = time.time(); st = {}
    with cf.ThreadPoolExecutor(4) as ex:
        for i, s in ex.map(work, todo):
            n += 1; st[s] = st.get(s, 0) + 1
            if n % 250 == 0: print(n, round(time.time() - t0), st, flush=True)
    print('done', n, round(time.time() - t0), st, flush=True)
