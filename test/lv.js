const fs=require('fs');
const {DATA,TREE_ORDER}=require('../src/data.js');
const {LEVELS,RANKS}=require('../src/levels.js');
const E=require('../src/engine.js');
DATA.LV=LEVELS; DATA.RK=RANKS;
const zero={str:0,agi:0,sta:0,int:0,spi:0,healing:0,spellDamage:0,natureDamage:0,mp5:0,critRating:0,hitRating:0,ap:0,armor:0};
const route=[['tidalfocus',5],['mindful',3],['ihw',2],['watershield',1],['ihw',3],['totemicfocus',1],['manatide',1],['ancknow',5],['mentaldex',3],['thundering',5],['eleweapons',2],['stormstrike',1],['restotems',5],['tidalmastery',4],['healingway',3],['natswift',1],['purification',5],['riptide',1]];
const mh={w:{min:5,max:10,speed:2.6},wt:'Mace'};
for(const L of [8,10,20,30,40,50,60]){
  const t=E.talentsAt(route, L-9);
  const c=E.character({level:L,gearStats:zero,talents:t,buffs:{},extra:{},mh},DATA);
  const S=E.healSpells(c,DATA,{});
  const d=E.levelDefaults(DATA,L);
  const o={fight:120,tankHP:d.tankHP,dpsHP:d.dpsHP,bossSwing:2,tankAvoid:0.3,spikeChance:0.1,aoeEvery:20,aoeDmg:d.aoe,preCast:1,potions:true};
  const r=E.runScenario(c,DATA,o,20,d.dtps,1);
  const mx=E.maxDTPS(c,DATA,o,12,0.9);
  const cap=E.capacity(c,DATA,{horizon:300,mix:{HW:0.7,CH:0.3},chainEff:0.8,healEff:0.85,hstTargets:3,hitsPerSec:0.1,potions:true});
  const dm=E.damage(c,DATA,{mobDiff:0,front:true,imbue:'windfury',shock:'earth'});
  const cf=E.casterFight(c,DATA,{T:60,mobDiff:0});
  console.log(L, 'hp',c.hp,'mana',Math.round(c.mana),'spells',Object.keys(S).filter(k=>S[k]&&S[k].name||k==='MT'&&S.MT).join('/'),
   'HW',Math.round(S.HW.base),S.HW.mana.toFixed(0),'defaults',JSON.stringify(d),'surv',r.survival.toFixed(2),'hps',r.hps.toFixed(1),'maxDTPS',mx,'cap',Math.round(cap.total),
   'melee',dm.dps.toFixed(1),dm.imbue,'LB',cf.dps.toFixed(1));
}
console.log('--- solo');
for(const L of [4,8,10,14,20,30,40,50,60]){
  const t=E.talentsAt(route, L-9);
  const g=Object.assign({},zero,{armor:L*12, int:Math.round(L*0.6), sta:Math.round(L*0.6), str:Math.round(L*0.4)});
  const mh2={w:{min:Math.round(L*1.2),max:Math.round(L*2.2),speed:3.4},two:true,wt:'Mace'};
  const c=E.character({level:L,gearStats:g,talents:t,buffs:{},extra:{},mh:mh2},DATA);
  const r=E.solo(c,DATA,{mobDiff:0});
  console.log(L,'mob',r.mob.hp,'dps',r.mob.dps,'taken',r.mob.taken.toFixed(1),'LS',r.ls.dps.toFixed(1), r.styles.map(s=>s.key+':'+s.perHour.toFixed(0)+'/h kill'+s.kill.toFixed(1)+' rest'+s.rest.toFixed(1)+' '+(s.imbue||'')+(s.unsafe?' UNSAFE '+s.unsafe:'')).join(' | '));
}
