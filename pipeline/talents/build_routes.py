# Build /home/claude/wowsim/data/routes/<class>.json: leveling routes (point by point where the guide gives the order)
# and level 60 builds per dungeon role, each with its source. Inputs are the pages fetched by fetch_maxroll.py,
# fetch_method.py, fetch_wt.py and fetch_timesaver.py, decoded with lib.py / method_decode.py.
import json, re, sys, os, collections
sys.path.insert(0, '/home/claude/wowsim/pipeline/talents')
import lib

TODAY = '2026-11-08'
D = '/home/claude/dl/talents_all'
OUT = '/home/claude/wowsim/data/routes'
os.makedirs(OUT, exist_ok=True)
CL = lib.load_classes()

SPECS = {  # tree key -> (spec name, dungeon roles)
    'druid': {'balance': ('Balance', ['damage']), 'feral_combat': ('Feral', ['damage', 'tank']), 'restoration': ('Restoration', ['healer'])},
    'hunter': {'beast_mastery': ('Beast Mastery', ['damage']), 'marksmanship': ('Marksmanship', ['damage']), 'survival': ('Survival', ['damage'])},
    'mage': {'arcane': ('Arcane', ['damage']), 'fire': ('Fire', ['damage']), 'frost': ('Frost', ['damage'])},
    'paladin': {'holy': ('Holy', ['healer']), 'protection': ('Protection', ['tank']), 'retribution': ('Retribution', ['damage'])},
    'priest': {'discipline': ('Discipline', ['healer']), 'holy': ('Holy', ['healer']), 'shadow': ('Shadow', ['damage'])},
    'rogue': {'assassination': ('Assassination', ['damage']), 'combat': ('Combat', ['damage']), 'subtlety': ('Subtlety', ['damage'])},
    'shaman': {'ele': ('Elemental', ['damage']), 'enh': ('Enhancement', ['damage']), 'res': ('Restoration', ['healer'])},
    'warlock': {'affliction': ('Affliction', ['damage']), 'demonology': ('Demonology', ['damage']), 'destruction': ('Destruction', ['damage'])},
    'warrior': {'arms': ('Arms', ['damage']), 'fury': ('Fury', ['damage']), 'protection': ('Protection', ['tank'])},
}
ALIAS = {'feral_combat': ['feral', 'bear', 'cat'], 'beast_mastery': ['beast mastery', ' bm '], 'marksmanship': ['marksmanship', 'marks'],
         'restoration': ['restoration', 'resto'], 'res': ['restoration', 'resto'], 'ele': ['elemental'], 'enh': ['enhancement', 'enh '],
         'discipline': ['discipline', 'disc'], 'demonology': ['demonology', 'demonolgy', 'demo '], 'destruction': ['destruction', 'destro'],
         'affliction': ['affliction'], 'protection': ['protection', 'prot'], 'retribution': ['retribution', 'ret '], 'holy': ['holy'],
         'shadow': ['shadow'], 'assassination': ['assassination'], 'combat': ['combat'], 'subtlety': ['subtlety'], 'arms': ['arms'],
         'fury': ['fury'], 'arcane': ['arcane'], 'fire': ['fire'], 'frost': ['frost'], 'balance': ['balance'], 'survival': ['survival']}

def spec_of(cls, label, alloc):
    tabs = CL[cls]; T = lib.tree_of(tabs)
    lab = ' ' + (label or '').lower() + ' '
    hits = [k for k in SPECS[cls] if any(a in lab for a in ALIAS.get(k, [k]))]
    if len(hits) == 1:
        return hits[0], 'guide label'
    pts = collections.Counter()
    for k, v in alloc.items(): pts[tabs[T[k]]['key']] += v
    if hits:
        best = max(hits, key=lambda k: pts[k])
        return best, 'guide label names several specs; the one with most points'
    return (pts.most_common(1)[0][0] if pts else None), 'tree with most points (guide label names no spec)'

def runs(seq):
    out = []
    for i in seq:
        if out and out[-1][0] == i: out[-1][1] += 1
        else: out.append([i, 1])
    return out

