# Talent data for all nine classes (WoW Forever, client build 1.60.1.70862)

Built 2026-11-08 by the scripts in `pipeline/talents/`. Nothing here comes from Classic talent data: the trees, ranks and values are read from the Forever client tables and checked against four other Forever sources.

## Files

- `data/talents/<class>.json`: the three trees in calculator order, every talent with its position, ranks, prerequisite, per-rank text, client effect values and the checks run on it.
- `data/routes/<class>.json`: for each spec, leveling routes from level 10 (point by point where the guide publishes the order) and level 60 builds per dungeon role (tank, healer, damage), each with its source.

### Talent file fields

- `codeOrder`: per tree, the talent ids in the order a timesaver.gg / wowsims build code lists them (row by row, left to right). A code is one digit per talent in that order, trees joined with `-`, trailing zeros and dashes dropped.
- Per talent: `id`, `name`, `tree`, `row` and `col` (1-based, as in `opt/talents_meta.json`), `maxRank`, `prereq` (id) and `prereq_rank`, `tier_points_required`, `spell_id`, `rank_spell_ids`, `trait` (client definition, node and node entry ids), `wowsims_field`, `ranks` (text per rank), `effects`, `forever_vs_classic`.
- `rank_spell_ids`: Forever talents are trait nodes, so every rank reports the same spell id. The rank only changes the effect values, which come from the trait curve (`TraitDefinitionEffectPoints` to `CurvePoint`). Where the old Classic `Talent` table in the same client has a talent of the same name, its rank spells are kept as `legacy_classic_rank_spell_ids`. The Forever trees do not use them.
- `effects`: one entry per client spell effect. Each entry has `per_rank` values and their source: the trait curve, base points that stay the same at every rank, or level-scaled base points at level 60.
  - Spell modifiers have `spell_mod` (the SpellModOp name from wowsims `sim/core/dbcenums/spellmods.go`), `mod_kind` (pct or flat) and `affects`.
  - `affects` lists the class's learnable spells whose class mask overlaps the effect's mask. Treat it as a guide, not a proof.
  - Flat cast-time and cooldown values are in milliseconds (Improved Frostbolt: -100 per rank, which is 0.1 s).
  - Where the aura type states a stat directly, a plain `stat` key is added, for example `crit_pct`, `spell_hit_pct`, `int_pct` or `damage_done_pct` with `school`.
- `ranks[].text`: resolved from the client description (`Spell.Description_lang`) at each rank. Level-scaled ability values are shown at level 60. If a token could not be resolved, the text comes from wowforevertalents.com instead, and `text_source` and `client_unresolved_tokens` say so. `numbers_match` compares the numbers in the text with timesaver.gg and wowforevertalents.com. Where either one differs, `other_texts` holds all three versions.
- `forever_vs_classic`: wowforevertalents.com's own label (new, changed or unchanged). It was not checked here.

## Sources

| Source | What was used | Fetched |
| --- | --- | --- |
| Forever client DB2, build 1.60.1.70862, via wago.tools CSV export (`ext/wago_talents/`) | Trait tables (tree, nodes, entries, definitions, curves, edges, tier conditions), Spell, SpellEffect, SpellName, SkillLineAbility, SpellClassOptions and the other spell tables | 2026-11-08 |
| wowsims/forever commit 125e534 (2026-11-08) | `ui/sim/talents/trees/<class>.json`, `proto/<class>.proto`, `assets/db_inputs/spell_store_inputs.json` (its spell store: class data from build 70790 with hotfix push 113715), preset talent strings | local clone |
| timesaver.gg calculator, `https://timesaver.gg/tools/wow-forever/talent-calculator/<class>` | Trees, rank texts and its presets (with order lists for some) | 2026-11-08 |
| Warcraft DB Forever, `https://forever.warcraftdb.com/api/v1/talents/<class>` | Trees, and the decoder for Warcraft Tavern build links | 2026-11-08 |
| wowforevertalents.com | Trees, rank texts, its new/changed/unchanged labels (its bundle says client 70862 plus the DBCache hotfixes of 2026-11-07) | 2026-11-08 |
| Maxroll leveling guides, `https://maxroll.gg/wow-forever/class-guides/<class>-leveling-guide` (published Oct 29-30, updated Nov 4 2026, author "maxroll") | Planner profiles, whose `talents.history` gives the point order as client node entry ids | 2026-11-08 |
| Method.gg leveling guides (updated Nov 4-8 2026) and 22 spec "talents" pages (updated Nov 4-7 2026) | `data-talent` embeds: the final build as a bit string, plus the point order, over client node ids | 2026-11-08 |
| Warcraft Tavern Forever spec and leveling guides | Warcraft DB calculator links (`#?t=`), one character per point, in order | 2026-11-08 |
| wowtbc.gg "Warcraft Forever" class guides (28 spec pages, no author or date shown) | Gatsby `page-data.json`: level 60 builds and a "Leveling 1-60" point order | 2026-11-08 |

