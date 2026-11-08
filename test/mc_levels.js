// Sim every class and spec at several levels with typical gear through the wasm engine.
// Checks: no refusals, no errors, damage rises with level. Usage: node test/mc_levels.js [class] [levels]
const path = require('path');
const R = p => require(path.join(__dirname, '..', p));
Object.assign(global, R('src/mc/classdata.js'), R('src/mc/items.js'), R('src/levels.js'));
const MC = R('src/mc/request.js'), G = R('src/mc/gear.js');
const {load, sim} = R('engine-wasm/test/run.js');
const engineIds = new Set();
for(const line of require('fs').readFileSync(path.join(__dirname, '../vendor/mythicsim-forever-engine/data/items.jsonl'), 'utf8').split('\n')) if(line.trim()) engineIds.add(String(JSON.parse(line).id));
(async () => {
  let ex = await load();
  const only = process.argv[2] && process.argv[2] !== 'all' ? [process.argv[2]] : Object.keys(CLASSDATA);
  const levels = (process.argv[3] || '10,20,30,40,50,60').split(',').map(Number);
  let fails = 0;
  for(const cls of only){
    const cd = CLASSDATA[cls]; const race = Object.keys(cd.races)[0];
    for(const spec of Object.keys(cd.specs)){
      const row = [];
      let prev = 0;
      for(const L of levels){
        const gear = G.typicalGear(ITEMS_ALL, cls, spec, L, {inEngine: id => engineIds.has(String(id))});
        const req = MC.buildRequest({cls, race, spec, level: L, gear, duration: 60, iterations: 100});
        const t0 = Date.now();
        let res; try { res = sim(ex, JSON.stringify(req)); } catch(e){ res = {ok: false, stage: 'trap', reason: String(e.message||e)}; ex = await load(); }
        if(!res.ok || process.env.DUMP) require('fs').writeFileSync('/tmp/mc_'+cls+'_'+spec+'_'+L+'.json', JSON.stringify(req));
        const s = MC.summarize(res);
        if(!s.ok){ fails++; row.push(L+': FAIL '+s.why.slice(0, 160)); continue; }
        const v = s.total + s.hps;
        row.push(L+': '+v.toFixed(0)+(s.petDps ? ' (pet '+s.petDps.toFixed(0)+')' : '')+(s.hps ? ' hps' : '')+' '+(Date.now()-t0)+'ms'+(v < prev*0.98 ? ' DROP' : ''));
        prev = v;
      }
      console.log(cls.padEnd(8), spec.padEnd(14), row.join(' | '));
    }
  }
  console.log('failures', fails);
})();