def route_entry(cls, seq, final, label, source, kind, notes=None):
    tabs = CL[cls]; B = lib.by_id(tabs)
    e = {'name': label, 'source': source, 'kind': kind}
    if seq:
        alloc, errs = lib.check_order(tabs, seq)
        cnt = collections.Counter()
        order = []
        for i, tid in enumerate(seq):
            cnt[tid] += 1
            order.append({'level': 10 + i, 'id': tid, 'name': B[tid]['name'], 'rank': cnt[tid]})
        e['order'] = order
        e['route_runs'] = runs(seq)
        e['order_check'] = {'ok': not errs, 'errors': errs,
                            'rule': 'client tree 1.60.1.70862: row N needs 5 x (N-1) points in rows above, prerequisite at max rank, one point per level from 10'}
        final = final if final is not None else alloc
    e['final'] = {'code': lib.encode(tabs, final), 'split': lib.split(tabs, final), 'points': sum(final.values()),
                  'talents': {k: v for k, v in sorted(final.items(), key=lambda kv: list(B).index(kv[0]))},
                  'legal_on_client_tree': lib.check_alloc(tabs, final) or 'OK'}
    if seq is not None and final is not None:
        e['final']['order_end_state_equals_final'] = (lib.check_order(tabs, seq)[0] == final)
    pts = sum(final.values())
    if pts < 51:
        notes = (notes or []) + [f'the guide\'s build has {pts} points, so it covers levels 10 to {9 + pts}']
    if notes: e['notes'] = notes
    return e

def single_tab_label(spec_page, data_talent):
    h = open(f'{D}/method/spec_{spec_page}_talents.html').read()
    i = h.find(data_talent[:40])
    if i < 0: return None
    lab = re.findall(r'<(?:li|a|span|button)[^>]*>\s*([^<>]{3,60}?)\s*</(?:li|a|span|button)>', h[max(0, i - 1500):i])
    return lab[-1].strip() if lab else None

def excerpt(s, n=400):
    s = re.sub(r'<[^>]*>?', ' ', s or '')
    s = re.sub(r'\s+', ' ', s).strip()
    return s if len(s) <= n else '...' + s[-n:]

routes = {c: {'leveling': [], 'endgame': [], 'excluded': []} for c in lib.CLASSES}

# ---------------- Maxroll leveling (planner history = point order) ----------------
for cls in lib.CLASSES:
    tabs = CL[cls]
    entry = {t['entry_id']: t['id'] for tab in tabs for t in tab['talents']}
    mx = json.load(open(f'{D}/maxroll/{cls}.json'))
    m = mx['meta']
    for p in mx['profiles']:
        seq = [entry[x] for x in p['history'] if x in entry]
        miss = [x for x in p['history'] if x not in entry]
        src = {'site': 'Maxroll', 'url': m['url'], 'title': m['title'], 'author': m['author']['name'], 'published': m['date'], 'updated': m['modified'],
               'date_seen': TODAY, 'data': f'planner profile "{p["name"]}" (uid {p["uid"]}, planner {p["planner_id"]} saved {p["planner_date"]}): talents.history, TraitNodeEntry ids from window.__remixContext',
               'guide_order': 'point by point (the planner history is the guide\'s own order)'}
        notes = []
        if miss: notes.append(f'{len(miss)} history entries are not nodes of the live client tree: {miss}')
        e = route_entry(cls, seq, None, p['name'], src, 'point_by_point', notes)
        routes[cls]['leveling'].append(e)

