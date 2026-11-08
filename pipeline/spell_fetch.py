import json, subprocess, os, time, concurrent.futures as cf
R='/home/claude/data/repos/wowsims-forever/assets/database/'
ids=set(json.load(open('/home/claude/cache/target_ids.json')))
items={}
for f in ['leftover_db.json','db.json']:
    for it in json.load(open(R+f))['items']: items[it['id']]=it
sp=set()
for i in ids:
    for s in items[i].get('sources',[]):
        if 'crafted' in s and s['crafted'].get('spellId'): sp.add(s['crafted']['spellId'])
print(len(sp))
def work(s):
    p=f'/home/claude/cache/spell/{s}.json'
    if os.path.exists(p): return
    for a in range(4):
        r=subprocess.run(["curl","-sS","-m","30","-w","\n%{http_code}",f"https://forever.warcraftdb.com/api/data/node/spell/{s}"],capture_output=True,text=True)
        body,_,code=r.stdout.rpartition("\n")
        if code=='200': open(p,'w').write(body); return
        if code=='404': open(p,'w').write('{"__404__":true}'); return
        time.sleep(2*(a+1))
with cf.ThreadPoolExecutor(4) as ex: list(ex.map(work,sorted(sp)))
print('done')
