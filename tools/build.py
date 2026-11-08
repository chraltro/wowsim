import json, os
ROOT=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
base=ROOT+'/src/'
r=lambda f: open(base+f).read()
html=r('app.html')
meta=json.load(open(ROOT+'/opt/talents_meta.json'))
tmeta='const TALENT_META = '+json.dumps([{k:t[k] for k in ('id','tree','name','max')} for t in meta], separators=(',',':'))+';'
data = r('data.js') + '\n' + r('levels.js') + '\n' + tmeta + '\nDATA.LV = LEVELS; DATA.RK = RANKS;\n'
items, engine, log, worker, main = r('items.js'), r('engine.js'), r('logparse.js'), r('worker.js'), r('app_main.js')
wsrc = data + '\n' + engine + '\n' + log + '\n' + worker
for k,v in [('/*DATA_JS*/',data),('/*ITEMS_JS*/',items),('/*ENGINE_JS*/',engine),('/*LOG_JS*/',log + '\n' + worker),('/*WORKER_JS*/',wsrc),('/*MAIN_JS*/',main)]:
    assert k in html, k
    html = html.replace(k, v.replace('</script>','<\\/script>'))
os.makedirs(ROOT+'/dist', exist_ok=True)
open(ROOT+'/dist/index.html','w').write(html)
print('bytes', len(html))
