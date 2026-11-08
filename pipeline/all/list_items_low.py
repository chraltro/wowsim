# Warcraft DB Forever item lists for the low-level extension (reqLvl 0-39, and ilvl<45).
import json, subprocess, urllib.parse as u, sys, time
BASE = "https://forever.warcraftdb.com/api/data/list/items"
def get(url):
    for a in range(5):
        r = subprocess.run(["curl", "-sS", "-m", "60", url], capture_output=True)
        try: return json.loads(r.stdout)
        except Exception: time.sleep(2 * (a + 1))
    raise RuntimeError(url)
def crawl(filters, tag):
    fq = ''.join('&f=' + u.quote(f) for f in filters)
    rows = []; page = 1
    while True:
        d = get(f"{BASE}?page={page}&per_page=100{fq}&columns=name,item_level,required_level,source,item_subtype,slot,bind,usable_class&sort_by=name&sort_dir=asc")
        rows += d['rows']
        if page >= d['pages']: break
        page += 1; time.sleep(0.15)
    print(tag, d['total'], len(rows), file=sys.stderr)
    return rows
out = {}
out['q_req_low'] = crawl(['required_level:between:0,39', 'item_class:in:2,4'], 'req0-39')
out['q_ilvl_low'] = crawl(['item_level:lt:45', 'item_class:in:2,4'], 'ilvl<45')
json.dump(out, open('/home/claude/cache/list/lists_low.json', 'w'))
