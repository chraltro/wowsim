// Pareto frontier: most melee DPS for each healing level, measured against the pure build.
process.env.PRESET = process.argv[2] || 'resto_timesaver';
const {H, Dm, legal, code, split, ils, TREE_ORDER} = require('./lib.js');
const E2 = require('../src/engine.js');
const pure = E2.talentsFromCode('-055-5530003315513151', TREE_ORDER);
const hyb = E2.talentsFromCode('-055030310021-5530000115513101', TREE_ORDER);
const Hp = H(pure);
const need = (process.argv[3]||'').split(',').filter(Boolean);
const okNeed = t => need.every(id => (t[id]||0) >= 1);
const res = [];
for(const tau of [1.02, 1.0, 0.99, 0.98, 0.97, 0.95, 0.93, 0.90, 0.85]){
  const target = tau*Hp;
  const sc = t => okNeed(t) ? Dm(t) - 80*Math.max(0, target - H(t))/1000 : -1e9;
  const starts = [pure, hyb].filter(t => okNeed(t));
  const r = ils(sc, starts, 20);
  res.push({tau, split:split(r.t), code:code(r.t), H:H(r.t), Hrel:H(r.t)/Hp, D:Dm(r.t), t:r.t});
}
console.log(JSON.stringify(res));
