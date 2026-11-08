// Caster frontier: most Lightning Bolt damage over a 2-minute fight from full mana, for each healing level.
process.env.PRESET = process.argv[2] || 'resto_timesaver';
const L = require('./lib.js');
const {E, TREE_ORDER, H, Dm, ils, split, code, char} = L;
const {DATA} = require('../src/data.js');
const Cd = t => E.casterFight(char(t), DATA, {T:120, mobLevel:60}).dps;
const pure = E.talentsFromCode('-055-5530003315513151', TREE_ORDER);
const Hp = H(pure);
const need = (process.argv[3]||'').split(',').filter(Boolean);
const okNeed = t => need.every(id => (t[id]||0) >= 1);
const res = [];
const mode = process.argv[4] || 'caster';
const dmg = mode === 'caster' ? Cd : (t => Math.max(Cd(t), Dm(t)));
for(const tau of [1.0, 0.99, 0.98, 0.97, 0.95, 0.92, 0.90, 0.85, 0.80, 0.0]){
  const target = tau*Hp;
  const sc = t => okNeed(t) ? dmg(t) - 80*Math.max(0, target - H(t))/1000 : -1e9;
  const r = ils(sc, [pure].filter(okNeed), 20);
  res.push({tau, split:split(r.t), code:code(r.t), Hrel:H(r.t)/Hp, caster:Cd(r.t), melee:Dm(r.t), t:r.t});
}
console.log(JSON.stringify(res));