# ---------------- Method leveling + spec pages ----------------
E = json.load(open(f'{D}/method/embeds.json'))
MXD = {(m['page'], m['idx']): m for m in json.load(open('/home/claude/work/talents/method_decoded.json'))}
for page in E:
    cls = page['class']
    for i, emb in enumerate(page['embeds']):
        md = MXD.get((page['url'], i))
        label = emb['tab'] or emb['heading']
        if not emb['tab'] and page['kind'] == 'spec_talents':
            label = single_tab_label(page['spec_page'], emb['data_talent']) or label
        if not md:
            routes[cls]['excluded'].append({'source': page['url'], 'label': 'embed #%d near "%s"' % (i, emb['heading']), 'reason': 'embed is not a class tree build (Legacy talents or a short discussion example); it does not decode against the class tree'})
            continue
        src = {'site': 'Method.gg', 'url': page['url'], 'title': page['meta']['title'], 'author': page['meta']['author'], 'updated': page['meta']['updated'],
               'patch': page['meta'].get('patch'), 'date_seen': TODAY,
               'data': f'data-talent embed #{i} ("{label}"), decoded with the reader in pipeline/talents/method_decode.py',
               'guide_order': 'point by point (the embed carries the order after ";")' if md['order'] else 'final build only'}
        notes = []
        if md['unknown_nodes']: notes.append(f'nodes not in the client tree: {md["unknown_nodes"]}')
        if page['kind'] == 'leveling':
            note = excerpt(emb.get('context_after'), 300)
            if note: notes.append('guide text after the build: ' + note)
            e = route_entry(cls, md['order'], md['final'], label, src, 'point_by_point' if md['order'] else 'final_only', notes)
            routes[cls]['leveling'].append(e)
        else:
            notes.append('guide text: ' + excerpt((emb.get('context_after') or '') or emb.get('context_before'), 400))
            if any('based on the beta build' in (x.get('context_before') or '') for x in page['embeds']):
                notes.append('the page says: "These talents are based on the beta build of the game; everything is subject to change."')
            e = route_entry(cls, None, md['final'], label, src, 'level_60_build', notes)
            e['method_spec_page'] = page['spec_page']
            if md['order']:
                alloc, errs = lib.check_order(CL[cls], md['order'])
                e['embedded_order_check'] = {'ok': not errs, 'errors': errs[:5], 'note': 'the embed also carries a point order; recorded here only as a legality check'}
            routes[cls]['endgame'].append(e)

# ---------------- Warcraft Tavern (Warcraft DB ordered builds) ----------------
WT = json.load(open(f'{D}/wt/links.json'))
WTD = json.load(open(f'{D}/wt/page_dates.json'))
for page in WT:
    for l in page['links']:
        cls = l['class']; tabs = CL[cls]
        seq, bad = lib.decode_wdb_ordered(tabs, l['t'])
        hp = l['headings_path']
        label = l['link_text'] or (hp[-2] if len(hp) >= 2 and hp[-1] == 'Talents' else l['heading'])
        meta = WTD.get(page['slug'], {})
        src = {'site': 'Warcraft Tavern', 'url': page['url'], 'title': page['meta']['title'], 'author': (meta.get('author_slugs') or [None])[0],
               'updated': meta.get('last_updated'), 'date_seen': TODAY, 'calculator_link': l['url'],
               'data': 'Warcraft DB calculator link #?t= (one character per point, in order)', 'guide_order': 'point by point (the link string is ordered)'}
        own_heading = hp[-2] if len(hp) >= 2 and hp[-1] == 'Talents' else (hp[-1] if hp else '')
        heading_txt = own_heading + ' / ' + (l['link_text'] or '')
        stale = any(k in heading_txt for k in ('Level 30', 'Mid-Level', 'Mid-level', 'Beta'))
        notes = []
        if bad: notes.append(f'characters that are not a node of the live client tree were skipped: {bad}')
        ctx = excerpt(l['context_before'], 300)
        if ctx: notes.append('guide text before the link: ' + ctx)
        if stale:
            alloc, errs = lib.check_order(tabs, seq)
            routes[cls]['excluded'].append({'source': page['url'], 'label': label, 'headings': hp, 'calculator_link': l['url'],
                                            'code': lib.encode(tabs, alloc), 'points': len(seq),
                                            'reason': 'beta-era build for the level 30 cap (guide says it will be updated for 60)' + (f'; skipped chars {bad}' if bad else '')})
            continue
        if page['slug'].endswith('-leveling'):
            routes[cls]['leveling'].append(route_entry(cls, seq, None, label, src, 'point_by_point', notes))
        else:
            e = route_entry(cls, seq, None, label, src, 'level_60_build', notes)
            routes[cls]['endgame'].append(e)

