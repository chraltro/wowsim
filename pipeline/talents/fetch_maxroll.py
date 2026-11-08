# Fetch the nine Maxroll WoW Forever leveling guides and pull the planner profiles out of window.__remixContext.
# Each profile's talents.history is the guide's point-by-point order as TraitNodeEntry ids (client table, build 70862).
# Output: /home/claude/dl/talents_all/maxroll/<class>.json
import re, json, subprocess, sys, datetime
CLASSES = ['druid', 'hunter', 'mage', 'paladin', 'priest', 'rogue', 'shaman', 'warlock', 'warrior']
OUT = '/home/claude/dl/talents_all/maxroll'

def find_profiles(o, acc):
    if isinstance(o, dict):
        if 'plannerProfile' in o and isinstance(o['plannerProfile'], dict):
            acc.append(o['plannerProfile'])
        for v in o.values():
            find_profiles(v, acc)
    elif isinstance(o, list):
        for v in o:
            find_profiles(v, acc)

for c in (sys.argv[1:] or CLASSES):
    url = f'https://maxroll.gg/wow-forever/class-guides/{c}-leveling-guide'
    html = subprocess.run(['curl', '-sS', '-A', 'Mozilla/5.0', url], capture_output=True, text=True).stdout
    open(f'{OUT}/{c}-leveling-guide.html', 'w').write(html)
    sc = [s for s in re.findall(r'<script[^>]*>(.*?)</script>', html, re.S) if 'window.__remixContext' in s][0]
    d = json.loads(sc[sc.find('=') + 1:].strip().rstrip(';'))
    post = d['state']['loaderData']['branch-posts']['post']
    acc = []
    find_profiles(post, acc)
    profiles = []
    for pp in acc:
        for p in pp['data']['planner']['profiles']:
            profiles.append({'uid': p['uid'], 'name': p['name'], 'history': p['talents']['history'],
                             'position': p['talents'].get('position'), 'planner_id': pp.get('id'),
                             'planner_date': pp.get('date'), 'notes': p.get('notes')})
    meta = {'url': url, 'title': post['title'], 'date': post['date'], 'modified': post['modified'],
            'author': post['author'], 'fetched': datetime.date.today().isoformat()}
    # plain text of the guide body for later checks
    text = re.sub(r'<[^>]+>', ' ', html)
    text = re.sub(r'\s+', ' ', text)
    json.dump({'meta': meta, 'profiles': profiles}, open(f'{OUT}/{c}.json', 'w'), indent=1)
    open(f'{OUT}/{c}.txt', 'w').write(text)
    print(c, meta['title'], meta['date'], meta['modified'], [(p['name'], len(p['history'])) for p in profiles])
