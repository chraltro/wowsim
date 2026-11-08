import json, subprocess, urllib.parse as u, sys, os, time
BASE="https://forever.warcraftdb.com/api/data/list/items"
def get(url):
    for a in range(4):
        r=subprocess.run(["curl","-sS","-m","60",url],capture_output=True)
        try: return json.loads(r.stdout)
        except Exception: time.sleep(2)
    raise RuntimeError(url)
def crawl(filters, tag):
    fq=''.join('&f='+u.quote(f) for f in filters)
    rows=[]; page=1
    while True:
        d=get(f"{BASE}?page={page}&per_page=100{fq}&columns=name,item_level,required_level,source,item_subtype,slot,bind,usable_class&sort_by=name&sort_dir=asc")
        rows+=d['rows']
        if page>=d['pages']: break
        page+=1
    print(tag, d['total'], len(rows), file=sys.stderr)
    return rows
out={}
out['q_req']=crawl(['required_level:between:40,60','item_class:in:2,4'],'req40-60')
out['q_ilvl']=crawl(['item_level:gte:45','item_class:in:2,4'],'ilvl>=45')
out['alliance_only']=[r['item_id'] for r in crawl(['side:in:1','item_class:in:2,4','item_level:gte:40'],'alliance')]
out['horde_only']=[r['item_id'] for r in crawl(['side:in:2','item_class:in:2,4','item_level:gte:40'],'horde')]
json.dump(out,open('/home/claude/cache/list/lists.json','w'))