# ---------------- timesaver.gg presets (secondary; codes it transcribed from Wowhead / Icy Veins / Maxroll / Method) ----------------
for cls in lib.CLASSES:
    tabs = CL[cls]; B = lib.by_id(tabs)
    byname = {}
    for tab in tabs:
        for t in tab['talents']: byname[t['name']] = t['id']
    ts = json.load(open(f'{D}/ts/{cls}.json'))
    for x in ts['presets']:
        dec, err = lib.decode(tabs, x['code'])
        src = {'site': 'timesaver.gg (transcription)', 'url': ts['url'], 'date_seen': TODAY, 'cites': x['source'],
               'data': f'preset "{x["name"]}" in the calculator page payload; mode {x["mode"]}',
               'guide_order': 'point by point as transcribed by timesaver.gg' if x.get('order') else 'final build only'}
        seq = [byname[n] for n in x['order']] if x.get('order') else None
        e = route_entry(cls, seq, dec, x['name'], src, 'point_by_point' if seq else 'final_only')
        e['secondary'] = True
        if x['source']['name'] in ('Wowhead', 'Icy Veins'):
            e['notes'] = (e.get('notes') or []) + [f'original {x["source"]["name"]} page not reachable from this sandbox (Cloudflare); this is timesaver.gg\'s transcription, unverified against the original']
        routes[cls]['leveling'].append(e)

# ---------------- wowtbc.gg "Warcraft Forever" class guides (Gatsby page-data: level 60 builds + "Leveling 1-60" order) ----------------
WOWTBC = {'affliction-warlock': ('warlock', 'affliction'), 'arcane-mage': ('mage', 'arcane'), 'arms-warrior': ('warrior', 'arms'),
          'assassination-rogue': ('rogue', 'assassination'), 'balance-druid': ('druid', 'balance'), 'beast-mastery-hunter': ('hunter', 'beast_mastery'),
          'combat-rogue': ('rogue', 'combat'), 'demonology-warlock': ('warlock', 'demonology'), 'destruction-warlock': ('warlock', 'destruction'),
          'discipline-priest': ('priest', 'discipline'), 'elemental-shaman': ('shaman', 'ele'), 'enhancement-shaman': ('shaman', 'enh'),
          'feral-dps-druid': ('druid', 'feral_combat'), 'feral-tank-druid': ('druid', 'feral_combat'), 'fire-mage': ('mage', 'fire'),
          'frost-mage': ('mage', 'frost'), 'fury-warrior': ('warrior', 'fury'), 'holy-paladin': ('paladin', 'holy'), 'holy-priest': ('priest', 'holy'),
          'marksmanship-hunter': ('hunter', 'marksmanship'), 'protection-paladin': ('paladin', 'protection'), 'protection-warrior': ('warrior', 'protection'),
          'restoration-druid': ('druid', 'restoration'), 'restoration-shaman': ('shaman', 'res'), 'retribution-paladin': ('paladin', 'retribution'),
          'shadow-priest': ('priest', 'shadow'), 'subtlety-rogue': ('rogue', 'subtlety'), 'survival-hunter': ('hunter', 'survival')}
