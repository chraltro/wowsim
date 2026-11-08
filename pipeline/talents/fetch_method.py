# Fetch Method.gg WoW Forever leveling guides and spec talent pages, and pull every talent embed with its context
# (nearest heading, tab label, surrounding text). Output: /home/claude/dl/talents_all/method/embeds.json
import re, json, subprocess, html as H, datetime, os
OUT = '/home/claude/dl/talents_all/method'
CLASSES = ['druid', 'hunter', 'mage', 'paladin', 'priest', 'rogue', 'shaman', 'warlock', 'warrior']
SPECS = ['affliction-warlock', 'arcane-mage', 'arms-warrior', 'assassination-rogue', 'balance-druid', 'beast-mastery-hunter',
         'combat-rogue', 'demonology-warlock', 'destruction-warlock', 'feral-dps-druid', 'feral-tank-druid', 'fire-mage',
         'frost-mage', 'fury-warrior', 'holy-paladin', 'marksmanship-hunter', 'protection-paladin', 'protection-warrior',
         'restoration-druid', 'shadow-priest', 'subtlety-rogue', 'survival-hunter']
SPEC_CLASS = {s: s.split('-')[-1] for s in SPECS}

def get(url, path):
    if not os.path.exists(path):
        h = subprocess.run(['curl', '-sS', '-A', 'Mozilla/5.0', url], capture_output=True, text=True).stdout
        open(path, 'w').write(h)
    return open(path).read()

def text_of(s):
    s = re.sub(r'<(script|style)[^>]*>.*?</\1>', ' ', s, flags=re.S)
    return re.sub(r'\s+', ' ', H.unescape(re.sub(r'<[^>]+>', ' ', s))).strip()

def meta(s):
    m = {}
    for k, pat in [('title', r'<title>([^<]*)'), ('updated', r'Last Updated: </strong>\s*([^<]+)</span>'), ('patch', r'guide-patch">([^<]+)<'),
                   ('author', r'(?:author-name|guide-custom-author)">([^<]+)<')]:
        x = re.search(pat, s)
        m[k] = H.unescape(x.group(1)) if x else None
    return m

def embeds(s):
    out = []
    # tab labels: <a ... href="#tabs-XXXX-N" ...>Label</a>
    tablabel = {m.group(1): text_of(m.group(2)) for m in re.finditer(r'href="#((?:tabs-[A-Za-z0-9]+-|talentBuildTab_)\d+)"[^>]*>(.*?)</a>', s, re.S)}
    for m in re.finditer(r'data-talent="([^"]+)"', s):
        pos = m.start()
        before = s[:pos]
        heads = re.findall(r'<h([1-4])[^>]*>(.*?)</h\1>', before, re.S)
        heading = text_of(heads[-1][1]) if heads else None
        panes = list(re.finditer(r'id="((?:tabs-[A-Za-z0-9]+-|talentBuildTab_)\d+)"', before))
        tab = tablabel.get(panes[-1].group(1)) if panes else None
        # paragraph text just before the embed (same pane)
        start = panes[-1].end() if panes else max(0, pos - 4000)
        ctx = text_of(before[start:])[-1500:]
        after = s[m.end():]
        nxt = re.search(r'id="((?:tabs-[A-Za-z0-9]+-|talentBuildTab_)\d+)"|data-talent=', after)
        ctx_after = text_of(after[:nxt.start() if nxt else 6000])[:1500]
        out.append({'data_talent': H.unescape(m.group(1)), 'heading': heading, 'tab': tab, 'context_before': ctx, 'context_after': ctx_after})
    return out

res = []
today = datetime.date.today().isoformat()
for c in CLASSES:
    url = f'https://www.method.gg/wow-forever/wow-forever-{c}-leveling-guide-and-talents'
    s = get(url, f'{OUT}/lev_{c}.html')
    res.append({'class': c, 'kind': 'leveling', 'url': url, 'fetched': today, 'meta': meta(s), 'embeds': embeds(s)})
for sp in SPECS:
    url = f'https://www.method.gg/wow-forever/class-guides/{sp}/talents'
    s = get(url, f'{OUT}/spec_{sp}_talents.html')
    res.append({'class': SPEC_CLASS[sp], 'spec_page': sp, 'kind': 'spec_talents', 'url': url, 'fetched': today, 'meta': meta(s), 'embeds': embeds(s)})
json.dump(res, open(f'{OUT}/embeds.json', 'w'), indent=1)
for r in res:
    print(r['class'], r['kind'], r.get('spec_page', ''), r['meta']['title'], r['meta']['updated'], r['meta']['author'], len(r['embeds']), [(e['heading'], e['tab']) for e in r['embeds']][:8])
