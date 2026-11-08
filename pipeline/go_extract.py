import re, json, sys
s = open(sys.argv[1], encoding='utf-8', errors='replace').read()
# collect all next_f push string chunks
chunks = re.findall(r'self\.__next_f\.push\(\[1,("(?:[^"\\]|\\.)*")\]\)', s)
full = ''.join(json.loads(c) for c in chunks)
open(sys.argv[2], 'w').write(full)
i = full.find('"grid":{')
start = i + len('"grid":')
# bracket match
depth = 0; j = start; instr = False; esc = False
while True:
    ch = full[j]
    if instr:
        if esc: esc = False
        elif ch == '\\': esc = True
        elif ch == '"': instr = False
    else:
        if ch == '"': instr = True
        elif ch == '{': depth += 1
        elif ch == '}':
            depth -= 1
            if depth == 0: break
    j += 1
grid = json.loads(full[start:j+1])
json.dump(grid, open(sys.argv[3], 'w'), indent=1)
print(grid.keys())
for t in grid['tabs']:
    print(t['name'], t['talent_count'])