for slug, (cls, spk) in WOWTBC.items():
    tabs = CL[cls]; B = lib.by_id(tabs)
    byname = {t['name']: t['id'] for tab in tabs for t in tab['talents']}
    pos = {t['id']: (t['row'] + 1, t['col'] + 1) for tab in tabs for t in tab['talents']}
    pc = json.load(open(f'{D}/wowtbc/pd_{slug}.json'))['result']['pageContext']
    url = f'https://wowtbc.gg/warcraftforever/class-guides/{slug}/'
    keys = ['bisTalentOne', 'bisTalentTwo', 'bisTalentThree', 'bisTalentFour', 'bisTalentFive']
    paths = pc.get('talentBuildPaths') or []
    ti = 0
    for bi, bname in enumerate(pc['talentBuildNames']):
        src = {'site': 'wowtbc.gg (Warcraft Forever class guide)', 'url': url, 'author': None, 'updated': None, 'date_seen': TODAY,
               'data': f'https://wowtbc.gg/page-data/warcraftforever/class-guides/{slug}/page-data.json, build "{bname}"',
               'note': 'the page shows no author or date'}
        notes = []
        if bi < len(paths) and paths[bi]:
            seq = []; unk = []
            for st in paths[bi]:
                if st['name'] in byname: seq.append(byname[st['name']])
                else: unk.append(st['name'])
            if unk: notes.append(f'names not in the client tree: {sorted(set(unk))}')
            src['guide_order'] = 'point by point ("Leveling 1-60" talentBuildPaths)'
            e = route_entry(cls, seq, None, f'{bname}', src, 'point_by_point', notes)
            e['wowtbc_spec_page'] = slug; e['spec_forced'] = spk
            routes[cls]['leveling'].append(e)
            continue
        k = keys[ti]; ti += 1
        final = {}; unk = []; posbad = []
        for t in pc.get(k) or []:
            if not t['active_ranks']: continue
            tid = byname.get(t['name'])
            if not tid: unk.append(t['name']); continue
            final[tid] = t['active_ranks']
            if (int(t['row'][1:]), int(t['column'][1:])) != pos[tid]: posbad.append(f'{t["name"]} at {t["row"]}{t["column"]} vs client r{pos[tid][0]}c{pos[tid][1]}')
        if unk: notes.append(f'names not in the client tree: {unk}')
        if posbad: notes.append('position differs from the client tree: ' + '; '.join(posbad))
        src['guide_order'] = 'final build only'
        e = route_entry(cls, None, final, bname, src, 'level_60_build', notes)
        e['wowtbc_spec_page'] = slug; e['spec_forced'] = spk
        if slug == 'feral-dps-druid': e['role_override'] = ['damage']
        if slug == 'feral-tank-druid': e['role_override'] = ['tank']
        if 'Smite' in bname: e['role_override'] = ['damage']; e['notes'] = (e.get('notes') or []) + ['Smite damage build in the Discipline tree (guide name "Smite DPS")']
        routes[cls]['endgame'].append(e)

# wowsims-forever sim presets are not guide builds; they are used only as decode checks (decode_checks.py), not listed here.

# ---------------- assemble per spec, cross-reference identical codes ----------------
def use_of(text):
    t = (text or '').lower()
    u = []
    if 'dungeon' in t: u.append('dungeon')
    if 'raid' in t: u.append('raid')
    return u

