import re, html, json, os, sys, glob
def money(s):
    if not s: return None
    g=re.search(r'(\d+)g',s); si=re.search(r'(\d+)s',s); c=re.search(r'(\d+)c',s)
    if not (g or si or c): return None
    return (int(g.group(1)) if g else 0)*10000+(int(si.group(1)) if si else 0)*100+(int(c.group(1)) if c else 0)
def toks(seg):
    seg=re.sub(r'<[^>]+>',' | ',seg); seg=html.unescape(seg)
    t=[x.strip() for x in seg.split('|')]
    return [x for x in t if x]
def parse(path):
    s=open(path,encoding='utf-8',errors='ignore').read()
    r={'ok':False}
    if len(s)<2000: return r
    m=re.search(r'<title>(.*?)</title>',s,re.S)
    r['title']=html.unescape(m.group(1)).split(' – ')[0].strip() if m else None
    m=re.search(r'<meta name="description" content="([^"]*)"',s)
    d=html.unescape(m.group(1)) if m else ''
    r['desc']=d; r['ok']=True
    mb=re.match(r'Buy (.+?) from (.+?) (?:in (.+?) )?for ([0-9gsc ]+)\.',d)
    r['desc_price']=money(mb.group(4)) if mb else None
    i=s.find('Sold by')
    vendors=[]; more=0
    if i>0:
        j=s.find('Where to find them on the map',i)
        seg=s[i:(j if j>0 else i+12000)]
        t=toks(seg)
        mm=re.search(r'\+(\d+) more vendors',' '.join(t)); more=int(mm.group(1)) if mm else 0
        # walk entries: each has '<' title '>' marker; vendor name precedes optional faction
        k=0
        while k < len(t):
            if t[k]=='<' and k+2<len(t) and t[k+2]=='>':
                # name and faction before
                fac=None; name=None
                if k-1>=0 and t[k-1] in ('Alliance','Horde'):
                    fac=t[k-1]; name=t[k-2] if k-2>=0 else None
                else:
                    name=t[k-1]
                # stock: find next token after 'Copy /way'
                stock=None
                for q in range(k+3, min(k+14,len(t))):
                    if t[q].startswith('Copy /way'):
                        # skip number token
                        stock=t[q+2] if q+2<len(t) else None
                        break
                vendors.append({'name':name,'faction':fac,'title':t[k+1],'stock':stock})
                k+=3
            else: k+=1
    r['vendors']=vendors; r['more']=more
    m=re.search(r'is sold by .*? for ([0-9gsc ]+)\.',s)
    r['faq_price']=money(m.group(1)) if m else None
    return r
if __name__=='__main__':
    for p in sys.argv[1:]:
        print(os.path.basename(p), json.dumps(parse(p))[:900]); print()
