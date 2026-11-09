import re, html, json, sys, collections
def tokens(path):
    s=open(path,encoding='utf-8',errors='ignore').read()
    s=re.sub(r'<script.*?</script>','',s,flags=re.S); s=re.sub(r'<style.*?</style>','',s,flags=re.S)
    s=re.sub(r'<[^>]+>',' | ',s); s=html.unescape(s)
    return [x.strip() for x in s.split('|') if x.strip()]
def isint(x):
    return re.fullmatch(r'\d+',x) is not None
def parse(path):
    t=tokens(path)
    # find header 'Reagents','Source'
    starts=[i for i in range(len(t)-1) if t[i]=='Reagents' and t[i+1]=='Source']
    rows=[]
    for st in starts:
        i=st+2
        while i < len(t)-6:
            try:
                name=t[i]; j=i+1; new=False
                if t[j]=='New': new=True; j+=1
                if not isint(t[j]): break
                learn=int(t[j]); j+=1
                if t[j]=='*': j+=1
                o,y,g,gr=t[j:j+4]
                if not all(isint(v) for v in (o,y,g,gr)): break
                j+=4; reag=[]
                while j+2 < len(t) and t[j+1]=='×' and isint(t[j+2]):
                    reag.append((t[j],int(t[j+2]))); j+=3
                src=t[j]; j+=1
                rows.append({'name':name,'new':new,'learn':learn,'orange':int(o),'yellow':int(y),'green':int(g),'grey':int(gr),'reagents':reag,'source':src})
                i=j
            except Exception as e:
                break
    # dedupe identical rows (page may repeat table)
    seen=set(); out=[]
    for r in rows:
        k=(r['name'],tuple(r['reagents']),r['learn'])
        if k in seen: continue
        seen.add(k); out.append(r)
    return out
if __name__=='__main__':
    rows=parse(sys.argv[1])
    print(len(rows), collections.Counter(r['source'] for r in rows))
    for r in rows[:3]: print(r)
    for r in rows:
        if r['name'] in ('Red Linen Bag','Linen Bag','Spidersilk Boots'): print(r)
