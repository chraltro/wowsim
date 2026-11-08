# Decode checks for the calculator code order, per class. Output: /home/claude/work/talents/decode_checks.json
#  A. Maxroll planner (TraitNodeEntry ids, client ids) end state == timesaver.gg preset code decoded with codeOrder.
#  B. Method.gg embed loadout (its own bit format over client TraitNode ids) == timesaver preset code citing Method,
#     and Method order end state == Method loadout.
#  C. Talent names linked in the guide's talent text are present in the decoded build(s).
#  D. wowsims-forever preset talent strings decode to legal 51-point builds.
import json, re, sys, html as H
sys.path.insert(0, '/home/claude/wowsim/pipeline/talents')
import lib, method_decode as MD
CL = lib.load_classes()
D = '/home/claude/dl/talents_all'
WSP = {  # wowsims-forever commit 125e534 preset strings (path: string)
    'shaman': {'ui/specs/shaman/elemental/builds/testing.build.json': '5500331023001351-05500001-053',
               'ui/specs/shaman/elemental/presets.ts ManaTideTalents': '5500331013001351-04-053150001001',
               'ui/specs/shaman/enhancement/builds/testing.build.json': '053303102-053030310051002251-03'},
    'priest': {'ui/specs/priest/healer/presets.ts DiscTalents': '005025021330011531-335001030301',
               'ui/specs/priest/healer/presets.ts HolyTalents': '00520101133-33505003030121531',
               'ui/specs/priest/dps/builds/testing.build.json': '00530300103-3-50042201251302051',
               'ui/specs/priest/dps/builds/smite_testing.build.json': '525235031030001001-30515100002-3'},
    'paladin': {'ui/specs/paladin/retribution/builds/unsealed_wrath.siml': '050250002-501-05233011201301351',
                'ui/specs/paladin/retribution/builds/holy_shock.siml': '05025210221021--0523330110130033'},
}

def names(tabs, alloc):
    B = lib.by_id(tabs)
    return sorted(f'{B[k]["name"]} {v}/{B[k]["max"]}' for k, v in alloc.items())

def maxroll_text_names(cls):
    s = open(f'{D}/maxroll/{cls}-leveling-guide.html').read()
    i = s.find('id="talents-header"')
    j = s.find('<h2 id=', i + 10)
    seg = s[i:j if j > 0 else i + 200000]
    return sorted(set(H.unescape(x).strip() for x in re.findall(r'class="wow-(?:trait|spell)"[^>]*>([^<]+)<', seg)))

out = {}
TS = {c: json.load(open(f'{D}/ts/{c}.json'))['presets'] for c in lib.CLASSES}
MXD = json.load(open('/home/claude/work/talents/method_decoded.json'))
for cls in lib.CLASSES:
    tabs = CL[cls]; B = lib.by_id(tabs)
    talent_names = {t['name'] for tab in tabs for t in tab['talents']}
    checks = []
    entry = {t['entry_id']: t['id'] for tab in tabs for t in tab['talents']}
    mx = json.load(open(f'{D}/maxroll/{cls}.json'))
    union = {}
    for p in mx['profiles']:
        seq = [entry[e] for e in p['history'] if e in entry]
        alloc, _ = lib.check_order(tabs, seq)
        for k, v in alloc.items(): union[k] = max(union.get(k, 0), v)
        code = lib.encode(tabs, alloc)
        for x in TS[cls]:
            if x['source']['name'] == 'Maxroll' and x['code'] == code:
                dec, err = lib.decode(tabs, x['code'])
                checks.append({'check': 'A', 'published': f'timesaver.gg preset "{x["name"]}" code {x["code"]} (cites {x["source"]["url"]})',
                               'against': f'Maxroll planner profile "{p["name"]}" ({mx["meta"]["url"]}), TraitNodeEntry ids mapped through the client',
                               'decoded': names(tabs, dec), 'match': dec == alloc and not err})
    # C: names in Maxroll text
    tn = [n for n in maxroll_text_names(cls) if n in talent_names]
    missing = [n for n in tn if not any(B[k]['name'] == n for k in union)]
    checks.append({'check': 'C', 'published': f'Maxroll guide talent section text ({mx["meta"]["url"]})', 'talents_named_in_text': tn,
                   'named_but_not_in_any_profile_build': missing, 'match': not missing})
    # B: Method vs timesaver presets that cite Method
    for m in [m for m in MXD if m['class'] == cls]:
        for x in TS[cls]:
            if x['source']['name'] == 'Method' and x['code'] == m['code']:
                dec, err = lib.decode(tabs, x['code'])
                checks.append({'check': 'B', 'published': f'timesaver.gg preset "{x["name"]}" code {x["code"]} (cites {x["source"]["url"]})',
                               'against': f'Method embed on {m["page"]} decoded from its own loadout bit string (client TraitNode ids)',
                               'decoded': names(tabs, dec), 'match': dec == m['final']})
        if m['order']:
            alloc, _ = lib.check_order(tabs, m['order'])
            checks.append({'check': 'B2', 'published': f'Method embed {m["page"]} #{m["idx"]}', 'against': 'its own point order string',
                           'match': alloc == m['final'], 'code': m['code']})
    # D: wowsims presets
    for path, code in WSP.get(cls, {}).items():
        dec, err = lib.decode(tabs, code)
        checks.append({'check': 'D', 'published': f'wowsims-forever {path}: {code}', 'decoded': names(tabs, dec), 'split': lib.split(tabs, dec),
                       'legal': lib.check_alloc(tabs, dec) or 'OK', 'match': not err and not lib.check_alloc(tabs, dec) and lib.encode(tabs, dec) == code})
    out[cls] = checks
    print(cls, [(c['check'], c['match']) for c in checks])
json.dump(out, open('/home/claude/work/talents/decode_checks.json', 'w'), indent=1)
