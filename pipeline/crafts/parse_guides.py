"""Parse the Waylaid Crate, Craftsman's Writ and Merchant's Favor tables from two guides into guides.json.

raw/guides/method_crates.html  https://www.method.gg/wow-forever/how-to-get-waylaid-crates-and-merchants-favor-in-wow-forever
raw/guides/wowgg_favor.html    https://wow.gg/guides/merchants-favor
Names stay as the guides print them; build_data.py resolves them to item ids and reports any it cannot find.
"""
import re, html, json, os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
RAW = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, 'raw')

def text(path):
    s = open(path, encoding='utf-8', errors='ignore').read()
    s = re.sub(r'<script.*?</script>', '', s, flags=re.S); s = re.sub(r'<style.*?</style>', '', s, flags=re.S)
    s = re.sub(r'<(br|/p|/tr|/li|/h\d|/div)[^>]*>', '\n', s); s = re.sub(r'</t[dh]>', ' | ', s)
    s = re.sub(r'<[^>]+>', '', s); s = html.unescape(s)
    s = re.sub(r'[ \t]+', ' ', s)
    return re.sub(r'\n\s*\n+', '\n', s)

# --- Method: every crate with its fills (any one of them completes the crate)
m = text(os.path.join(RAW, 'guides/method_crates.html'))
lines = [l.strip() for l in m.split('\n')]
crates = []
i = 0
while i < len(lines):
    mm = re.match(r'(Waylaid Crate: (Apprentice|Journeyman|Expert|Artisan|Earthly|Flowering)[^|]*) \|$', lines[i])
    if mm and i + 2 < len(lines) and re.match(r'\d+ \|$', lines[i + 1]):
        name = mm.group(1).strip()
        level = int(lines[i + 1].split()[0])
        fills = []
        j = i + 2
        while j < len(lines):
            f = re.match(r'(\d+) (.+?)( \|)?$', lines[j])
            if not f: break
            fills.append([f.group(2).strip(), int(f.group(1))])
            j += 1
            if f.group(3): break
        tier = next(t for t in ('Apprentice', 'Journeyman', 'Expert', 'Artisan') if t in name)
        if not any(c['name'] == name for c in crates):
            crates.append({'name': name, 'tier': tier, 'level': level, 'fills': fills})
        i = j
    else:
        i += 1

# --- wow.gg: favor per crate, writs, favor recipe catalog
w = text(os.path.join(RAW, 'guides/wowgg_favor.html'))
favor = {}
a = w.find('How Much Currency Crates Reward', w.find('How Much Currency Crates Reward') + 10)
for l in w[a:a + 600].split('\n'):
    f = re.match(r'(Apprentice|Journeyman|Expert|Artisan) \| (Common|Uncommon)[^|]*\| (\d+) \|', l)
    if f: favor.setdefault(f.group(1), {})['1' if f.group(2) == 'Common' else '2'] = int(f.group(3))
writs = []
a = w.find("All Craftsman's Writs", 2000); b = w.find('Where to Turn In Craftsman', a + 50)
prof = None
for l in w[a:b].split('\n'):
    l = l.strip()
    if l in ('Alchemy', 'Blacksmithing', 'Engineering', 'Leatherworking', 'Tailoring'): prof = l
    f = re.match(r"Craftsman's Writ: [^|]*\| (.+?) ×(\d+) \| (\d+) \| (\w+) \| (\d+) \|", l)
    if f: writs.append({'item': f.group(1).strip(), 'qty': int(f.group(2)), 'skill': int(f.group(3)), 'tier': f.group(4), 'rep': int(f.group(5)), 'prof': prof})
recipes = []
a = w.find('All Recipes and Certificates', w.find('Total Cost of a Profession'))
for l in w[a:].split('\n'):
    f = re.match(r'((?:Recipe|Pattern|Plans|Schematic|Formula|Manual|Design)[^|]*?) \| (\d+) \| (\d+) \| ([A-Za-z]*) ?\|', l.strip())
    if f: recipes.append({'name': f.group(1).strip(), 'skill': int(f.group(2)), 'favor': int(f.group(3)), 'rep': f.group(4)})

out = {
    'sources': {
        'crates': 'https://www.method.gg/wow-forever/how-to-get-waylaid-crates-and-merchants-favor-in-wow-forever',
        'favor, writs and favor recipes': 'https://wow.gg/guides/merchants-favor',
    },
    'crates': crates, 'favor_per_crate': favor, 'writs': writs, 'favor_recipes': recipes,
}
json.dump(out, open(os.path.join(HERE, 'guides.json'), 'w'), indent=1, ensure_ascii=False)
print(len(crates), 'crates,', favor, len(writs), 'writs,', len(recipes), 'favor recipes')