Wowhead, Icy Veins and Mobalytics return Cloudflare challenges to this sandbox (HTTP 403 or an empty 202), and WebFetch failed on Icy Veins too. Their builds appear only as timesaver.gg transcriptions. Those entries are marked `secondary: true` and are unverified against the original pages. wow.gg loads its builds in the browser, so they were not read.

## Verification

Trees:

- `pipeline/talents/client_trees.py` rebuilds the nine trees from the client Trait tables. It is an independent Python version of the placement rules documented in wowsims `tools/database/tables.go`.
- The rebuild matches the wowsims tree JSON on all 467 talents: name, row, column, max rank, spell id, definition id and prerequisite.
- It also matches timesaver.gg (names, positions, ranks and prerequisite indexes) and Warcraft DB for all nine classes.
- wowforevertalents.com matches except Hunter Marksmanship, where it adds Improved Serpent Sting (5 ranks, row 4 col 4). The client parks that node off the tree canvas, and wowsims, timesaver.gg and Warcraft DB all leave it out. Treat it as not in the game.

Calculator order:

- The proto field order (`talent_spell_id`) equals `codeOrder` for every class.
- Shaman ids and order equal `opt/talents_meta.json` and `TREE_ORDER` in `src/data.js`.
- `-055-5530003315513151` decodes to 0/10/41 and `-055030200001-5530100014513151` to 0/16/35, both legal, and both re-encode to the same string.

Tier rule:

- In the client, every node's `TraitCond.SpentAmountRequired` is 5 x (row - 1), for all 467 nodes.

Rank values:

- 1,746 per-rank curve values and 773 effect base points and per-level values were compared with wowsims' hotfixed spell store. There were 0 differences, and the 0 description differences include Vindication's text.
- So the hotfixes up to push 113715 did not change talent values from the base DB2. Later hotfixes were not checked.

Rank texts:

- There are 1,297 talent ranks in total.
- The numbers in the client text equal wowforevertalents.com on 1,269 ranks and timesaver.gg on 1,255.
- Most differences are ability damage ranges, where the sources round differently or timesaver.gg skips level scaling (Oath of Light shows 0 on timesaver.gg; the client and wowforevertalents.com give 400/115/230).
- Other differences:
  - wowforevertalents.com gives Vindication the Classic text ("Strength and Agility by 5%"). The client and wowsims give an Attack Power reduction of 68/136/204 for 30 sec.
  - timesaver.gg's Thick Hide shows "180 additional base Armor per level" at every rank. The client gives 1/2/3.
  - The resolver here cannot fill some tokens (22 ranks), so the text comes from wowforevertalents.com for 13 talents: Feral Charge, Shifting Power, Wild Growth, Summon Hawk, Ice Barrier, Shield Specialization, Reckoning, Divine Aegis, Holy Nova, Prayer of Mending, Death Mark, Demonic Brand and Piercing Howl. Their effect values in `effects` still come from the client.
  - Shaman: all 148 ranks agree across the three sources.

Decode checks. These are stored per class in `verification.decode_checks`; the scripts are `decode_checks.py`, `check_maxroll_vs_timesaver.py` and `check_method.py`.

- A, every class except rogue: a timesaver.gg preset code that cites Maxroll, decoded with `codeOrder`, equals the Maxroll planner build read from client node entry ids. That is 21 builds, all equal. Rogue has no such pair, because timesaver.gg's rogue presets cite Method.
- B, rogue and warrior: timesaver.gg preset codes that cite Method equal the Method embeds decoded from Method's own bit format. That is 4 builds, all equal.
- B2: in all 61 Method embeds, the point order ends on the loadout string's build.
- C (soft check): every talent linked in the Maxroll talent text appears in a decoded profile build, except three that the text names as optional swaps (Hunter: Improved Mend Pet, Spirit Bond; Rogue: Puncturing Wounds).
- D: all 9 wowsims preset strings decode and re-encode exactly. One, the Holy Priest preset `00520101133-33505003030121531`, breaks the tier rule: its row 3 Discipline talents (Mental Agility, Inner Focus, Improved Power Word: Shield, Meditation) have 8 points above them, and 10 are needed.

