"""Parse data/skills.lua of the MissingTradeSkillsList addon (Classic Era) into {spellId: {...}}.

For every Classic recipe it gives the skill at which it can be learned, and for trainer recipes the trainer's fee.
Forever moved many recipes down the skill range; build_data.py moves the Classic learn skill by the same amount.
"""
import re, sys, collections

SECTION = re.compile(r'^\t\["([^"]+)"\] = \{\n(.*?)^\t\},', re.M | re.S)


def field(block, name):
    m = re.search(r'^\t\t\t\["%s"\] = (\d+),' % name, block, flags=re.M)
    return int(m.group(1)) if m else None


def parse(path):
    s = open(path, encoding='utf-8').read()
    out = {}
    for sec in SECTION.finditer(s):
        for block in re.split(r'^\t\t\{\n', sec.group(2), flags=re.M)[1:]:
            sid, learn = field(block, 'id'), field(block, 'min_skill')
            if sid is None or learn is None:
                continue
            fee = re.search(r'^\t\t\t\["trainers"\] = \{\s*\["price"\] = (\d+)', block, flags=re.M)
            if fee:
                kind = 'trainer'
            elif 'auto learned' in block:
                kind = 'auto'
            elif re.search(r'^\t\t\t\["items"\]', block, flags=re.M):
                kind = 'item'
            else:
                kind = 'other'
            out[sid] = {'learn': learn, 'kind': kind, 'fee': int(fee.group(1)) if fee else 0, 'prof': sec.group(1)}
    return out


if __name__ == '__main__':
    d = parse(sys.argv[1])
    print(len(d), collections.Counter(v['kind'] for v in d.values()))
