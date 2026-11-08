# Resolve each talent rank from the client and compare the numbers with timesaver.gg and wowforevertalents.com texts.
import json, re, sys, collections
sys.path.insert(0, '/home/claude/wowsim/pipeline/talents')
from talent_text import Client, resolve
cl = Client()
C = json.load(open('/home/claude/work/talents/client_trees.json'))['classes']
WFT = {c['slug']: c for c in json.load(open('/home/claude/dl/talents_all/wft/wft_classes.json'))}
num = lambda s: [float(x) for x in re.findall(r'\d+(?:\.\d+)?', s or '')]
stats = collections.Counter(); out = {}
for cls, v in C.items():
    ts = json.load(open(f'/home/claude/dl/talents_all/ts/{cls}.json'))['cls']['trees']
    wt = WFT[cls]['trees']
    for ti, tab in enumerate(v['tabs']):
        tsn = {x['name']: x for x in ts[ti]['talents']}
        wtn = {x['name']: x for x in wt[ti]['talents']}
        for t in tab['talents']:
            ranks = []
            for r in range(1, t['max'] + 1):
                txt, unres, _ = resolve(cl, t['spell_id'], r, t['definition_id'])
                tst = tsn[t['name']]['ranks'][r - 1] if t['name'] in tsn and len(tsn[t['name']]['ranks']) >= r else None
                wtt = wtn[t['name']]['ranks'][r - 1]['description'] if t['name'] in wtn and len(wtn[t['name']]['ranks']) >= r else None
                a, b, c = num(txt), num(tst), num(wtt)
                stats['ranks'] += 1
                if unres: stats['unresolved'] += 1
                agree_ts = a == b; agree_wt = a == c; ts_wt = b == c
                stats['client=ts'] += agree_ts; stats['client=wft'] += agree_wt; stats['ts=wft'] += ts_wt
                ranks.append({'rank': r, 'client': txt, 'unresolved': unres, 'timesaver': tst, 'wft': wtt,
                              'num_match_ts': agree_ts, 'num_match_wft': agree_wt, 'ts_eq_wft': ts_wt})
            out[(cls, tab['name'], t['name'])] = ranks
print(dict(stats))
json.dump({'|'.join(k): v for k, v in out.items()}, open('/home/claude/work/talents/text_compare.json', 'w'), indent=1)
# show disagreements where client is fully resolved
n = 0
for k, ranks in out.items():
    for r in ranks:
        if not r['unresolved'] and not (r['num_match_ts'] and r['num_match_wft']):
            n += 1
            if n <= 40:
                print('DIS', k, r['rank']); print('   C ', r['client'][:260]); print('   TS', (r['timesaver'] or '')[:260]); print('   WF', (r['wft'] or '')[:260])
print('disagreements (resolved)', n)
