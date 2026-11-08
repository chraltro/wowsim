import json, subprocess, os, sys, time, concurrent.futures as cf
SUB_OK={'Cloth','Leather','Mail','Miscellaneous','Shield','Dagger','Staff','One-Handed Mace','Two-Handed Mace','Two-Handed Axe','One-Handed Axe','Fist Weapon','Totem'}
SLOT_BAD={'Shirt','Tabard',None}
B="https://forever.warcraftdb.com"
def get(url):
    for a in range(5):
        r=subprocess.run(["curl","-sS","-m","60","-w","\n%{http_code}",url],capture_output=True,text=True)
        body,_,code=r.stdout.rpartition("\n")
        if code=="200":
            try: return json.loads(body)
            except Exception: pass
        elif code=="404": return None
        time.sleep(1.5*(a+1))
    return {"__error__":code}
def work(row):
    i=row['item_id']; p=f"/home/claude/cache/items/{i}.json"
    if os.path.exists(p): return i,'cached'
    tt=get(f"{B}/api/v1/tooltip/item/{i}")
    node=get(f"{B}/api/data/node/item/{i}")
    tabs={}
    if node and 'tabs' in node:
        for t in node['tabs']:
            if t['slug'] in ('screenshots','comments') or not t.get('count'): continue
            rows=[]; page=1
            while True:
                d=get(f"{B}/api/data/node/item/{i}/tab/{t['slug']}?page={page}")
                if not d or '__error__' in d: rows.append({'__error__':True}); break
                rows+=d.get('rows',[])
                if page>=d.get('pages',1) or page>=5: break
                page+=1
            tabs[t['slug']]=rows
    json.dump({'list':row,'tooltip':tt,'node':node,'tabs':tabs,'fetched':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime())},open(p,'w'))
    return i,'ok'
d=json.load(open('/home/claude/cache/list/lists.json'))
m={}
for r in d['q_req']+d['q_ilvl']: m[r['item_id']]=r
keep=[r for r in m.values() if ((r['required_level'] is not None and 40<=r['required_level']<=60) or (r['required_level'] is None and (r['item_level'] or 0)>=45)) and r['item_subtype'] in SUB_OK and r['slot'] not in SLOT_BAD]
print('targets',len(keep),flush=True)
n=0
with cf.ThreadPoolExecutor(6) as ex:
    for i,s in ex.map(work,keep):
        n+=1
        if n%200==0: print(n,flush=True)
print('done',n,flush=True)
