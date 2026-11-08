# Fetch timesaver.gg WoW Forever talent calculator pages and pull the embedded trees + presets out of the RSC payload.
# Output: /home/claude/dl/talents_all/ts/<class>.json  {"trees":[...], "presets":[...], "fetched":..., "url":...}
import re, json, subprocess, sys, datetime
CLASSES = ['druid','hunter','mage','paladin','priest','rogue','shaman','warlock','warrior']
OUT = '/home/claude/dl/talents_all/ts'
def extract(full, start):
    depth=0; j=start; instr=False; esc=False
    while True:
        ch=full[j]
        if instr:
            if esc: esc=False
            elif ch=='\\': esc=True
            elif ch=='"': instr=False
        else:
            if ch=='"': instr=True
            elif ch in '{[': depth+=1
            elif ch in '}]':
                depth-=1
                if depth==0: break
        j+=1
    return full[start:j+1]
for c in (sys.argv[1:] or CLASSES):
    url = f'https://timesaver.gg/tools/wow-forever/talent-calculator/{c}'
    html = subprocess.run(['curl','-sS','-A','Mozilla/5.0',url],capture_output=True,text=True).stdout
    open(f'{OUT}/calc_{c}.html','w').write(html)
    chunks = re.findall(r'self\.__next_f\.push\(\[1,"((?:[^"\\]|\\.)*)"\]\)', html)
    full = ''.join(json.loads('"'+x+'"') for x in chunks)
    i = full.find('"cls":{')
    cls = json.loads(extract(full, i+len('"cls":')))
    j = full.find('"presets":', i)
    presets = json.loads(extract(full, j+len('"presets":'))) if j>0 else []
    json.dump({'url':url,'fetched':datetime.date.today().isoformat(),'cls':cls,'presets':presets}, open(f'{OUT}/{c}.json','w'), indent=1)
    print(c, [ (t['name'],len(t['talents'])) for t in cls['trees']], 'presets', len(presets))
