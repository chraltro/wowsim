// Synthetic Forever-style log for parser testing (Advanced Combat Logging on, classic layout).
const L=[]; let t=0;
const ts=s=>{const tt=72000+s; const h=Math.floor(tt/3600), m=Math.floor(tt%3600/60), sec=(tt%60).toFixed(3); return `11/8/2026 ${h}:${String(m).padStart(2,'0')}:${sec.padStart(6,'0')}-1  `;};
const me='Player-4701-0A1B2C3D', tank='Player-4701-0B000001', boss='Creature-0-4701-1-1-12345-000ABC';
let mana=4000;
const adv=(unit,hp,mhp,pw,mpw)=>`${unit},0000000000000000,${hp},${mhp},120,600,1800,0,${pw},${mpw},0,-1234.50,567.25,1426,1.5708,60`;
L.push(ts(0)+'COMBAT_LOG_VERSION,20,ADVANCED_LOG_ENABLED,1,BUILD_VERSION,1.60.1,PROJECT_ID,99');
L.push(ts(0)+`ENCOUNTER_START,3001,"Thane Bjorgar",1,5,9001`);
for(let s=0;s<60;s+=2){
  L.push(ts(s)+`SWING_DAMAGE,${boss},"Thane Bjorgar",0xa48,0x0,${tank},"Niels-Forever",0x512,0x0,${adv(boss,50000,60000,0,0)},900,0,1,0,0,0,nil,nil,nil`);
}
for(let s=1;s<60;s+=2.6){
  mana-=180;
  L.push(ts(s)+`SPELL_CAST_SUCCESS,${me},"Thordun-Forever",0x511,0x0,${tank},"Niels-Forever",0x512,0x0,10396,"Healing Wave",0x8,${adv(me,3000,3000,mana,4000)}`);
  L.push(ts(s+0.01)+`SPELL_HEAL,${me},"Thordun-Forever",0x511,0x0,${tank},"Niels-Forever",0x512,0x0,10396,"Healing Wave",0x8,${adv(tank,4000,5500,0,100)},1200,300,0,${s%5<1?1:'nil'}`);
}
L.push(ts(10)+`SPELL_CAST_SUCCESS,${me},"Thordun-Forever",0x511,0x0,0000000000000000,nil,0x80000000,0x80000000,16190,"Mana Tide Totem",0x8,${adv(me,3000,3000,2500,4000)}`);
L.push(ts(12)+`SPELL_ENERGIZE,${me},"Thordun-Forever",0x511,0x0,${me},"Thordun-Forever",0x511,0x0,52128,"Water Shield",0x8,${adv(me,3000,3000,2600,4000)},80,0,0,4000`);
L.push(ts(30)+`SPELL_DAMAGE,${boss},"Thane Bjorgar",0xa48,0x0,${me},"Thordun-Forever",0x511,0x0,99,"Cleave",0x1,${adv(me,2000,3000,2000,4000)},700,0,1,0,0,0,nil,nil,nil`);
L.push(ts(61)+`UNIT_DIED,0000000000000000,nil,0x80000000,0x80000000,${boss},"Thane Bjorgar",0xa48,0x0,0`);
L.push(ts(61)+`ENCOUNTER_END,3001,"Thane Bjorgar",1,5,1,61000`);
require('fs').writeFileSync(__dirname+'/sample.txt',L.join('\n'));
