# Decode all Method embeds, map node ids to client talents, check final == order end state and legality.
import json, sys
sys.path.insert(0, '/home/claude/wowsim/pipeline/talents')
import lib, method_decode as MD
CL = lib.load_classes()
E = json.load(open('/home/claude/dl/talents_all/method/embeds.json'))
out = []
for page in E:
    cls = page['class']; tabs = CL[cls]; B = lib.by_id(tabs)
    node = {t['node_id']: t['id'] for tab in tabs for t in tab['talents']}
    for i, e in enumerate(page['embeds']):
        try:
            d = MD.decode(cls, e['data_talent'])
        except Exception as ex:
            print('FAIL', cls, page.get('spec_page', page['kind']), e['heading'], ex, e['data_talent'][:60]); continue
        if not d['spec_ok']:
            print('NOT CLASS TREE', cls, page.get('spec_page', 'lev'), e['heading'], 'spec', d['spec']); continue
        final = {node[n]: r for n, r in d['final'].items() if n in node}
        unk = [n for n in d['final'] if n not in node]
        seq = [node[n] for n in d['order'] if n in node]
        unk_o = [n for n in d['order'] if n not in node]
        alloc, errs = lib.check_order(tabs, seq) if seq else ({}, [])
        code = lib.encode(tabs, final)
        same = (alloc == final) if seq else None
        print(f'{cls:8} {page.get("spec_page", "leveling")[:22]:22} {str(e["tab"] or e["heading"])[:40]:40} pts {sum(final.values()):2} order {len(seq):2} split {lib.split(tabs, final):8} {code:38} order==final {same} unk {unk+unk_o} legal {lib.check_alloc(tabs, final) or "OK"} orderErr {errs[:2]}')
        out.append({'page': page['url'], 'class': cls, 'idx': i, 'code': code, 'final': final, 'order': seq, 'order_errors': errs, 'unknown_nodes': unk + unk_o})
json.dump(out, open('/home/claude/work/talents/method_decoded.json', 'w'), indent=1)
