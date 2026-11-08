import re, json, sys
s = open(sys.argv[1], encoding='utf-8', errors='replace').read()
chunks = re.findall(r'self\.__next_f\.push\(\[1,("(?:[^"\\]|\\.)*")\]\)', s)
full = ''.join(json.loads(c) for c in chunks)
open(sys.argv[2], 'w').write(full)
print(len(chunks), len(full))
