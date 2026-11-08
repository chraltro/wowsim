// Web Worker: runs MythicSim's engine (WebAssembly) for the group page.
// Messages in: {type:'init', module} then {id, type:'char'|'ups', ...}. Out: {id, result} or {id, progress}.
let MOD = null;
function runReq(req){
  const ex = new WebAssembly.Instance(MOD, {}).exports;   // a fresh instance per run: the engine keeps state between runs
  const bytes = new TextEncoder().encode(JSON.stringify(req));
  const p = ex.ws_alloc(bytes.length);
  new Uint8Array(ex.memory.buffer, p, bytes.length).set(bytes);
  let n;
  try { n = ex.ws_sim(p, bytes.length); } catch(e){ return {ok: false, stage: 'engine', reason: 'the engine stopped ('+(e.message||e)+')'}; }
  return JSON.parse(new TextDecoder().decode(new Uint8Array(ex.memory.buffer, ex.ws_out_ptr(), n)));
}
const run = req => MCRequest.summarize(runReq(req));
function roleOf(ctx){ const sp = CLASSDATA[ctx.cls].specs[ctx.spec]; return (sp.roles && sp.roles[0]) || 'damage'; }
function dungeon(ctx){
  const role = roleOf(ctx);
  const req = MCRequest.buildRequest(Object.assign({}, ctx, {targetLevel: Math.min(63, ctx.level + 2), boss: true, duration: 120, iterations: ctx.iterations || 100, role: role === 'healer' ? undefined : role}));
  const s = run(req);
  return Object.assign({role}, s);
}
function metric(ctx, objective, killTime){
  if(objective === 'quest'){ const q = MCQuest.questSim(Object.assign({}, ctx, {fixedDuration: killTime, iterations: 120}), run); return q.ok ? {v: q.perHour, q} : {v: null, why: q.why}; }
  const d = dungeon(Object.assign({}, ctx, {iterations: 120}));
  return d.ok ? {v: d.role === 'healer' ? d.hps : d.dps, d} : {v: null, why: d.why};
}
var ITEMS_ALL = {};
self.onmessage = e => {
  const m = e.data;
  if(m.items) Object.assign(ITEMS_ALL, m.items);
  if(m.type === 'init'){ MOD = m.module; postMessage({id: m.id, result: true}); return; }
  try {
    if(m.type === 'char'){
      const quest = MCQuest.questSim(m.ctx, run);
      const dung = dungeon(m.ctx);
      postMessage({id: m.id, result: {quest, dungeon: dung}});
      return;
    }
    if(m.type === 'ups'){
      const killTime = Math.max(4, Math.min(120, Math.round(m.killTime || 20)));
      const base = metric(m.ctx, m.objective, killTime);
      const out = [];
      m.candidates.forEach((c, k) => {
        const gear = Object.assign({}, m.ctx.gear); gear[c.slot] = c.id; if(c.slot === 'mainhand' && c.two) delete gear.offhand;
        const r = metric(Object.assign({}, m.ctx, {gear}), m.objective, killTime);
        out.push({id: c.id, slot: c.slot, v: r.v, why: r.why});
        if(k % 4 === 3) postMessage({id: m.id, progress: (k+1)/m.candidates.length});
      });
      postMessage({id: m.id, result: {base: base.v, why: base.why, items: out}});
      return;
    }
    throw new Error('unknown job '+m.type);
  } catch(err){ postMessage({id: m.id, error: String(err && err.message || err)}); }
};
