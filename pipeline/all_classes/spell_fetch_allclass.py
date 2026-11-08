# Warcraft DB Forever spell nodes (recipe skill level) for crafted sources of the all-classes targets and for the
# created-by tabs of every cached Warcraft DB item. Same cache as ../all/spell_fetch_all.py (cache/spell/<id>.json).
import json, subprocess, os, time, glob, concurrent.futures as cf
from common import CACHE, WORK, load_wowsims_items

if __name__ == '__main__':
    ids = set(json.load(open(os.path.join(WORK, 'target_ids.json'))))
    items = load_wowsims_items()
    sp = set()
    for i in ids:
        for s in items[i].get('sources', []):
            if 'crafted' in s and s['crafted'].get('spellId'): sp.add(s['crafted']['spellId'])
    for p in glob.glob(os.path.join(CACHE, 'items', '*.json')):
        for t in json.load(open(p))['tabs'].get('created-by', []):
            if t.get('ID'): sp.add(t['ID'])
    todo = sorted(s for s in sp if not os.path.exists(os.path.join(CACHE, 'spell', f'{s}.json')))
    print(len(sp), 'todo', len(todo), flush=True)

    def work(s):
        p = os.path.join(CACHE, 'spell', f'{s}.json')
        for a in range(4):
            r = subprocess.run(["curl", "-sS", "-m", "30", "-w", "\n%{http_code}", f"https://forever.warcraftdb.com/api/data/node/spell/{s}"], capture_output=True, text=True)
            body, _, code = r.stdout.rpartition("\n"); time.sleep(0.1)
            if code == '200': open(p + '.part', 'w').write(body); os.replace(p + '.part', p); return 'ok'
            if code == '404': open(p, 'w').write('{"__404__":true}'); return '404'
            time.sleep(2 * (a + 1))
        return 'fail'
    with cf.ThreadPoolExecutor(4) as ex: res = list(ex.map(work, todo))
    print('done', {k: res.count(k) for k in set(res)})
