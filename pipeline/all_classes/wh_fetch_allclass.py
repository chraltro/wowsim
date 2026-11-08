# Wowhead Forever tooltips for the all-classes build: wowsims targets + Warcraft DB-only candidates of every equippable
# subtype. Same cache as ../all/wh_fetch_all.py (cache/wh/<id>.json; 404 stored as {"__404__":true}); only missing ids are fetched.
import json, subprocess, os, time, concurrent.futures as cf
from common import CACHE, WORK, DBDIR
from crawl_wdb_allclass import SUB_ALL, SLOT_BAD

allw = set(it['id'] for f in ['db.json', 'leftover_db.json'] for it in json.load(open(os.path.join(DBDIR, f)))['items'])


def wanted():
    ids = set(json.load(open(os.path.join(WORK, 'target_ids.json'))))
    for f in ('lists.json', 'lists_low.json'):
        d = json.load(open(os.path.join(CACHE, 'list', f)))
        for k in ('q_req', 'q_ilvl', 'q_req_low', 'q_ilvl_low'):
            for r in d.get(k, []):
                if (r['quality'] or 0) >= 2 and r['item_id'] not in allw and r['item_subtype'] in SUB_ALL and r['slot'] not in SLOT_BAD \
                        and (r['required_level'] is None or r['required_level'] <= 60):
                    ids.add(r['item_id'])
    return ids


st = {'200': 0, '404': 0, 'fail': 0}


def work(i):
    p = os.path.join(CACHE, 'wh', f'{i}.json')
    for a in range(4):
        r = subprocess.run(["curl", "-sS", "-m", "30", "-A", "Mozilla/5.0", "-w", "\n%{http_code}", f"https://nether.wowhead.com/forever/tooltip/item/{i}"], capture_output=True, text=True)
        body, _, code = r.stdout.rpartition("\n")
        time.sleep(0.15)
        if code == '200':
            open(p + '.part', 'w').write(body); os.replace(p + '.part', p); st['200'] += 1; return
        if code == '404':
            open(p, 'w').write('{"__404__":true}'); st['404'] += 1; return
        time.sleep(2 * (a + 1))
    st['fail'] += 1


if __name__ == '__main__':
    ids = wanted()
    todo = sorted(i for i in ids if not os.path.exists(os.path.join(CACHE, 'wh', f'{i}.json')))
    print('ids', len(ids), 'todo', len(todo), flush=True)
    t0 = time.time(); n = 0
    with cf.ThreadPoolExecutor(4) as ex:
        for _ in ex.map(work, todo):
            n += 1
            if n % 500 == 0: print(n, round(time.time() - t0), st, flush=True)
    print('done', n, round(time.time() - t0), st, flush=True)
