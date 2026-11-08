const {DATA,TREE_ORDER}=require('../src/data.js');
const meta=require('../opt/talents_meta.json');
const M=Object.fromEntries(meta.map(t=>[t.id,t]));
const ROUTES={
 pure:[['tidalfocus',5],['mindful',3],['ihw',2],['watershield',1],['ihw',3],['anchealing',1],['manatide',1],['tidalmastery',5],['natswift',1],['healingway',3],['purification',5],['riptide',1],['thundering',5],['anchealing',2],['restotems',5],['healfocus',3],['ancknow',5]],
 melee:[['tidalfocus',5],['mindful',3],['ihw',2],['watershield',1],['ihw',3],['totemicfocus',1],['manatide',1],['ancknow',5],['mentaldex',3],['thundering',5],['eleweapons',2],['stormstrike',1],['restotems',5],['tidalmastery',4],['healingway',3],['natswift',1],['purification',5],['riptide',1]],
 mq:[['tidalfocus',5],['mindful',3],['ihw',2],['watershield',1],['ihw',3],['totemicfocus',1],['manatide',1],['ancknow',5],['mentaldex',3],['thundering',5],['eleweapons',2],['stormstrike',1],['flurry',5],['mentalquick',2],['restotems',5],['tidalmastery',1],['healingway',3],['purification',3]],
 ele:[['tidalfocus',5],['mindful',3],['ihw',2],['watershield',1],['anchealing',1],['healfocus',3],['manatide',1],['convection',5],['concussion',5],['elefocus',1],['restotems',5],['healingway',3],['natswift',1],['purification',5],['riptide',1],['ancknow',5],['thundering',4]]
};
const code=t=>['ele','enh','res'].map(tr=>TREE_ORDER[tr].map(id=>t[id]||0).join('').replace(/0+$/,'')).join('-');
// legality: tree points before row r must be >= 5*(r-1); prereqs; max ranks
function check(route){
  const t={}, spent={ele:0,enh:0,res:0}; let n=0, errs=[];
  for(const [id,k] of route){ for(let i=0;i<k;i++){ const m=M[id]; if(!m){errs.push('unknown '+id);continue;}
    const before=spent[m.tree]; if(before < 5*(m.r-1)) errs.push('lvl '+(10+n)+' '+id+' row'+m.r+' needs '+5*(m.r-1)+' in '+m.tree+' has '+before);
    if(m.req && (t[m.req]||0) < M[m.req].max) errs.push('lvl '+(10+n)+' '+id+' needs '+m.req+' maxed');
    t[id]=(t[id]||0)+1; if(t[id]>m.max) errs.push(id+' over max'); spent[m.tree]++; n++; } }
  return {t,n,errs,spent};
}
for(const k in ROUTES){ const r=check(ROUTES[k]); console.log(k, r.n, r.spent, code(r.t), r.errs.slice(0,5)); }
console.log(meta.filter(m=>m.req).map(m=>m.id+'<-'+m.req).join(' '));
