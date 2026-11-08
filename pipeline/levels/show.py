import json,sys
R=json.load(open('/home/claude/work/spells_all.json'))
def show(i):
    r=R.get(str(i))
    if not r: print(i,'MISSING'); return
    keys=['ID','Name','Rank','School','SpellLevel','BaseLevel','MaxLevel','CastTimeMs','DurationMs','CooldownMs','CategoryCooldownMs','GCDMs','Category','ProcChance','ProcCharges','ProcFlags','ICDMs','RPPM','ProcChanceSource','ProcChanceEffect','MaxStack','MaxRange','Speed','RefIDs','_overrides']
    print({k:r[k] for k in keys if k in r})
    for e in r.get('Effects',[]):
        ek=['Index','Type','Aura','BasePoints','PPL','Variance','SPCoef','APCoef','Amplitude','PeriodMs','Misc','Misc2','TriggerID','ChainTargets','ChainAmp','PointsPerResource','RadiusMax','Target']
        print('   ',{k:e[k] for k in ek if k in e})
    if 'Powers' in r: print('    Powers',r['Powers'])
for a in sys.argv[1:]:
    show(int(a))
