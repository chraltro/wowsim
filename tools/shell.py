"""The site's shared shell: every page builder runs its HTML through shell().

Replaces three markers:
  /*__SHEET_CSS__*/    with src/site/sheet.css (tokens, base type, the bars)
  <!--__SHEET_TOP__--> with the title bar and the name box and formula bar for the page
  <!--__SHEET_TABS__--> with the sheet tabs at the bottom, which are the site's navigation
"""
import html, os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# key: (tab label, path from the site root, one sentence for the formula bar)
PAGES = [
    ('start', 'Start', '', 'Tools for five players leveling together in World of Warcraft: Forever. Alliance, RP-PvP, EU.'),
    ('forever', 'Group Sim', 'forever/', "Every character in the group at the same level, from 1 to 60: how fast each one quests and what each one does in a dungeon. Class combat comes from MythicSim's Forever engine."),
    ('shaman', 'Shaman Sim', 'shaman/', 'A Restoration Shaman from level 1 to 60, healing a dungeon pull second by second. It also ranks gear upgrades for your level and reads your combat logs.'),
    ('crafts', 'Craft Profits', 'crafts/', 'What every recipe makes on your auction house after the 5% cut, priced from the latest AHledger scan.'),
]


def shell(page_html, key):
    up = '' if key == 'start' else '../'
    me = next(p for p in PAGES if p[0] == key)
    top = ('<header class="xl-top"><a class="doc" href="%s">wowsim</a><span class="where">WoW: Forever, Alliance RP-PvP EU</span></header>\n'
           '<div class="xl-fx" role="note"><span class="nb">%s</span><span class="fx" aria-hidden="true">fx</span><span class="tx">%s</span></div>'
           % (up or './', html.escape(me[1]), html.escape(me[3])))
    tabs = '<nav class="xl-tabs" aria-label="Pages">%s<span class="gap"></span></nav>' % ''.join(
        '<a href="%s"%s>%s</a>' % (up + (p[2] or './') if up or p[2] else './', ' aria-current="page"' if p[0] == key else '', html.escape(p[1]))
        for p in PAGES)
    css = open(os.path.join(ROOT, 'src', 'site', 'sheet.css'), encoding='utf-8').read()
    for marker, value in (('/*__SHEET_CSS__*/', css), ('<!--__SHEET_TOP__-->', top), ('<!--__SHEET_TABS__-->', tabs)):
        if marker not in page_html:
            raise SystemExit('shell: %s missing from the %s page' % (marker, key))
        page_html = page_html.replace(marker, value)
    return page_html
