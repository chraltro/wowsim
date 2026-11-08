// Run a request file through the wasm build and print headline numbers.
const fs = require('fs');
const path = require('path');
const wasmPath = path.join(__dirname, '../target/wasm32-unknown-unknown/release/wowsim_engine.wasm');
// The engine keeps state between runs that a second run in the same instance trips over,
// so every run gets a fresh instance of the compiled module (instantiating takes a few ms).
let MODULE = null;
async function load(){ if(!MODULE) MODULE = await WebAssembly.compile(fs.readFileSync(wasmPath)); return {fresh: () => new WebAssembly.Instance(MODULE, {}).exports}; }
function sim(eng, reqText){
  const ex = eng.fresh ? eng.fresh() : eng;
  const bytes = Buffer.from(reqText, 'utf8');
  const p = ex.ws_alloc(bytes.length);
  new Uint8Array(ex.memory.buffer, p, bytes.length).set(bytes);
  const n = ex.ws_sim(p, bytes.length);
  ex.ws_free(p, bytes.length);
  const out = Buffer.from(new Uint8Array(ex.memory.buffer, ex.ws_out_ptr(), n)).toString('utf8');
  return JSON.parse(out);
}
if(require.main === module) (async () => {
  const ex = await load();
  for(const f of process.argv.slice(2)){
    const t0 = Date.now(); const r = sim(ex, fs.readFileSync(f, 'utf8')); const ms = Date.now() - t0;
    if(!r.ok){ console.log(path.basename(f), 'FAILED', r.stage, r.code, r.reason); continue; }
    const pl = r.report.result.raidMetrics.parties[0].players[0];
    console.log(path.basename(f), 'dps', pl.dps.avg.toFixed(3), 'pets', (pl.pets||[]).map(x=>x.name+' '+x.dps.avg.toFixed(2)).join(','), 'oom', pl.secondsOomAvg, ms+'ms');
  }
})();
module.exports = {load, sim};
