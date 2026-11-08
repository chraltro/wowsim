import re, html, json, sys
out = {}
for f in sys.argv[1:]:
    t = open(f).read()
    title = re.search(r'<title>([^<]*)', t).group(1)
    name = title.split(' WoW Forever')[0]
    txt = html.unescape(re.sub(r'<[^>]+>', '\n', re.sub(r'<(script|style).*?</\1>', '', t, flags=re.S)))
    lines = [l.strip() for l in txt.split('\n') if l.strip()]
    lvl = None
    for i, l in enumerate(lines):
        if l == 'Level Range':
            lvl = lines[i+1]; break
    rows = []
    for tr in re.findall(r'<tr.*?</tr>', t, flags=re.S):
        m = re.search(r'wowhead\.com/forever/item=(\d+)', tr)
        if not m: continue
        cells = [html.unescape(re.sub(r'<[^>]+>', ' ', c)).split() for c in re.findall(r'<t[dh][^>]*>(.*?)</t[dh]>', tr, flags=re.S)]
        cells = [' '.join(c) for c in cells]
        rows.append({'id': int(m.group(1)), 'cells': cells})
    out[name] = {'file': f, 'level': lvl, 'rows': rows}
json.dump(out, open('/home/claude/cache/loot/method_parsed.json', 'w'), indent=1)
for k, v in out.items():
    print(k, v['level'], len(v['rows']))
    for r in v['rows']: print('   ', r['id'], r['cells'])
