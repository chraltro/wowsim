const E=require('../src/engine.js');const {DATA,TREE_ORDER}=require('../src/data.js');const {ITEMS,SETS,PRESETS}=require('../src/items.js');
const preset=process.argv[2]||'resto_timesaver';
const g=E.sumGear(PRESETS[preset].gear,ITEMS,SETS);
const builds=JSON.parse(process.argv[3]);
const so={fight:120,tankHP:6500,dpsHP:3800,bossSwing:2.0,tankAvoid:0.3,spikeChance:0.1,aoeEvery:15,aoeDmg:500,meHitsPerSec:0.05,preCast:0.7,potions:true,tablet:false};
for(const [name,code] of Object.entries(builds)){
  const t=E.talentsFromCode(code,TREE_ORDER);
  const c=E.character({gearStats:g.s,mh:g.mh,oh:g.oh,talents:t,buffs:{motw:true,ai:true}},DATA);
  const m=E.maxDTPS(c,DATA,so,60,0.9);
  const long=Object.assign({},so,{fight:240});
  const m2=E.maxDTPS(c,DATA,long,40,0.9);
  const at=E.runScenario(c,DATA,so,100,325,7);
  console.log(name.padEnd(12), code.padEnd(36), 'maxDTPS 2min',m,' 4min',m2,' survival@325',(at.survival*100).toFixed(0)+'%', 'manaEnd',at.manaEnd.toFixed(0));
}
