# The remaining fetches behind data/talents and data/routes (run once on 2026-11-08; kept as a record):
#  - wago.tools DB2 CSV exports for the Forever build 1.60.1.70862  -> /home/claude/ext/wago_talents/<Table>_70862.csv
#  - Warcraft DB Forever talent API                                  -> /home/claude/dl/talents_all/wdb/<class>.json
#  - wowforevertalents.com class data (JSON.parse literal in its JS)  -> /home/claude/dl/talents_all/wft/wft_classes.json
#  - wowtbc.gg "Warcraft Forever" class guide page-data JSON         -> /home/claude/dl/talents_all/wowtbc/pd_<spec>.json
#  - Warcraft Tavern page "Last updated" dates and author slugs       -> /home/claude/dl/talents_all/wt/page_dates.json
import subprocess, json, re, os, glob, html as H, sys

def curl(url, path):
    subprocess.run(['curl', '-sS', '-A', 'Mozilla/5.0', '-o', path, url], check=True)

CLASSES = ['druid', 'hunter', 'mage', 'paladin', 'priest', 'rogue', 'shaman', 'warlock', 'warrior']
TABLES = ['Talent', 'TalentTab', 'TraitTree', 'TraitNode', 'TraitNodeEntry', 'TraitNodeXTraitNodeEntry', 'TraitDefinition', 'TraitEdge',
          'TraitDefinitionEffectPoints', 'TraitCond', 'TraitNodeGroup', 'TraitNodeGroupXTraitNode', 'TraitNodeGroupXTraitCond', 'TraitCurrency',
          'TraitTreeXTraitCurrency', 'SkillLine', 'SkillLineAbility', 'SpellName', 'Spell', 'SpellEffect', 'SpellMisc', 'SpellCategories',
          'SpellDescriptionVariables', 'SpellXDescriptionVariables', 'Curve', 'CurvePoint', 'SpellDuration', 'SpellRange', 'SpellCastTimes',
          'SpellCooldowns', 'SpellPower', 'SpellAuraOptions', 'SpellRadius', 'SpellTargetRestrictions', 'SpellProcsPerMinute', 'SpellClassOptions', 'SpellLevels']
WOWTBC = ['affliction-warlock', 'arcane-mage', 'arms-warrior', 'assassination-rogue', 'balance-druid', 'beast-mastery-hunter', 'combat-rogue',
          'demonology-warlock', 'destruction-warlock', 'discipline-priest', 'elemental-shaman', 'enhancement-shaman', 'feral-dps-druid', 'feral-tank-druid',
          'fire-mage', 'frost-mage', 'fury-warrior', 'holy-paladin', 'holy-priest', 'marksmanship-hunter', 'protection-paladin', 'protection-warrior',
          'restoration-druid', 'restoration-shaman', 'retribution-paladin', 'shadow-priest', 'subtlety-rogue', 'survival-hunter']

if 'wago' in sys.argv:
    os.makedirs('/home/claude/ext/wago_talents', exist_ok=True)
    for t in TABLES:
        curl(f'https://wago.tools/db2/{t}/csv?build=1.60.1.70862', f'/home/claude/ext/wago_talents/{t}_70862.csv')
if 'wdb' in sys.argv:
    for c in CLASSES:
        curl(f'https://forever.warcraftdb.com/api/v1/talents/{c}', f'/home/claude/dl/talents_all/wdb/{c}.json')
if 'wft' in sys.argv:
    D = '/home/claude/dl/talents_all/wft'
    curl('https://wowforevertalents.com/_astro/VotePair.BIlRC5wl.js', f'{D}/VotePair.BIlRC5wl.js')   # bundle named by /_astro/TalentCalculator.m0nqtEMz.js
    s = open(f'{D}/VotePair.BIlRC5wl.js').read()
    i = s.find('Y=JSON.parse(`') + len('Y=JSON.parse(`'); j = s.find('`)', i)
    json.dump(json.loads(s[i:j].replace('\\`', '`').replace('\\\\', '\\')), open(f'{D}/wft_classes.json', 'w'), indent=1)
if 'wowtbc' in sys.argv:
    for sp in WOWTBC:
        curl(f'https://wowtbc.gg/page-data/warcraftforever/class-guides/{sp}/page-data.json', f'/home/claude/dl/talents_all/wowtbc/pd_{sp}.json')
if 'wtdates' in sys.argv:
    out = {}
    for f in sorted(glob.glob('/home/claude/dl/talents_all/wt/*.html')):
        s = open(f).read()
        t = H.unescape(re.sub(r'\s+', ' ', re.sub(r'<[^>]+>', ' ', re.sub(r'<(script|style)[^>]*>.*?</\1>', ' ', s, flags=re.S))))
        m = re.search(r'Last updated (\w+ \d{1,2}, 20\d\d)', t)
        out[os.path.basename(f)[:-5]] = {'last_updated': m.group(1) if m else None, 'author_slugs': sorted(set(re.findall(r'author/([a-z0-9-]+)/', s)))[:3]}
    json.dump(out, open('/home/claude/dl/talents_all/wt/page_dates.json', 'w'), indent=1)
