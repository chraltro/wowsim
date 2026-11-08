import json,sys,time,subprocess,urllib.parse
tid=sys.argv[1]; base='https://us.forums.blizzard.com/en/wow/t/'
d=json.load(open(f'/home/claude/dl/bz/t{tid}.json'))
stream=d['post_stream']['stream']; have={p['id'] for p in d['post_stream']['posts']}
posts=list(d['post_stream']['posts'])
need=[i for i in stream if i not in have]
for k in range(0,len(need),20):
    batch=need[k:k+20]
    q='&'.join('post_ids[]=%d'%i for i in batch)
    url=f'{base}{tid}/posts.json?{q}'
    for attempt in range(4):
        out=subprocess.run(['curl','-sS','-A','Mozilla/5.0',url],capture_output=True,text=True).stdout
        try:
            j=json.loads(out)
            if 'post_stream' in j: posts+=j['post_stream']['posts']; break
        except Exception: pass
        time.sleep(15)
    time.sleep(6)
d['post_stream']['posts']=sorted(posts,key=lambda p:p['post_number'])
json.dump(d,open(f'/home/claude/dl/bz/t{tid}_all.json','w'))
print(tid,'total posts fetched',len(posts),'of',len(stream))
