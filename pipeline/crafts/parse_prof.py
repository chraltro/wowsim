"""Parse a MetaBot profession page into one dict per recipe row.

Every recipe row carries an aria-label like "Learn at 175; yellow from 200, green from 213, grey at 225".
A learn skill followed by * is MetaBot's own estimate: the client does not say when a trainer offers the recipe.
"""
import re, html, sys, collections

ROW = re.compile(r'<tr[^>]*>(.*?)</tr>', re.S)
LABEL = re.compile(r'aria-label="Learn at (\d+); yellow from (\d+), green from (\d+), grey at (\d+)"')
NAME = re.compile(r'<bdi class="[^"]*nameText[^"]*">(.*?)</bdi>', re.S)
REAGENT = re.compile(r'<li>.*?<bdi class="[^"]*nameText[^"]*">(.*?)</bdi>.*?<span class="[^"]*qty[^"]*">×(?:<!-- -->)?(\d+)</span>.*?</li>', re.S)
SOURCE = re.compile(r'<span class="[^"]*srcTag[^"]*"[^>]*>(.*?)</span>', re.S)
CELL = re.compile(r'<td[^>]*>(.*?)</td>', re.S)


def text(s):
    return html.unescape(re.sub(r'<[^>]+>', '', s)).strip()


def parse(path):
    s = open(path, encoding='utf-8', errors='ignore').read()
    s = re.sub(r'<script.*?</script>', '', s, flags=re.S)
    rows, seen = [], set()
    for body in ROW.findall(s):
        lab = LABEL.search(body)
        if not lab:
            continue
        cells = CELL.findall(body)
        name = NAME.search(cells[0]) if cells else None
        if not name or len(cells) < 4:
            continue
        learn, yellow, green, grey = (int(x) for x in lab.groups())
        reagents = [(text(a), int(q)) for a, q in REAGENT.findall(body)]
        src = SOURCE.search(body)
        row = {
            'name': text(name.group(1)), 'new': '>New<' in cells[0], 'learn': learn, 'est': '*' in text(cells[1]),
            'orange': learn, 'yellow': yellow, 'green': green, 'grey': grey, 'reagents': reagents,
            'source': text(src.group(1)) if src else '—',
        }
        key = (row['name'], tuple(reagents), learn, yellow, grey)
        if key in seen:   # the page repeats its tables
            continue
        seen.add(key)
        rows.append(row)
    return rows


if __name__ == '__main__':
    out = parse(sys.argv[1])
    print(len(out), collections.Counter(r['source'] for r in out), 'estimated learn:', sum(r['est'] for r in out))
    for r in out[:3]:
        print(r)
