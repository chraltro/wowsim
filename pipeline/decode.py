import json,sys
d=json.load(open(sys.argv[1]))
trees=d['trees']; L='ABC'
def decode(s):
    alloc={}; order=[]; tree=-1
    for ch in s:
        if ch in L: tree=L.index(ch); continue
        v=ord(ch)-48 if ord(ch)<=57 else ord(ch)-87
        tier,col=divmod(v,4)
        t=[x for x in trees[tree]['talents'] if x['tier']==tier and x['column']==col]
        if not t: order.append((tree,'??'+ch)); continue
        t=t[0]; k=(tree,t['name'])
        alloc[k]=alloc.get(k,0)+1; order.append(k)
    return alloc,order
for s in sys.argv[2:]:
    a,o=decode(s)
    print('BUILD',s,'total',sum(a.values()))
    for ti in range(3):
        pts=sum(v for (t,n),v in a.items() if t==ti)
        if pts: print(' ',trees[ti]['name'],pts)
        for (t,n),v in a.items():
            if t==ti:
                mx=[x['max_rank'] for x in trees[ti]['talents'] if x['name']==n][0]
                print('    ',n,f'{v}/{mx}')
    # order with level
    p2l=d['points_to_level']
    seq=[]; 
    for i,k in enumerate(o):
        seq.append(f"{p2l[i+1] if i+1<len(p2l) else '?'}:{k[1]}")
    print('  ORDER',' | '.join(seq))
