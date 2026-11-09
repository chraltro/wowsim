#!/usr/bin/env python3
"""Build the Craft Profits page: src/crafts/ + data/crafts.json -> dist/crafts/index.html (one self-contained file)."""
import os
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
r = lambda f: open(os.path.join(ROOT, f), encoding='utf-8').read()
html = r('src/crafts/app.html')
data = r('data/crafts.json').replace('</', '<\\/')
for k, v in [('/*__DATA__*/', data), ('/*__CORE__*/', r('src/crafts/core.js')), ('/*__APP__*/', r('src/crafts/app.js').replace('</script>', '<\\/script>'))]:
    assert html.count(k) == 1, k
    html = html.replace(k, v)
out = os.path.join(ROOT, 'dist/crafts')
os.makedirs(out, exist_ok=True)
open(os.path.join(out, 'index.html'), 'w', encoding='utf-8').write(html)
print('crafts/index.html', len(html.encode()), 'bytes')
