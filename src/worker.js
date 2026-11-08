self.WorkerJob = function(msg){
  if(msg.type === 'sim'){
    const best = (c, o) => { let b = null; ['rockbiter','flametongue','windfury'].forEach(im => { const d = Engine.damage(c, DATA, Object.assign({}, o, {imbue:im})); if(d.imbue === im && (!b || d.dps > b.dps)) b = d; }); return b; };
    return msg.jobs.map(j => {
      const c = j.c;
      const at = Engine.runScenario(c, DATA, j.s, 40, j.dtps, 1);
      const maxDTPS = Engine.maxDTPS(c, DATA, j.s, 20, 0.9);
      const cap = Engine.capacity(c, DATA, j.cap);
      const dSust = best(c, {mobDiff:j.mobDiff, front:true, shock:'none'});
      const dShock = best(c, {mobDiff:j.mobDiff, front:true, shock:'earth'});
      const bolt = Engine.boltDPS(c, DATA, {mobDiff:j.mobDiff});
      return {build:j.build, at, maxDTPS, cap:{total:cap.total, hps:cap.hps}, dmg:{sustained:dSust.dps, imbue:dSust.imbue, withShock:dShock.dps, manaWithShock:dShock.manaPerSec}, bolt};
    });
  }
  if(msg.type === 'log'){
    const report = LogParse.analyze(msg.text, {name:msg.name, gap:msg.gap});
    if(report.error) return {error:report.error};
    const obs = LogParse.observations(report);
    return {report, obs, text: LogParse.summaryText(report, obs)};
  }
  throw new Error('Unknown job');
};
if(typeof window === 'undefined'){
  self.onmessage = e => {
    try{ postMessage({id:e.data.id, result:self.WorkerJob(e.data)}); }
    catch(err){ postMessage({id:e.data.id, error:String(err && err.message || err)}); }
  };
}
