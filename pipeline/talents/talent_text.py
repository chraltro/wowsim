# Resolve a talent spell's client description into per-rank text, using the Forever client DB2 tables
# (build 1.60.1.70862, wago.tools CSV). Rank values come from TraitDefinitionEffectPoints curves
# (CurvePoint Pos_0 = rank, Pos_1 = value); effects without a curve use SpellEffect.EffectBasePointsF.
# Tokens this resolver cannot evaluate are left in the text as {?token} and reported.
import csv, collections, re, math

W = '/home/claude/ext/wago_talents'
B = '70862'

def _rows(t):
    with open(f'{W}/{t}_{B}.csv', newline='') as f:
        return list(csv.DictReader(f))

class Client:
    def __init__(self):
        I = int
        self.name = {I(r['ID']): r['Name_lang'] for r in _rows('SpellName')}
        self.spell = {I(r['ID']): r for r in _rows('Spell')}
        self.eff = collections.defaultdict(dict)
        for r in _rows('SpellEffect'):
            if r['DifficultyID'] == '0':
                self.eff[I(r['SpellID'])][I(r['EffectIndex'])] = r
        self.misc = {}
        for r in _rows('SpellMisc'):
            if r['DifficultyID'] == '0':
                self.misc[I(r['SpellID'])] = r
        self.dur = {I(r['ID']): r for r in _rows('SpellDuration')}
        self.radius = {I(r['ID']): r for r in _rows('SpellRadius')}
        self.aura = {}
        for r in _rows('SpellAuraOptions'):
            if r['DifficultyID'] == '0':
                self.aura[I(r['SpellID'])] = r
        self.curve = collections.defaultdict(list)
        for r in _rows('CurvePoint'):
            self.curve[I(r['CurveID'])].append((float(r['Pos_0']), float(r['Pos_1'])))
        self.tdep = collections.defaultdict(dict)
        for r in _rows('TraitDefinitionEffectPoints'):
            self.tdep[I(r['TraitDefinitionID'])][I(r['EffectIndex'])] = (I(r['OperationType']), I(r['CurveID']))
        dv = {I(r['ID']): r['Variables'] for r in _rows('SpellDescriptionVariables')}
        self.descvars = collections.defaultdict(dict)
        for r in _rows('SpellXDescriptionVariables'):
            txt = dv.get(I(r['SpellDescriptionVariablesID']), '')
            for m in re.finditer(r'\$(\w+)=(\$\{.*?\}|[^\n]+)', txt):
                self.descvars[I(r['SpellID'])][m.group(1)] = m.group(2).strip()
        self.levels = {}
        for r in _rows('SpellLevels'):
            if r['DifficultyID'] == '0':
                self.levels[I(r['SpellID'])] = r
        self.cooldown = {}
        for r in _rows('SpellCooldowns'):
            if r['DifficultyID'] == '0':
                self.cooldown[I(r['SpellID'])] = r

    def curve_at(self, cid, x):
        pts = sorted(self.curve[cid])
        for px, py in pts:
            if abs(px - x) < 1e-9:
                return py
        # linear interpolation / clamp
        if not pts:
            return None
        if x <= pts[0][0]: return pts[0][1]
        if x >= pts[-1][0]: return pts[-1][1]
        for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
            if x0 <= x <= x1:
                return y0 + (y1 - y0) * (x - x0) / (x1 - x0)

    def effect_points(self, spell_id, idx, rank=None, definition_id=None):
        """Value of effect idx (0-based). For the talent's own spell, use the trait curve for the rank."""
        if definition_id is not None and rank is not None and idx in self.tdep.get(definition_id, {}):
            op, cid = self.tdep[definition_id][idx]
            v = self.curve_at(cid, rank)
            if v is not None:
                return v, 'curve'
        e = self.eff.get(spell_id, {}).get(idx)
        if e is None:
            return None, 'missing'
        v = float(e['EffectBasePointsF'])
        ppl = float(e['EffectRealPointsPerLevel'] or 0)
        if ppl:
            lv = self.levels.get(spell_id)
            base = int(lv['BaseLevel']) if lv else 0
            mx = int(lv['MaxLevel']) if lv and int(lv['MaxLevel']) else LEVEL
            v += ppl * (min(LEVEL, mx) - base)
            return v, 'level%d' % LEVEL
        return v, 'base'

    def variance(self, spell_id, idx):
        e = self.eff.get(spell_id, {}).get(idx)
        return float(e['Variance'] or 0) if e else 0.0

    def duration_ms(self, spell_id):
        m = self.misc.get(spell_id)
        if not m: return None
        d = self.dur.get(int(m['DurationIndex']))
        return int(d['Duration']) if d else None

