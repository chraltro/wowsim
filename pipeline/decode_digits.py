import json,sys
d=json.load(open(sys.argv[1]))
trees=d['trees']
def dec(code):
    code=code.lstrip('h')
    parts=code.split('-')
    out=[]
    for ti,tr in enumerate(trees):
        s=parts[ti] if ti<len(parts) else ''
        tal=sorted(tr['talents'],key=lambda x:(x['tier'],x['column']))
        alloc=[]
        for i,x in enumerate(tal):
            r=int(s[i]) if i<len(s) else 0
            if r: alloc.append((x['name'],r,x['max_rank'],x['tier']+1))
        out.append((tr['name'],sum(a[1] for a in alloc),alloc))
    return out
def valid(out):
    # check row gating and prereqs
    errs=[]
    for (tn,tot,alloc),tr in zip(out,trees):
        byname={x['name']:x for x in tr['talents']}
        ranks={a[0]:a[1] for a in alloc}
        for n,r,mx,row in alloc:
            if r>mx: errs.append(f'{n} over max')
            below=sum(rr for nn,rr,_,rw in alloc if rw<row)
            if below<(row-1)*5: errs.append(f'{n} row{row} needs {(row-1)*5} has {below}')
            pre=byname[n]['prereq_talent']
            if pre:
                pn=[x['name'] for x in tr['talents'] if x['id']==pre][0]
                if ranks.get(pn,0)<byname[n]['prereq_rank']: errs.append(f'{n} prereq {pn} {byname[n]["prereq_rank"]}')
    return errs
for code in sys.argv[2:]:
    out=dec(code)
    print('CODE',code,'split',' / '.join(str(o[1]) for o in out),'total',sum(o[1] for o in out))
    for tn,tot,alloc in out:
        if tot: print('  ',tn,tot,': ',', '.join(f'{n} {r}/{mx}' for n,r,mx,row in alloc))
    print('   validity:', valid(out) or 'OK')
