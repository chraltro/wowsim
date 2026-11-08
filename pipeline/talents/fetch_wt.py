# Fetch Warcraft Tavern WoW Forever spec and leveling guides; pull every Warcraft DB calculator link (#?t=<ordered build>)
# with its link text, nearest heading and the page's dates. Output: /home/claude/dl/talents_all/wt/links.json
import re, json, subprocess, os, html as H, datetime
OUT = '/home/claude/dl/talents_all/wt'
SPECS = ['affliction-warlock', 'arcane-mage', 'arms-warrior', 'assassination-rogue', 'balance-druid', 'beast-mastery-hunter', 'combat-rogue',
         'demonology-warlock', 'destruction-warlock', 'discipline-priest', 'elemental-shaman', 'enhancement-shaman', 'feral-druid', 'fire-mage',
         'frost-mage', 'fury-warrior', 'holy-paladin', 'holy-priest', 'marksmanship-hunter', 'protection-paladin', 'protection-warrior',
         'restoration-druid', 'restoration-shaman', 'retribution-paladin', 'shadow-priest', 'subtlety-rogue', 'survival-hunter']
LEV = ['druid-leveling', 'hunter-leveling', 'mage-leveling', 'paladin-leveling', 'priest-leveling', 'rogue-leveling', 'shaman-leveling', 'warlock-leveling', 'warrior-leveling']

def get(slug):
    p = f'{OUT}/{slug}.html'
    if not os.path.exists(p):
        h = subprocess.run(['curl', '-sS', '-A', 'Mozilla/5.0', f'https://www.warcrafttavern.com/forever/guides/{slug}/'], capture_output=True, text=True).stdout
        open(p, 'w').write(h)
    return open(p).read()

def text_of(s):
    s = re.sub(r'<(script|style)[^>]*>.*?</\1>', ' ', s, flags=re.S)
    return re.sub(r'\s+', ' ', H.unescape(re.sub(r'<[^>]+>', ' ', s))).strip()

res = []
for slug in SPECS + LEV:
    s = get(slug)
    meta = {}
    for k, pat in [('title', r'<title>([^<]*)'), ('modified', r'"dateModified":"([^"]+)"'), ('published', r'"datePublished":"([^"]+)"'),
                   ('author', r'"author":\{"@type":"Person","name":"([^"]+)"'), ('updated_text', r'(?:Last updated|Updated)[^<]{0,10}<[^>]*>?\s*([^<]{4,40})')]:
        m = re.search(pat, s)
        meta[k] = H.unescape(m.group(1)).strip() if m else None
    links = []
    for m in re.finditer(r'<a[^>]+href="(https://www\.warcrafttavern\.com/forever/tools/talent-calculator/(\w+)#\?t=([^"]*))"[^>]*>(.*?)</a>', s, re.S):
        before = s[:m.start()]
        heads = re.findall(r'<h([1-4])[^>]*>(.*?)</h\1>', before, re.S)
        links.append({'url': H.unescape(m.group(1)), 'class': m.group(2), 't': H.unescape(m.group(3)), 'link_text': text_of(m.group(4)),
                      'heading': text_of(heads[-1][1]) if heads else None, 'headings_path': [text_of(h[1]) for h in heads[-3:]],
                      'context_before': text_of(before[-2500:])[-600:]})
    res.append({'slug': slug, 'url': f'https://www.warcrafttavern.com/forever/guides/{slug}/', 'fetched': datetime.date.today().isoformat(), 'meta': meta, 'links': links})
    print(slug, meta['modified'], meta['author'], len(links), [(l['class'], l['link_text'][:40], l['heading'][:40] if l['heading'] else None) for l in links][:6])
json.dump(res, open(f'{OUT}/links.json', 'w'), indent=1)
