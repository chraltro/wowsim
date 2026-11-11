// Read a ClaudeExport text (addon/ClaudeExport) into one object. No DOM, no dependencies: used by tools/check.js
// and usable in a page.
(function (root) {
'use strict';

const SLOT_KEYS = {
  'Head': 'head', 'Neck': 'neck', 'Shoulder': 'shoulder', 'Back': 'back', 'Chest': 'chest', 'Shirt': 'shirt', 'Tabard': 'tabard',
  'Wrist': 'wrist', 'Hands': 'hands', 'Waist': 'waist', 'Legs': 'legs', 'Feet': 'feet', 'Finger 1': 'finger1', 'Finger 2': 'finger2',
  'Trinket 1': 'trinket1', 'Trinket 2': 'trinket2', 'Main hand': 'mainhand', 'Off hand': 'offhand', 'Ranged/Relic': 'relic',
};
const ATTR = { strength: 'str', agility: 'agi', stamina: 'sta', intellect: 'int', spirit: 'spi' };
const ARMOR_TYPES = ['Cloth', 'Leather', 'Mail', 'Plate', 'Shield'];

function copper(text) {
  let c = 0;
  const m = String(text || '').match(/(\d+)\s*g/); if (m) c += +m[1] * 10000;
  const s = String(text || '').match(/(\d+)\s*s\b/); if (s) c += +s[1] * 100;
  const k = String(text || '').match(/(\d+)\s*c\b/); if (k) c += +k[1];
  return c;
}

// Stats the sims understand, read from an item's tooltip lines.
function tooltipStats(lines) {
  const s = {}; let w = null, two = false, wt = null, at = null;
  const add = (k, v) => { s[k] = (s[k] || 0) + v; };
  for (const raw of lines || []) {
    const l = raw.trim();
    let m;
    if ((m = l.match(/^([+-]\d+) (Strength|Agility|Stamina|Intellect|Spirit)$/))) add(ATTR[m[2].toLowerCase()], +m[1]);
    else if ((m = l.match(/^(\d+) Armor$/))) add('armor', +m[1]);
    else if ((m = l.match(/^(\d+) - (\d+) Damage\s+Speed ([\d.]+)$/))) w = { min: +m[1], max: +m[2], speed: +m[3] };
    else if ((m = l.match(/^(Two-Hand|One-Hand|Main Hand|Off Hand|Ranged)\s+(.+)$/))) { two = m[1] === 'Two-Hand'; wt = m[2].trim(); }
    else if ((m = l.match(/^(Head|Shoulder|Chest|Wrist|Hands|Waist|Legs|Feet|Back|Shield|Off Hand)\s+(Cloth|Leather|Mail|Plate|Shield)$/))) at = m[2];
    else if ((m = l.match(/^Equip: Increases healing done by spells and effects by up to (\d+)/))) add('healing', +m[1]);
    else if ((m = l.match(/^Equip: Increases damage and healing done by magical spells and effects by up to (\d+)/))) { add('healing', +m[1]); add('spellDamage', +m[1]); }
    else if ((m = l.match(/^Equip: Increases damage done by Nature spells and effects by up to (\d+)/))) add('natureDamage', +m[1]);
    else if ((m = l.match(/^Equip: Restores (\d+) mana per 5 sec/))) add('mp5', +m[1]);
    else if ((m = l.match(/^Equip: \+?(\d+) Attack Power/i))) add('ap', +m[1]);
    else if ((m = l.match(/^Equip: Increases your (critical strike|hit) rating by (\d+)/i))) add(m[1].toLowerCase() === 'hit' ? 'hitRating' : 'critRating', +m[2]);
  }
  return { s, w, two, wt, at };
}

// "Name x14 (id 2318, ilvl 10, req 5, Uncommon, Leather, Chest, vendor 15c ea, soulbound, durability 38/45)"
function itemFromLine(text) {
  const m = text.match(/^(.*?)(?: x(\d+))? \((id \d+.*)\)$/);
  if (!m) return null;
  const meta = m[3].split(', ');
  const it = { name: m[1], count: m[2] ? +m[2] : 1, id: null, ilvl: null, req: 1, quality: null, vendor: 0, soulbound: false, tags: [], lines: [] };
  for (const t of meta) {
    let x;
    if ((x = t.match(/^id (\d+)$/))) it.id = +x[1];
    else if ((x = t.match(/^ilvl (\d+)$/))) it.ilvl = +x[1];
    else if ((x = t.match(/^req (\d+)$/))) it.req = +x[1];
    else if ((x = t.match(/^vendor (.+) ea$/))) it.vendor = copper(x[1]);
    else if (t === 'soulbound') it.soulbound = true;
    else if (/^durability /.test(t) || /^enchant /.test(t)) { /* not needed */ }
    else if (/^(Poor|Common|Uncommon|Rare|Epic|Legendary)$/.test(t)) it.quality = t;
    else it.tags.push(t);
  }
  return it;
}

function parseExport(text) {
  const out = {
    exported: null, addon: null, name: null, realm: null, level: null, race: null, cls: null, faction: null,
    gold: 0, zone: null, subzone: null, xp: null, gear: {}, bags: [], bank: [], bankSnapshot: null,
    quests: [], completed: null, talents: {}, talentPoints: {}, skills: {}, recipes: {}, ah: null, warnings: [],
  };
  const lines = String(text || '').replace(/\r/g, '').split('\n');
  let m = lines.slice(0, 3).join(' ').match(/Exported (\d{4}-\d\d-\d\d \d\d:\d\d)/);
  if (m) out.exported = m[1];
  m = lines.slice(0, 3).join(' ').match(/Addon version ([\d.]*\d)/);
  if (m) out.addon = m[1];

  // cut into "## " sections
  const sections = [];
  let cur = null;
  for (const l of lines) {
    if (l.startsWith('## ')) { cur = { title: l.slice(3).trim(), lines: [] }; sections.push(cur); }
    else if (cur) cur.lines.push(l);
    if (/^\(section failed: /.test(l)) out.warnings.push('The addon reported: ' + l);
  }
  const find = (re) => sections.find((s) => re.test(s.title));

  // An item list: "- item" lines, each followed by tooltip lines indented four spaces.
  const itemList = (ls) => {
    const items = [];
    for (const l of ls) {
      if (l.startsWith('- ')) { const it = itemFromLine(l.slice(2)); if (it) items.push(it); }
      else if (l.startsWith('    ') && items.length) items[items.length - 1].lines.push(l.trim());
    }
    return items;
  };

  let s = find(/^Character$/);
  if (s) {
    const c = s.lines.join('\n');
    if ((m = c.match(/^(.+?)-(.+?), level (\d+) (\S+(?: \S+)?) (\S+), (\S+)$/m))) {
      out.name = m[1]; out.realm = m[2]; out.level = +m[3]; out.race = m[4]; out.cls = m[5].toLowerCase(); out.faction = m[6];
      // "Night Elf Hunter" keeps both words of the race; "Dwarf Death Knight" is not a thing in Forever
    }
    if ((m = c.match(/^Gold: (.+)$/m))) out.gold = copper(m[1]);
    if ((m = c.match(/^Location: (.+?)(?: \/ (.+?))?(?: \(([\d.]+), ([\d.]+)\))?$/m))) { out.zone = m[1]; out.subzone = m[2] || null; if (m[3]) out.pos = [+m[3], +m[4]]; }
    if ((m = c.match(/^XP: (\d+) \/ (\d+)/m))) out.xp = [+m[1], +m[2]];
    if ((m = c.match(/^Unspent talent points: (\d+)/m))) out.unspent = +m[1];
  }

  s = find(/^Equipped gear$/);
  if (s) {
    let last = null;
    for (const l of s.lines) {
      const g = l.match(/^\[(.+?)\] (.+)$/);
      if (g) {
        const key = SLOT_KEYS[g[1]];
        last = g[2] === '(empty)' ? null : itemFromLine(g[2]);
        if (key && last) out.gear[key] = last;
      } else if (l.startsWith('    ') && last) last.lines.push(l.trim());
    }
  }

  s = find(/^Bags /);
  if (s) out.bags = itemList(s.lines.filter((l) => !/^Bag \d+:/.test(l)));
  s = find(/^Bank/);
  if (s) {
    out.bank = itemList(s.lines);
    if ((m = s.title.match(/snapshot (.+?)\)/))) out.bankSnapshot = m[1];
    else if (s.lines.some((l) => /not cached yet/.test(l))) out.warnings.push('The bank has never been opened with the addon loaded, so bank items are unknown.');
  }

  s = find(/^Quest log$/);
  if (s) {
    let zone = null, q = null, inChoices = false, choice = null;
    for (const l of s.lines) {
      let g;
      if (l.startsWith('### ')) {
        zone = l.slice(4).replace(/ \(COLLAPSED.*$/, '');
        if (/COLLAPSED/.test(l)) out.warnings.push('Quest log header "' + zone + '" was collapsed in game, so its quests are missing from the export.');
      } else if ((g = l.match(/^- (.+) \(((?:lvl|id|group|COMPLETE)[^()]*)\)$/))) {
        q = { title: g[1], zone, level: null, id: null, complete: false, objectives: [], choices: [], rewards: [] };
        for (const t of g[2].split(', ')) {
          let x;
          if ((x = t.match(/^lvl (\d+)$/))) q.level = +x[1];
          else if ((x = t.match(/^id (\d+)$/))) q.id = +x[1];
          else if (t === 'COMPLETE') q.complete = true;
          else if ((x = t.match(/^group (\d+)$/))) q.group = +x[1];
        }
        out.quests.push(q); inChoices = false; choice = null;
      } else if (q && /^    Choose one of:/.test(l)) { inChoices = true; }
      else if (q && inChoices && l.startsWith('    - ')) { choice = itemFromLine(l.slice(6)); if (choice) q.choices.push(choice); }
      else if (q && inChoices && l.startsWith('        ') && choice) choice.lines.push(l.trim());
      else if (q && (g = l.match(/^    \[(x| )\] (.*)$/))) q.objectives.push({ done: g[1] === 'x', text: g[2] });
      else if (q && (g = l.match(/^    Goal: (.*)$/))) q.goal = g[1];
      else if (q && (g = l.match(/^    Rewards: (.*)$/))) {
        const x = g[1].match(/(\d+) xp/); if (x) q.xp = +x[1];
        g[1].split(', ').forEach((r) => { const y = r.match(/^reward: (.+)$/); if (y) q.rewards.push(y[1]); });
      }
    }
  }

  s = find(/^Completed quests/);
  if (s) {
    out.completed = new Set();
    for (const l of s.lines) for (const t of l.split(',')) { const n = parseInt(t, 10); if (n) out.completed.add(n); }
  }

  s = find(/^Talents$/);
  if (s) {
    let tree = null;
    for (const l of s.lines) {
      let g;
      if ((g = l.match(/^### (.+?) \((\d+) points?\)$/))) { tree = g[1]; out.talentPoints[tree] = +g[2]; }
      else if ((g = l.match(/^- (.+?) (\d+)\/(\d+)/))) out.talents[g[1]] = { rank: +g[2], max: +g[3], tree };
    }
  }

  s = find(/^Skills and professions$/);
  if (s) for (const l of s.lines) { const g = l.match(/^- (.+?) (\d+)\/(\d+)/); if (g) out.skills[g[1]] = { rank: +g[2], max: +g[3] }; }

  s = find(/^Known recipes$/);
  if (s) {
    let prof = null;
    for (const l of s.lines) {
      const g = l.match(/^### (.+?) \((\d+) recipes?, snapshot (.+)\)$/);
      if (g) { prof = g[1]; out.recipes[prof] = { snapshot: g[3], names: new Map() }; }
      else if (prof && l.trim()) for (const t of l.split(', ')) { const x = t.match(/^(.*?)(?: \[(orange|yellow|green|grey)\])?$/); if (x && x[1]) out.recipes[prof].names.set(x[1], x[2] || null); }
    }
  }

  s = find(/^Auction house scan/);
  if (s) {
    const ah = { time: null, prices: new Map(), gearOnly: false };
    if ((m = s.title.match(/\((\d{4}-\d\d-\d\d \d\d:\d\d)/))) ah.time = m[1];
    let mode = null;
    for (const l of s.lines) {
      if (/^### Gear listed/.test(l)) mode = 'gear';
      else if (/^### All prices/.test(l)) mode = 'all';
      else if (/every other price is left out/.test(l)) ah.gearOnly = true;
      else if (mode === 'gear' && l.startsWith('- ')) {
        const g = l.match(/\(id (\d+)[^)]*\): (.+?), (\d+) listed$/);
        if (g) ah.prices.set(+g[1], { min: copper(g[2]), qty: +g[3] });
      } else if (mode === 'all') {
        for (const t of l.trim().split(/\s+/)) { const g = t.match(/^(\d+):(\d+):(\d+)$/); if (g) ah.prices.set(+g[1], { min: +g[2], qty: +g[3] }); }
      }
    }
    if (ah.prices.size) out.ah = ah;
  }

  if (!out.level) out.warnings.push('No "## Character" line found: this does not look like a ClaudeExport text.');
  return out;
}

const api = { parseExport, tooltipStats, itemFromLine, copper, SLOT_KEYS, ARMOR_TYPES };
if (typeof module !== 'undefined' && module.exports) module.exports = api; else root.CheckParse = api;
})(typeof self !== 'undefined' ? self : this);
