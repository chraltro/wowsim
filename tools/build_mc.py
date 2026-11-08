#!/usr/bin/env python3
"""Build the group page: dist/forever/index.html plus dist/forever/engine.wasm.gz."""
import os, shutil
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
r = lambda f: open(os.path.join(ROOT, f)).read()
shaman = r('src/app.html')
css = shaman[shaman.index('<style>') + 7:shaman.index('</style>')]
html = r('src/mc/app.html')
data = r('src/data.js') + '\n' + r('src/levels.js') + '\nDATA.LV = LEVELS; DATA.RK = RANKS;\n'
cls = r('src/mc/classdata.js')
mc = cls + '\n' + r('src/mc/items.js') + '\n' + r('src/mc/request.js') + '\n' + r('src/mc/gear.js') + '\n' + r('src/mc/quest.js')
worker = data + '\n' + cls + '\n' + r('src/mc/request.js') + '\n' + r('src/mc/quest.js') + '\n' + r('src/mc/worker.js')
for k, v in [('/*SHARED_CSS*/', css), ('/*DATA_JS*/', data), ('/*MC_JS*/', mc), ('/*WORKER_JS*/', worker), ('/*APP_JS*/', r('src/mc/app.js'))]:
    assert k in html, k
    html = html.replace(k, v.replace('</script>', '<\\/script>'))
out = os.path.join(ROOT, 'dist/forever')
os.makedirs(out, exist_ok=True)
open(os.path.join(out, 'index.html'), 'w').write(html)
shutil.copyfile(os.path.join(ROOT, 'dist/engine.wasm.gz'), os.path.join(out, 'engine.wasm.gz'))
print('index.html', len(html), 'bytes; engine.wasm.gz', os.path.getsize(os.path.join(out, 'engine.wasm.gz')))
