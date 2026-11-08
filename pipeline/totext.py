import re, html, sys
for f in sys.argv[1:]:
    t = open(f).read()
    t = re.sub(r'<(script|style|noscript).*?</\1>', '', t, flags=re.S)
    s = html.unescape(re.sub(r'<[^>]+>', '\n', t))
    lines = [l.strip() for l in s.split('\n') if l.strip()]
    open(f[:-5] + '.txt', 'w').write('\n'.join(lines))
