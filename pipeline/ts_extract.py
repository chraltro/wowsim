import json, sys
full = open(sys.argv[1]).read()
def extract(full, start):
    depth=0; j=start; instr=False; esc=False
    opener = full[start]
    closer = {'{':'}','[':']'}[opener]
    while True:
        ch=full[j]
        if instr:
            if esc: esc=False
            elif ch=='\\': esc=True
            elif ch=='"': instr=False
        else:
            if ch=='"': instr=True
            elif ch in '{[': depth+=1
            elif ch in '}]':
                depth-=1
                if depth==0: break
        j+=1
    return full[start:j+1]
idx = 0
n=0
while True:
    i = full.find('"trees":', idx)
    if i < 0: break
    st = i+len('"trees":')
    txt = extract(full, st)
    try:
        obj = json.loads(txt)
        json.dump(obj, open(sys.argv[2]+f'_{n}.json','w'), indent=1)
        print('trees', n, type(obj), len(obj), len(txt))
        n+=1
    except Exception as e:
        print('err', e)
    idx = st+1
# also print context before first trees
i = full.find('"trees":')
print(full[i-1500:i+300])
