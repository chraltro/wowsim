import json, subprocess, os, time, concurrent.futures as cf
ids=json.load(open('/home/claude/cache/target_ids.json'))
def work(i):
    p=f'/home/claude/cache/wh/{i}.json'
    if os.path.exists(p): return
    for a in range(4):
        r=subprocess.run(["curl","-sS","-m","30","-A","Mozilla/5.0","-w","\n%{http_code}",f"https://nether.wowhead.com/forever/tooltip/item/{i}"],capture_output=True,text=True)
        body,_,code=r.stdout.rpartition("\n")
        if code=='200':
            open(p,'w').write(body); return
        if code=='404':
            open(p,'w').write('{"__404__":true}'); return
        time.sleep(2*(a+1))
with cf.ThreadPoolExecutor(4) as ex: list(ex.map(work,ids))
print('done')
