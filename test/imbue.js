const E=require('../src/engine.js');const {DATA,TREE_ORDER}=require('../src/data.js');const {ITEMS,SETS,PRESETS}=require('../src/items.js');const {LEVELS,RANKS}=require('../src/levels.js');
const codes={pure:'-055-5530003315513151',melee:'-055030200001-5530100014513151',mq:'-055030200051002-553010001151303',ele:'5500001-045-2530001310513151',enh:'-5505030510050150512'};
for(const pk of ['resto_timesaver','enh_timesaver']){
 const g=E.sumGear(PRESETS[pk].gear,ITEMS,SETS); console.log(pk,'mh',g.mh&&g.mh.n,JSON.stringify(g.mh&&g.mh.w), 'oh', g.oh&&g.oh.n);
 for(const k in codes){ const t=E.talentsFromCode(codes[k],TREE_ORDER);
  for(const withLV of [false,true]){ const D=Object.assign({},DATA); if(withLV){D.LV=LEVELS;D.RK=RANKS;}
   const c=E.character({level:60,gearStats:g.s,mh:g.mh,oh:g.oh,talents:t,buffs:{motw:true,ai:true}},D);
   const r=['windfury','rockbiter','flametongue'].map(im=>{const d=E.damage(c,D,{mobDiff:0,front:true,imbue:im,shock:'none'});return im+' '+d.dps.toFixed(0);}).join(' ');
   const cap=E.capacity(c,D,{horizon:300,mix:{HW:0.7,CH:0.3},chainEff:0.8,healEff:0.85,hstTargets:3,hitsPerSec:0.1,potions:true}).total;
   console.log(' ',k,withLV?'LV':'old',r,'cap',Math.round(cap));}
 }
}
console.log(JSON.stringify(RANKS.wf), JSON.stringify(RANKS.rb.slice(-1)));
