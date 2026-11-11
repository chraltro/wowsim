#!/usr/bin/env node
/* What to do next, from a ClaudeExport text.

     node tools/check.js                 newest export in your pastes folder
     node tools/check.js path/to/export.txt
     node tools/check.js --mode heal     score gear for healing only (or: quest)
     node tools/check.js --offline       no network: use the last prices fetched, or the scan built into the site
     node tools/check.js --json          the full result as JSON instead of text

   It reads the same data and runs the same code as the site: the Shaman Sim engine scores gear, Craft Profits prices
   recipes. Prices come from the auction scan in the export when there is one (/claudeah in game), otherwise from
   AHledger's latest scan of your house. Quest data is built once by tools/fetch_quests.py.

   The report is printed and also saved under local/reports/. Nothing under local/ is ever committed. */
'use strict';
const fs = require('fs');
const path = require('path');
const ROOT = path.resolve(__dirname, '..');
const LOCAL = path.join(ROOT, 'local');
const args = process.argv.slice(2);
const flag = (n) => args.includes('--' + n);
const opt = (n, d) => { const i = args.indexOf('--' + n); return i >= 0 && args[i + 1] ? args[i + 1] : d; };
const fileArg = args.find((a, i) => !a.startsWith('--') && !(i > 0 && ['--mode', '--house'].includes(args[i - 1])));

function readConfig() {
  const cfg = { house: 'forever.rppvp.alliance.eu', pastes: null };
  try { Object.assign(cfg, JSON.parse(fs.readFileSync(path.join(LOCAL, 'config.json'), 'utf8'))); } catch (e) { /* no config is fine */ }
  return cfg;
}

// Where exports may be: an explicit folder, then local/pastes in the repo, then the older spots next to or inside it.
function findExport(cfg) {
  if (fileArg) return path.resolve(fileArg);
  const dirs = [process.env.WOWSIM_PASTES, cfg.pastes, path.join(LOCAL, 'pastes'), path.join(ROOT, 'pastes'), path.join(ROOT, '..', 'pastes')].filter(Boolean);
  let best = null;
  for (const d of dirs) {
    let names; try { names = fs.readdirSync(d); } catch (e) { continue; }
    for (const n of names) {
      if (!/\.txt$/i.test(n)) continue;
      const f = path.join(d, n), m = fs.statSync(f).mtimeMs;
      if (!best || m > best.m || (m === best.m && n !== 'latest.txt')) best = { f, m };
    }
  }
  if (!best) { console.error('No export found. Looked in:\n  ' + dirs.join('\n  ') + '\nIn game: /claudeexport with tools/export_watch.py running, or pass a file.'); process.exit(2); }
  return best.f;
}

async function loadPrices(cfg, core, D) {
  const cache = path.join(LOCAL, 'cache', 'prices_' + cfg.house + '.txt');
  const fresh = (() => { try { return Date.now() - fs.statSync(cache).mtimeMs < 45 * 60 * 1000; } catch (e) { return false; } })();
  if (!flag('offline') && !fresh) {
    try {
      const ctl = new AbortController(); const t = setTimeout(() => ctl.abort(), 20000);
      const res = await fetch('https://api.ahledger.com/v1/pricetable/' + cfg.house, { signal: ctl.signal, headers: { 'User-Agent': 'wowsim-check (personal tool; prices from AHledger)' } });
      clearTimeout(t);
      if (!res.ok) throw new Error('HTTP ' + res.status);
      const text = await res.text();
      core.parsePriceTable(text);                       // throws if it is not a price table
      fs.mkdirSync(path.dirname(cache), { recursive: true });
      fs.writeFileSync(cache, text);
    } catch (e) { console.error('AHledger not reached (' + e.message + '); using ' + (fs.existsSync(cache) ? 'the last prices fetched' : 'the scan built into the site') + '.'); }
  }
  try { return core.parsePriceTable(fs.readFileSync(cache, 'utf8')); } catch (e) { /* fall through */ }
  try { return core.parsePriceTable(D.snap); } catch (e) { return null; }
}

async function main() {
  const cfg = readConfig();
  if (opt('house')) cfg.house = opt('house');
  const file = findExport(cfg);
  const Parse = require('../src/check/parse.js');
  const Advise = require('../src/check/advise.js');
  const { DATA } = require('../src/data.js');
  const { LEVELS, RANKS } = require('../src/levels.js');
  DATA.LV = LEVELS; DATA.RK = RANKS;
  const { ITEMS, SETS } = require('../src/items.js');
  const core = require('../src/crafts/core.js');
  const D = require('../data/crafts.json');
  let quests = null;
  try { quests = JSON.parse(fs.readFileSync(path.join(LOCAL, 'cache', 'quests.json'), 'utf8')); } catch (e) { /* the report says how to get it */ }
  const ch = Parse.parseExport(fs.readFileSync(file, 'utf8'));
  if (!ch.level) { console.error(file + ' is not a ClaudeExport text.'); process.exit(2); }
  const ageH = (Date.now() - fs.statSync(file).mtimeMs) / 3600000;
  if (ageH > 24) ch.warnings.push('This export is ' + Math.round(ageH / 24) + ' day(s) old. Run /claudeexport again for current gear, bags and quests.');
  const prices = await loadPrices(cfg, core, D);
  const advisor = Advise.makeAdvisor({ Engine: require('../src/engine.js'), DATA, ITEMS, SETS, TALENT_META: require('../opt/talents_meta.json'), Parse,
    MCGear: require('../src/mc/gear.js'), crafts: { core, D }, quests, prices });
  const R = advisor.report(ch, { mode: opt('mode', 'both') });
  R.file = file;
  const text = Advise.render(R);
  if (flag('json')) console.log(JSON.stringify(R, (k, v) => (v instanceof Map ? [...v] : v instanceof Set ? [...v] : v), 1));
  else console.log(text);
  if (!flag('no-save')) {
    const dir = path.join(LOCAL, 'reports');
    fs.mkdirSync(dir, { recursive: true });
    const stamp = (ch.exported || new Date().toISOString().slice(0, 16)).replace(/[^\d]+/g, '-');
    fs.writeFileSync(path.join(dir, (ch.name || 'character') + '_' + stamp + '.md'), text);
    fs.writeFileSync(path.join(dir, 'latest.md'), text);
  }
}
main().catch((e) => { console.error(e.stack || String(e)); process.exit(1); });