summary = {}
for cls in lib.CLASSES:
    tabs = CL[cls]
    allb = routes[cls]['leveling'] + routes[cls]['endgame']
    bycode = collections.defaultdict(list)
    for e in allb: bycode[e['final']['code']].append(e)
    specs = {k: {'name': v[0], 'tree': k, 'dungeon_roles': v[1], 'leveling': [], 'endgame': {r: [] for r in v[1]}} for k, v in SPECS[cls].items()}
    for e in routes[cls]['leveling']:
        lab = e['name'] + ' ' + (e['source'].get('cites', {}) or {}).get('url', '') if e.get('secondary') else e['name']
        if e['source']['site'] == 'Method.gg':
            lab = e['name'] + ' ' + e['source']['url']
        sp, how = (e['spec_forced'], 'guide page is for this spec') if e.get('spec_forced') else spec_of(cls, lab, e['final']['talents'])
        e.pop('spec_forced', None)
        e['spec_assigned_by'] = how
        same = [f'{o["source"]["site"]}: {o["name"]}' for o in bycode[e['final']['code']] if o is not e]
        if same: e['same_final_code_as'] = same
        main = spec_of(cls, '', e['final']['talents'])[0]
        if main != sp:
            e['notes'] = (e.get('notes') or []) + [f'listed under {SPECS[cls][sp][0]} because the guide puts it there, but most points go into {SPECS[cls][main][0]}']
        specs[sp]['leveling'].append(e)
    for e in routes[cls]['endgame']:
        lab = e['name'] + ' ' + e['source']['url'] + ' ' + e.get('method_spec_page', '')
        sp, how = (e['spec_forced'], 'guide page is for this spec') if e.get('spec_forced') else spec_of(cls, lab, e['final']['talents'])
        e.pop('spec_forced', None)
        if e.get('method_spec_page'): how = 'guide page is for this spec'; sp = {'feral-dps-druid': 'feral_combat', 'feral-tank-druid': 'feral_combat'}.get(e['method_spec_page'], sp)
        e['spec_assigned_by'] = how
        same = [f'{o["source"]["site"]}: {o["name"]}' for o in bycode[e['final']['code']] if o is not e]
        if same: e['same_final_code_as'] = same
        e['use_in_build_name'] = use_of(e['name']) or None
        e['use_words_in_guide_text'] = use_of(' '.join(n for n in (e.get('notes') or []) if n.startswith('guide text'))) or None
        roles = SPECS[cls][sp][1]
        if cls == 'druid' and sp == 'feral_combat':
            pg = e.get('method_spec_page') or ''
            if pg == 'feral-dps-druid': roles = ['damage']
            elif pg == 'feral-tank-druid': roles = ['tank']
            else: roles = ['damage', 'tank']; e['role_note'] = 'hybrid bear/cat build; listed under both roles'
        if e.get('role_override'): roles = e['role_override']
        for r in roles:
            specs[sp]['endgame'].setdefault(r, []).append(e)
    doc = {'class': cls, 'generated': TODAY, 'generator': 'wowsim/pipeline/talents/build_routes.py',
           'talents_file': f'data/talents/{cls}.json', 'code_format': 'see data/talents/%s.json code_format; codes here are re-encoded from each source\'s own data' % cls,
           'level_rule': 'order[i] is the point spent at level 10 + i',
           'sources_tried': {
               'Maxroll': 'leveling guide planner profiles (point order): fetched',
               'Method.gg': 'leveling guide + spec "talents" pages (embeds with point order): fetched',
               'Warcraft Tavern': 'leveling guide + spec guides (Warcraft DB ordered links): fetched',
               'wowtbc.gg': 'Warcraft Forever class guides (page-data JSON: level 60 builds and a "Leveling 1-60" point order): fetched',
               'timesaver.gg': 'calculator presets (secondary transcriptions of Maxroll, Wowhead, Icy Veins, Method)',
               'Wowhead, Icy Veins, Mobalytics': 'blocked by Cloudflare from this sandbox (HTTP 403/202 challenge); only timesaver.gg transcriptions of their codes are included, marked secondary',
               'wowsims-forever': 'sim presets are not guides; used only as decode checks (see data/talents/README.md)'},
           'specs': specs, 'excluded': routes[cls]['excluded']}
    json.dump(doc, open(f'{OUT}/{cls}.json', 'w'), indent=1, ensure_ascii=False)
    summary[cls] = {sp: {'leveling': [(e['source']['site'], e['name'], e['kind'], e['final']['split'], e['final']['points'],
                                        (e.get('order_check') or {}).get('ok'), e['final']['legal_on_client_tree'] == 'OK') for e in v['leveling']],
                         'endgame': {r: [(e['source']['site'], e['name'], e['final']['split'], e['final']['legal_on_client_tree'] == 'OK') for e in lst] for r, lst in v['endgame'].items()}}
                    for sp, v in specs.items()}
json.dump(summary, open('/home/claude/work/talents/routes_summary.json', 'w'), indent=1)
for cls, s in summary.items():
    print('=====', cls)
    for sp, v in s.items():
        print('  ', sp, 'LEVELING:', [(a, b[:28], c[:5], d, f, g, h) for a, b, c, d, f, g, h in v['leveling']])
        for r, lst in v['endgame'].items():
            print('      ', r, [(a[:12], b[:30], c, d) for a, b, c, d in lst])
