# Decode Method.gg WoW Forever talent embeds (data-talent="<loadout>;<order>").
# Re-implements the reading side of https://www.method.gg/dfc/ForeverTalents.min.js (version 1.60.1-2nov) in Python;
# no Method code is run. Node lists come from Method's own data file /dfc/ForeverTalentsData-1.60.1-2nov.json,
# whose node ids are the client's TraitNode ids.
#  - order part: one base64 character per point; character k = the k-th node of the class when all of its tab nodes
#    are sorted by numeric node id.
#  - loadout part: bit stream (6 bits per base64 char, least significant bit first): 8 bits version, 16 bits spec id,
#    16 x 8 bits tree hash, then for every node in the same sorted order: 1 bit selected, and if selected 1 bit purchased,
#    1 bit partial (+6 bits rank when partial), 1 bit choice node (+2 bits entry index).
import json
B64 = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/'
DATA = '/home/claude/dl/talents_all/method/ForeverTalentsData-1.60.1-2nov.json'
SPEC = {'MAGE': 1482, 'DRUID': 1484, 'HUNTER': 1485, 'PALADIN': 1486, 'PRIEST': 1487, 'ROGUE': 1488, 'SHAMAN': 1489, 'WARLOCK': 1490, 'WARRIOR': 1491}
_d = json.load(open(DATA))

def class_nodes(cls):
    tabs = sorted(_d['classes'][cls.upper()]['tabs'], key=lambda t: t['order'])
    out = []
    for ti, tab in enumerate(tabs):
        tree = _d.get(tab['treeID'], {})
        for nid, n in tree.items():
            if n.get('curFlag') == tab['curFlag'] and (len(n.get('spells', [])) != 0 or n.get('rankDetails')):
                out.append((ti, int(nid), n))
    out.sort(key=lambda x: x[1])
    return tabs, out

class Bits:
    def __init__(self, s):
        self.v = [B64.index(c) for c in s]; self.i = 0; self.b = 0
    def read(self, width):
        val = 0; shift = 0
        while width > 0:
            if self.i >= len(self.v): raise ValueError('out of data')
            ch = self.v[self.i] >> self.b
            avail = 6 - self.b
            take = min(avail, width)
            val |= (ch & ((1 << take) - 1)) << shift
            shift += take; width -= take; self.b += take
            if self.b == 6: self.b = 0; self.i += 1
        return val

def decode(cls, data_talent):
    tabs, nodes = class_nodes(cls)
    loadout, _, order = data_talent.partition(';')
    r = Bits(loadout)
    version = r.read(8); spec = r.read(16)
    for _ in range(16): r.read(8)
    ranks = {}
    for ti, nid, n in nodes:
        if r.read(1):
            purchased = r.read(1)
            partial = r.read(1)
            rank = r.read(6) if partial else n['maxRank']
            if r.read(1): r.read(2)
            if purchased:
                ranks[nid] = rank
    seq = []
    bad = []
    for ch in order:
        k = B64.index(ch)
        if k >= len(nodes): bad.append(ch); continue
        seq.append(nodes[k][1])
    return {'version': version, 'spec': spec, 'spec_ok': spec == SPEC[cls.upper()], 'final': ranks, 'order': seq, 'bad_chars': bad,
            'tab_names': [t['name'] for t in tabs]}