## Routes: what to watch for

- `order[i]` is the point spent at level 10 + i. `route_runs` has the same order in the app's `ROUTES` format (`[id, count]`).
- `order_check` and `final.legal_on_client_tree` test each source against the client tree, using the wowsims rule: a row needs 5 points per row above it, counting only rows above, and a prerequisite must be at max rank.
- The client does not settle whether points in the gated row itself count. Method's planner counts every point in the tree. So Method's "Shock Prot", "Backstab Focused" and "Shadow Brand" are illegal under the wowsims rule and may be reachable in game. This is unverified.
- Maxroll Mage: all three planner orders have illegal steps on the client tree. The Fire build ends with Critical Mass at 5/3, so Maxroll's planner data does not match the live Mage tree. The final Frost and Arcane builds are legal and equal the timesaver.gg presets.
- Warcraft Tavern "Level 60 Deep Assassination Build" decodes to Lethality 5/2, Blood Splatter 2/1 and Seal Fate 5/3, so it was made on an older tree. Some other Warcraft Tavern links place a point one level early (flagged in `order_check`).
- Excluded and listed under `excluded`: Warcraft Tavern's level 30 beta builds (all three Shaman specs, the hunter leveling builds), and Method Legacy-talent embeds, which are not class tree builds.
- Partial routes kept as published:
  - Maxroll Hunter profiles have 50 points.
  - Method Paladin leveling builds stop at 33 (Retribution) and 43 (Protection) points.
  - Priest guides respec at 40: Maxroll and Method "Level 1-39" (30 points), then a full order for 40-60.
- wowtbc.gg's Restoration Shaman "Leveling 1-60" is the Elemental leveling path (31/9/11), the same one its Elemental page gives. It is listed under Restoration because the guide puts it there, with a note.
- No guide here gives milestones only: every non-secondary leveling entry is point by point. Final-only entries are timesaver.gg transcriptions of Wowhead and Icy Veins codes.
- Level 60 builds: `use_in_build_name` is "raid" and/or "dungeon" when the build's own name says so. `use_words_in_guide_text` records the same words found in the guide text next to the build, which is looser. Two builds are named for dungeons: Method's Protection Warrior "Standard Dungeon Build" and Frost Mage "Dungeon AoE + ST Blend". Warcraft Tavern's Arcane build is named "Dungeon & Raid". wowtbc.gg's builds have no use label.

## Gaps

- No Wowhead, Icy Veins or Mobalytics page was read directly (Cloudflare). wow.gg builds were not read.
- No guide from a reachable site has a level 60 build for Retribution Paladin, Discipline or Holy Priest, or any Shaman spec, apart from wowtbc.gg. Each of those has exactly one source: one wowtbc.gg page with no author or date.
- The wago.tools CSVs carry no hotfixes. They agree with wowsims' store through hotfix push 113715. Anything hotfixed after that is not reflected.
- The tier rule (whether points in the gated row count) and the prerequisite rank are taken from wowsims. The client tables do not settle either.
- `forever_vs_classic` labels come from wowforevertalents.com and were not checked.
- `affects` lists are derived from class masks. They can include spells that share mask bits.

## Rebuild

The scripts read the fetched pages and exports under `/home/claude/ext/` and `/home/claude/dl/talents_all/`, which are not in this repo (same convention as `pipeline/README.md`). Run order:

1. Fetch:
   - `fetch_misc.py wago wdb wft wowtbc`
   - `fetch_timesaver.py`
   - `fetch_maxroll.py`
   - `fetch_method.py`
   - `fetch_wt.py`
   - `fetch_misc.py wtdates`
2. `client_trees.py`: client tree rebuild, written to `/home/claude/work/talents/client_trees.json`.
3. `compare_text.py`: per-rank text from the client (`talent_text.py`), compared with the two calculators.
4. `check_method.py`: decodes the Method embeds (`method_decode.py`).
5. `decode_checks.py`.
6. `build_talents.py`, which writes `data/talents/<class>.json`.
7. `build_routes.py`, which writes `data/routes/<class>.json`.

`lib.py` holds the shared code: ids, `codeOrder`, code decode and encode, the Warcraft DB ordered-link decoder, and the legality checks. `check_maxroll_vs_timesaver.py` prints check A.
