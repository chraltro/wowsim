import re, json, sys

def strip_comments(s):
    # remove /* */ and // comments outside strings
    out=[];i=0;n=len(s);ins=False
    while i<n:
        c=s[i]
        if ins:
            out.append(c)
            if c=='\\': out.append(s[i+1]); i+=2; continue
            if c=='"': ins=False
            i+=1; continue
        if c=='"': ins=True; out.append(c); i+=1; continue
        if s.startswith('/*',i):
            j=s.index('*/',i); i=j+2; continue
        if s.startswith('//',i):
            j=s.find('\n',i); i = n if j<0 else j; continue
        out.append(c); i+=1
    return ''.join(out)

class P:
    def __init__(s,t): s.t=t; s.i=0
    def ws(s):
        while s.i<len(s.t) and s.t[s.i] in ' \t\n\r': s.i+=1
    def peek(s): s.ws(); return s.t[s.i] if s.i<len(s.t) else ''
    def value(s):
        s.ws(); c=s.t[s.i]
        if c=='"':
            j=s.i+1; buf=''
            while s.t[j]!='"':
                if s.t[j]=='\\': buf+=s.t[j:j+2]; j+=2; continue
                buf+=s.t[j]; j+=1
            s.i=j+1; return json.loads('"'+buf+'"')
        if c=='{':
            return s.composite()
        # type prefix or ident or number
        m=re.compile(r'(\[\d*\])?[A-Za-z_][\w.]*').match(s.t,s.i)
        if m and not re.match(r'-?\d',s.t[s.i:]):
            s.i=m.end(); s.ws()
            if s.i<len(s.t) and s.t[s.i]=='{':
                return s.composite()
            name=m.group(0)
            if name in ('true','false'): return name=='true'
            return name
        m=re.compile(r'-?(0x[0-9a-fA-F]+|\d+(\.\d+)?([eE][-+]?\d+)?)').match(s.t,s.i)
        s.i=m.end(); tok=m.group(0)
        if 'x' in tok: return int(tok,16)
        if re.search(r'[.eE]',tok): return float(tok)
        return int(tok)
    def orval(s):
        v=s.value(); s.ws()
        if s.i<len(s.t) and s.t[s.i]=='|':
            vs=[v]
            while s.peek()=='|':
                s.i+=1; vs.append(s.value())
            return ' | '.join(map(str,vs))
        return v
    def composite(s):
        assert s.t[s.i]=='{'; s.i+=1
        items=[]; keyed={}; iskeyed=None
        while True:
            if s.peek()=='}': s.i+=1; break
            v=s.orval(); s.ws()
            if s.t[s.i]==':':
                s.i+=1; v2=s.orval(); keyed[v]=v2; iskeyed=True
            else:
                items.append(v)
            s.ws()
            if s.t[s.i]==',': s.i+=1
        if keyed and not items: return keyed
        if keyed: keyed['_items']=items; return keyed
        return items

def load(path):
    txt=open(path).read()
    start=txt.index('var generatedSpells = []Spell{')
    body=txt[start+len('var generatedSpells = []Spell{'):]
    lines=body.split('\n')
    recs={}; cur=[]; comments={}
    def flush():
        if not cur: return
        raw='\n'.join(cur)
        cm=re.findall(r'// (override:.*)',raw)
        t=strip_comments(raw).strip().rstrip(',')
        p=P(t); v=p.value()
        if cm: v['_overrides']=cm
        recs[v['ID']]=v
    for ln in lines:
        if ln.startswith('\t{ID: '):
            flush(); cur=[ln]
        elif ln.startswith('}'):
            break
        else:
            if cur: cur.append(ln)
    flush()
    return recs

if __name__=='__main__':
    recs=load(sys.argv[1])
    json.dump(recs,open(sys.argv[2],'w'))
    print(len(recs))