def fmt_num(v, decimals=None):
    if v is None: return '?'
    if decimals is not None:
        return f'{v:.{decimals}f}'
    if abs(v - round(v)) < 1e-6:
        return str(int(round(v)))
    s = f'{v:.2f}'.rstrip('0').rstrip('.')
    return s

def fmt_time(ms):
    if ms is None: return '?'
    s = ms / 1000
    if s >= 3600 and s % 3600 == 0: return f'{int(s//3600)} hour' + ('s' if s // 3600 > 1 else '')
    if s >= 60 and s % 60 == 0: return f'{int(s//60)} min'
    return f'{fmt_num(s)} sec'

LEVEL = 60  # level used for level-scaled effect points (granted abilities)
TOKEN = re.compile(r'\$(?:(\d+))?([smMoatdhnuxbieqS])(\d)?(?![a-zA-Z])')

def resolve(cl, spell_id, rank, definition_id, text=None, depth=0):
    """Return (text, unresolved_tokens, values) for one rank."""
    if text is None:
        text = cl.spell.get(spell_id, {}).get('Description_lang', '') or ''
    unresolved = []
    last_number = [None]

    def val(tok_spell, letter, idx, signed=False):
        sid = int(tok_spell) if tok_spell else spell_id
        own = (sid == spell_id)
        i = int(idx) - 1 if idx else 0
        if letter in 'smMSb':
            if letter == 'b':
                e = cl.eff.get(sid, {}).get(i)
                return float(e['EffectPointsPerResource']) if e else None
            v, src = cl.effect_points(sid, i, rank if own else None, definition_id if own else None)
            if v is None: return None
            var = cl.variance(sid, i)
            if signed:
                return v
            if letter in 'sS' and var and src != 'curve':
                return ('range', abs(v) * (1 - var / 2), abs(v) * (1 + var / 2))
            return abs(v)
        if letter == 'd':
            ms = cl.duration_ms(sid)
            return ('time', ms)
        if letter == 't':
            e = cl.eff.get(sid, {}).get(i)
            return float(e['EffectAuraPeriod']) / 1000 if e and float(e['EffectAuraPeriod']) else None
        if letter == 'o':
            e = cl.eff.get(sid, {}).get(i)
            v, src = cl.effect_points(sid, i, rank if own else None, definition_id if own else None)
            ms = cl.duration_ms(sid)
            if e and v is not None and ms and float(e['EffectAuraPeriod']):
                return abs(v) * ms / float(e['EffectAuraPeriod'])
            return None
        if letter == 'a':
            e = cl.eff.get(sid, {}).get(i)
            if e:
                r = cl.radius.get(int(e['EffectRadiusIndex_0']))
                return float(r['Radius']) if r else None
            return None
        if letter == 'h':
            a = cl.aura.get(sid); return float(a['ProcChance']) if a else None
        if letter == 'n':
            a = cl.aura.get(sid); return float(a['ProcCharges']) if a else None
        if letter == 'u':
            a = cl.aura.get(sid); return float(a['CumulativeAura']) if a else None
        if letter == 'x':
            e = cl.eff.get(sid, {}).get(i); return float(e['EffectChainTargets']) if e else None
        if letter == 'e':
            e = cl.eff.get(sid, {}).get(i); return float(e['EffectAmplitude']) if e else None
        if letter == 'i':
            return None
        if letter == 'q':
            e = cl.eff.get(sid, {}).get(i); return float(e['EffectMiscValue_0']) if e else None
        return None

    def expr_value(expr):
        # substitute tokens inside ${...}
        def sub(m):
            v = val(m.group(1), m.group(2), m.group(3), signed=True)
            if isinstance(v, tuple): v = (v[1] + v[2]) / 2 if v[0] == 'range' else (v[1] or 0) / 1000
            if v is None:
                unresolved.append(m.group(0)); return 'None'
            return repr(v)
        e2 = TOKEN.sub(sub, expr)
        e2 = re.sub(r'\$(\w+)', lambda m: (unresolved.append('$' + m.group(1)) or 'None'), e2)
        e2 = e2.replace('<', '').replace('>', '')
        try:
            if 'None' in e2: return None
            if not re.fullmatch(r'[\d\.\s\+\-\*/\(\)eE]+', e2):
                unresolved.append('${' + expr + '}'); return None
            return eval(e2, {'__builtins__': {}})
        except Exception:
            unresolved.append('${' + expr + '}'); return None

    out = []
    i = 0
    s = text
    while i < len(s):
        ch = s[i]
        if ch != '$':
            out.append(ch); i += 1; continue
        rest = s[i:]
        # ${expr}.N
        m = re.match(r'\$\{(.*?)\}(?:\.(\d))?', rest)
        if m:
            v = expr_value(m.group(1))
            if v is None:
                out.append('{?' + m.group(0) + '}')
            else:
                out.append(fmt_num(v, int(m.group(2)) if m.group(2) else None)); last_number[0] = v
            i += len(m.group(0)); continue
        # $/N;token or $*N;token
        m = re.match(r'\$([/*])(\d+(?:\.\d+)?);\$?(?:(\d+))?([smMoatdhnuxbS])(\d)?', rest)
        if m:
            v = val(m.group(3), m.group(4), m.group(5))
            if isinstance(v, tuple): v = (v[1] + v[2]) / 2 if v[0] == 'range' else (v[1] or 0) / 1000
            if v is None:
                out.append('{?' + m.group(0) + '}'); unresolved.append(m.group(0))
            else:
                v = v / float(m.group(2)) if m.group(1) == '/' else v * float(m.group(2))
                out.append(fmt_num(v)); last_number[0] = v
            i += len(m.group(0)); continue
        # $l / $L plural
        m = re.match(r'\$[lL]([^:;]*):([^;]*);', rest)
        if m:
            n = last_number[0]
            out.append(m.group(1) if n is not None and abs(n - 1) < 1e-9 else m.group(2))
            i += len(m.group(0)); continue
        # $g male:female;
        m = re.match(r'\$[gG]([^:;]*):([^;]*);', rest)
        if m:
            out.append(m.group(1)); i += len(m.group(0)); continue
        # $?cond[a][b]
        m = re.match(r'\$\?([a-zA-Z!]*\d+(?:[&|][a-zA-Z!]*\d+)*)\[([^\]]*)\]\[([^\]]*)\]', rest)
        if m:
            out.append('{?if ' + m.group(1) + ': ' + m.group(2) + ' | else: ' + m.group(3) + '}')
            unresolved.append('$?' + m.group(1)); i += len(m.group(0)); continue
        # $<var>
        m = re.match(r'\$<(\w+)>', rest)
        if m:
            var = m.group(1)
            dv = cl.descvars.get(spell_id, {}).get(var)
            v = None
            if dv:
                inner = dv
                mm = re.fullmatch(r'\$\{(.*)\}', inner)
                v = expr_value(mm.group(1) if mm else inner)
            if v is None:
                out.append('{?$<' + var + '>}'); unresolved.append('$<' + var + '>')
            else:
                out.append(fmt_num(v)); last_number[0] = v
            i += len(m.group(0)); continue
        # $@spelldescN / $@spelltooltipN
        m = re.match(r'\$@(spelldesc|spelltooltip|spellname)(\d+)', rest)
        if m:
            sid = int(m.group(2))
            if m.group(1) == 'spellname':
                out.append(cl.name.get(sid, '?'))
            elif depth < 2:
                t2, u2, _ = resolve(cl, sid, None, None, depth=depth + 1)
                out.append(t2); unresolved.extend(u2)
            i += len(m.group(0)); continue
        # plain token
        m = TOKEN.match(rest)
        if m:
            v = val(m.group(1), m.group(2), m.group(3))
            if isinstance(v, tuple) and v[0] == 'range':
                out.append(fmt_num(round(v[1])) + ' to ' + fmt_num(round(v[2]))); last_number[0] = v[2]
            elif isinstance(v, tuple):
                out.append(fmt_time(v[1])); last_number[0] = (v[1] or 0) / 1000
            elif v is None:
                out.append('{?' + m.group(0) + '}'); unresolved.append(m.group(0))
            else:
                out.append(fmt_num(v)); last_number[0] = v
            i += len(m.group(0)); continue
        # named variable like $apm, $mcrit, $pl, $SPFR
        m = re.match(r'\$([a-zA-Z]+)', rest)
        if m:
            var = m.group(1)
            dv = cl.descvars.get(spell_id, {}).get(var)
            v = None
            if dv:
                mm = re.fullmatch(r'\$\{(.*)\}', dv)
                v = expr_value(mm.group(1) if mm else dv)
            if v is None:
                out.append('{?$' + var + '}'); unresolved.append('$' + var)
            else:
                out.append(fmt_num(v)); last_number[0] = v
            i += len(m.group(0)); continue
        out.append('$'); i += 1
    txt = ''.join(out)
    return txt, unresolved, None
