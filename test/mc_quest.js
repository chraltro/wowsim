// Questing kills per hour for every class and spec at a few levels, typical gear.
const path = require('path');
const R = p => require(path.join(__dirname, '..', p));
Object.assign(global, R('src/mc/classdata.js'), R('src/mc/items.js'), R('src/levels.js'), R('src/data.js'));
global.MCRequest = R('src/mc/request.js');
const G = R('src/mc/gear.js'), Q = R('src/mc/quest.js');
const {load, sim} = R('engine-wasm/test/run.js');
(async () => {
  const eng = await load();
  const run = req => { try { return MCRequest.summarize(sim(eng, JSON.stringify(req))); } catch(e){ return {ok: false, why: String(e.message||e)}; } };
  const only = process.argv[2] && process.argv[2] !== 'all' ? [process.argv[2]] : Object.keys(CLASSDATA);
  const levels = (process.argv[3] || '10,20,40,60').split(',').map(Number);
  for(const cls of only){
    const cd = CLASSDATA[cls], race = Object.keys(cd.races)[0];
    for(const spec of Object.keys(cd.specs)){
      const out = levels.map(L => {
        const gear = G.typicalGear(ITEMS_ALL, cls, spec, L, {inEngine: id => !ITEMS_ALL[id].ne});
        const q = Q.questSim({cls, race, spec, level: L, gear, iterations: 100}, run);
        if(!q.ok) return L+': FAIL '+q.why.slice(0, 80);
        return L+': '+q.perHour.toFixed(0)+'/h kill '+q.kill.toFixed(1)+'s rest '+q.rest.toFixed(1)+'s('+q.restFor[0]+')'+(q.risky ? ' RISKY' : '');
      });
      console.log(cls.padEnd(8), spec.padEnd(14), out.join(' | '));
    }
  }
})();
