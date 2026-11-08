# Map Maxroll planner histories (TraitNodeEntry ids) to talents and compare their end state with timesaver preset codes.
import json, sys
sys.path.insert(0, '/home/claude/wowsim/pipeline/talents')
import lib
CL = lib.load_classes()
for cls in lib.CLASSES:
    tabs = CL[cls]; B = lib.by_id(tabs)
    entry = {t['entry_id']: t['id'] for tab in tabs for t in tab['talents']}
    mx = json.load(open(f'/home/claude/dl/talents_all/maxroll/{cls}.json'))
    ts = json.load(open(f'/home/claude/dl/talents_all/ts/{cls}.json'))['presets']
    for p in mx['profiles']:
        miss = [e for e in p['history'] if e not in entry]
        seq = [entry[e] for e in p['history'] if e in entry]
        alloc, errs = lib.check_order(tabs, seq)
        code = lib.encode(tabs, alloc)
        match = [x['name'] for x in ts if x['code'] == code]
        # timesaver order equality
        ordm = [x['name'] for x in ts if x.get('order') and [B[i]['name'] for i in seq] == x['order']]
        print(f'{cls:8} {p["name"][:34]:34} pts {len(seq):2} split {lib.split(tabs, alloc):8} code {code:38} ts-code={match} ts-order={ordm} miss={miss} errs={errs[:3]}')
    for x in ts:
        a, e = lib.decode(tabs, x['code'])
        print(f'   TS {x["name"][:40]:40} {x["code"]:38} {x["source"]["name"]:8} split {lib.split(tabs,a)} pts {sum(a.values())} legal={lib.check_alloc(tabs,a) or "OK"} {e}')
